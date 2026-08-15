#!/usr/bin/env python3
"""Run the isolated Stage 7 pipeline on the copied 3DCodeBench framework.

The original 3DCodeBench text-to-3D system prompt remains the only generation
system prompt.  Structure extraction is a separate pre-generation phase and
does not modify this runner's prompt.  This runner has no dependency on
StructGen3D or any Stage 2--6 prompt, runner, output, or repair policy.
"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml


HARD_CODED_BLENDER = (
    "/Users/fengruiding/Downloads/3d_code/tools/"
    "Blender-5.0.app/Contents/MacOS/Blender"
)


REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from core.visual_critique import (  # noqa: E402
    build_critique_user_content,
    critique_system_prompt,
    parse_critique_response,
)
from core.structural_validation import (  # noqa: E402
    apply_parameter_invariance_gate,
    native_part_parameter_ids,
    run_validation_probe,
    score_markdown,
    score_structure_report,
)
from core.structure_extraction import validate_blueprint  # noqa: E402

DEFAULT_CONFIG_DIR = REPO_ROOT / "configs"
DEFAULT_CONFIG = DEFAULT_CONFIG_DIR / "gemma_4_31b.yaml"
DEFAULT_DATA_DIR = REPO_ROOT / "benchmark" / "categories"
DEFAULT_OUTPUT_DIR = REPO_ROOT.parent / "stage_results" / "stage7_output"
DEFAULT_STRUCTURE_CONTEXT_DIR = (
    DEFAULT_OUTPUT_DIR
)
DEFAULT_SYSTEM_PROMPT = REPO_ROOT / "prompts" / "text_to_3d_system_prompt.txt"
DEFAULT_VALIDATION_TEST_ROOT = REPO_ROOT.parent / "validation_test"
RENDER_SCRIPT = REPO_ROOT / "core" / "render.py"
MAX_ERROR_CHARS = 3000
API_FORMAT_LMSTUDIO = "lmstudio_responses"
API_FORMAT_OPENAI_CHAT = "openai_chat_completions"
API_FORMAT_OPENAI_RESPONSES = "openai_responses"
API_FORMAT_GEMINI_GENERATE_CONTENT = "gemini_generate_content"
SUPPORTED_API_FORMATS = {
    API_FORMAT_GEMINI_GENERATE_CONTENT,
    API_FORMAT_LMSTUDIO,
    API_FORMAT_OPENAI_CHAT,
    API_FORMAT_OPENAI_RESPONSES,
}

# Explicit transport seam for deterministic unit tests. Production leaves this
# unset and therefore always uses the isolated request worker for finite
# wall-clock deadlines.
_REQUEST_URLOPEN_OVERRIDE = None


class AmbiguousRemoteResultError(RuntimeError):
    """The remote may have spent tokens, but closed before returning a result."""


class ApiWallClockTimeoutError(AmbiguousRemoteResultError):
    """A request exceeded its total wall-clock deadline."""


class BackgroundResponseError(RuntimeError):
    """An OpenAI background response reached a non-success terminal state."""


def safe_to_retry_api_error(exc: BaseException) -> bool:
    """Retry only explicit server rejections that cannot hide a billed result."""

    if isinstance(exc, AmbiguousRemoteResultError):
        return False
    message = str(exc)
    return (
        "HTTP 408:" in message
        or "HTTP 429:" in message
        or re.search(r"HTTP 5\d\d:", message) is not None
    )


SHARED_ANCHOR_IMPLEMENTATION_CONTRACT = """For each concrete attachment in the
blueprint, derive one parent anchor and one child anchor after both geometries
are parameterized. Each local anchor must be a retained Mesh vertex or a Mesh
connection sample deliberately authored into that part; fixed world offsets,
parenting alone, proximity, comments, or metadata are not anchors.

Use this data flow for every independent child instance:

from mathutils import Matrix, Vector

def local_anchor_world(obj, local_anchor):
    return obj.matrix_world @ Vector(local_anchor)

def attach_child_to_parent_at_shared_anchor(
    parent_obj, child_obj, parent_anchor_local, child_anchor_local
):
    parent_anchor_world = local_anchor_world(parent_obj, parent_anchor_local)
    child_anchor_world = local_anchor_world(child_obj, child_anchor_local)
    correction = parent_anchor_world - child_anchor_world
    child_obj.matrix_world = Matrix.Translation(correction) @ child_obj.matrix_world
    aligned_child_world = child_obj.matrix_world.copy()
    child_obj.parent = parent_obj
    child_obj.matrix_world = aligned_child_world
    child_anchor_world = local_anchor_world(child_obj, child_anchor_local)
    assert (parent_anchor_world - child_anchor_world).length <= 1e-5

4. Call the helper once per independent child, including repeated left/right
   instances. Add no translation afterward. Build contact or embedding around
   the equal point. Parent size changes and child size changes must recompute
   their local anchors when the complete script reruns. Do not fake evidence
   with marker objects or metadata. Features classified by the planner as
   integrated stay in their owning Mesh or material and require no separate
   parent-child anchor."""

NATIVE_PART_PARAMETER_CONTRACT = """Declare one top-level literal dictionary
named PART_PARAMS. Its keys must equal the structure blueprint's parts[].id
values exactly: one key per listed semantic unit, no missing keys, and no extra
keys for helper geometry, ornaments, or samples. Do not use a prescribed
category ontology. A repeated item receives its own key only when the frozen
blueprint lists that concrete instance as its own part. Every value is a
literal dictionary containing at least {"scale": 1.0}; you may add other
simple numeric, boolean, or string construction parameters when useful.

PART_PARAMS = {
    "model_chosen_concrete_part_id": {"scale": 1.0},
}

For every listed semantic part, create one Mesh object whose obj.name and
obj["stage7_part_id"] equal its PART_PARAMS key. Repeated decorative primitives
owned by one listed unit may be built separately in memory, but join their
geometry into that one owning Mesh data-block before validation; do not expose
each primitive as another parameter part. Builders must read the current
parameters before authoring vertices, retained connection samples, or local
anchors. The scale is a geometry-construction input, not object.scale and not a
post-construction vertex edit. If a parent or child parameter changes, the
complete script must rebuild that geometry, derive both endpoints from the new
geometry, align the endpoints, and only then parent the child. Do not cache
anchors computed for scale 1.0. Integrated features remain inside their owner
and do not receive independent keys.

The web editor replaces only literal PART_PARAMS values before executing the
entire script from an empty Blender 5.0 scene. Therefore keep the declaration
literal and at module scope; do not overwrite it later. A shared Mesh builder
may apply PART_PARAMS[name]["scale"] to every authored local vertex before
from_pydata, provided every retained local anchor receives the identical scale
before world alignment. This central pattern is preferable to leaving scale
reads scattered or unused in individual builders."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Blender Python for all benchmark text prompts with LM Studio."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--model",
        default=None,
        help="Override only the model ID from the local config.",
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--output-prefix",
        default="",
        help=(
            "Prefix for output instance directories and canonical Python files, "
            "for example kimi_k3_. Input instance names remain unchanged."
        ),
    )
    parser.add_argument(
        "--output-suffix",
        default="",
        help=(
            "Suffix for output instance directories and canonical Python files, "
            "for example (1). Input instance names remain unchanged."
        ),
    )
    parser.add_argument(
        "--structure-context-dir",
        type=Path,
        default=DEFAULT_STRUCTURE_CONTEXT_DIR,
        help=(
            "Directory containing <instance>/structure.json from "
            "extract_structure.py; injected as ordinary user context."
        ),
    )
    parser.add_argument("--system-prompt", type=Path, default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument(
        "--prompt-type",
        choices=("description", "instruction"),
        default="description",
        help="Use prompt_description.txt or prompt_instruction.txt.",
    )
    parser.add_argument(
        "--instances",
        nargs="*",
        default=None,
        help="Optional instance names, e.g. Countertop_seed0 Vase_seed0.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--resume-existing",
        action="store_true",
        help=(
            "Reuse an existing canonical Python script and resume from Blender, "
            "structural, and visual validation without submitting a new initial "
            "generation request. Instances without a script still run normally."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="Model API timeout in seconds; 0 means no client-side time limit.",
    )
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--blender", default=HARD_CODED_BLENDER)
    parser.add_argument("--render-samples", type=int, default=32)
    parser.add_argument("--render-resolution", type=int, default=512)
    parser.add_argument(
        "--render-engine",
        choices=("CYCLES", "BLENDER_EEVEE"),
        default="CYCLES",
    )
    parser.add_argument("--render-timeout", type=int, default=240)
    parser.add_argument(
        "--validation-test-root",
        type=Path,
        default=DEFAULT_VALIDATION_TEST_ROOT,
        help="validation_test project used for parent/child and shared-anchor checks.",
    )
    parser.add_argument(
        "--structure-timeout",
        type=int,
        default=180,
        help="Seconds allowed for one validation_test Blender probe.",
    )
    parser.add_argument(
        "--max-structure-retries",
        type=int,
        default=1,
        help="Structural repair rounds after parent/child or shared-anchor validation fails.",
    )
    parser.add_argument(
        "--min-structure-score",
        type=float,
        default=85.0,
        help="Minimum 0-100 structural score; hard structural issues still fail.",
    )
    parser.add_argument(
        "--no-structure-verify",
        action="store_true",
        help="Disable validation_test structural checks and structural repair only.",
    )
    parser.add_argument(
        "--max-trace-retries",
        type=int,
        default=3,
        help="Blender traceback repair rounds after a generated script fails.",
    )
    parser.add_argument(
        "--max-visual-iterations",
        type=int,
        default=2,
        help="Visual feedback repair rounds after the script renders successfully.",
    )
    parser.add_argument(
        "--visual-baseline-dir",
        type=Path,
        default=None,
        help=(
            "Optional prior result directory whose renders are a visual quality "
            "floor during critique; it does not provide structural evidence."
        ),
    )
    parser.add_argument(
        "--no-render-verify",
        action="store_true",
        help="Disable Blender validation, traceback repair, and visual feedback.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep between successful requests.",
    )
    return parser.parse_args()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def output_instance_name(instance: str, prefix: str, suffix: str = "") -> str:
    """Return a filesystem-safe model/run name without changing input ids."""

    for label, value in (("prefix", prefix), ("suffix", suffix)):
        if value and (value in {".", ".."} or Path(value).name != value):
            raise ValueError(
                f"output {label} must be one path-segment fragment: {value!r}"
            )
    return f"{prefix}{instance}{suffix}"


def clear_generation_artifacts(out_dir: Path) -> None:
    """Clear one rerun while preserving provenance and resumable API requests."""

    if not out_dir.is_dir():
        return
    for child in out_dir.iterdir():
        if child.name == "structure_extraction" or child.name.endswith(
            ".background.json"
        ):
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def load_structure_context(
    structure_dir: Path,
    instance: str,
    output_instance: str | None = None,
) -> tuple[dict, Path]:
    """Load and revalidate one extraction before it reaches generation."""

    output_instance = output_instance or instance
    candidates = [
        structure_dir / output_instance / "structure_extraction" / "structure.json",
        structure_dir / instance / "structure_extraction" / "structure.json",
        structure_dir / instance / "structure.json",
    ]
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        raise FileNotFoundError(
            "missing extracted structure context; checked:\n- "
            + "\n- ".join(str(candidate.resolve()) for candidate in candidates)
        )
    try:
        blueprint = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid structure JSON {path}: {exc}") from exc
    if not isinstance(blueprint, dict):
        raise ValueError(f"structure context must be one JSON object: {path}")
    errors = validate_blueprint(blueprint)
    if errors:
        raise ValueError(
            "invalid extracted structure context:\n- " + "\n- ".join(errors)
        )
    return blueprint, path


def compact_blueprint_for_generation(blueprint: dict) -> dict:
    """Keep construction-critical fields while removing planner verbosity."""

    parts = []
    for part in blueprint.get("parts") or []:
        parts.append({
            "id": part.get("id"),
            "parent_id": part.get("parent_id"),
            "quantity": part.get("quantity"),
            "geometry": part.get("geometry_summary"),
            "representation_reason": part.get("representation_reason"),
            "integrated_features": part.get("integrated_features") or [],
        })
    attachments = []
    for item in blueprint.get("attachments") or []:
        attachments.append({
            "id": item.get("id"),
            "parent": item.get("parent_part_id"),
            "child": item.get("child_part_id"),
            "type": item.get("connection_type"),
            "parent_anchor": item.get("parent_anchor"),
            "child_anchor": item.get("child_anchor"),
            "placement": item.get("placement_rule"),
            "shared_anchor_id": item.get("shared_anchor_id"),
            "recompute": item.get("recompute_rule"),
        })
    return {
        "root": blueprint.get("root_part_id"),
        "frame": blueprint.get("coordinate_frame"),
        "parts": parts,
        "attachments": attachments,
        "constraints": blueprint.get("global_constraints") or [],
    }


def compose_generation_user_prompt(description: str, blueprint: dict) -> str:
    """Place compact extracted construction context beside the visual task."""

    structure_json = json.dumps(
        compact_blueprint_for_generation(blueprint),
        ensure_ascii=False,
        indent=2,
    )
    return f"""HARD RESPONSE MODE: Do not expose planning, analysis, a design diary,
or explanatory prose. Start immediately with valid Blender Python and spend the
response budget on one complete executable script. The first output line must
be Python, normally `import bpy`.

Object description:

<object_description>
{description}
</object_description>

<visual_fidelity_contract>
Visual quality and structure are equal requirements. Preserve the described
silhouette, proportions, colors, organic transitions, and diagnostic geometry.
Follow the planner's frozen decomposition exactly: construct every listed unit
independently and build every integrated feature inside its declared owner.
Do not add, remove, merge, split, or simplify units to make anchor validation
easier. Use self-contained materials or procedural shaders for requested color
and surface appearance; never return default white when color is named. Shared
anchors control only the listed independent attachments. Prefer compact
procedural helpers and loops; target one complete script under roughly 550
lines and 22,000 characters.
</visual_fidelity_contract>

Extracted structure context:

<structure_blueprint>
{structure_json}
</structure_blueprint>

Use the extracted structure as construction context so significant parts form
one coherent parent-to-child assembly and do not float apart. Every attachment
marked shared_anchor_required is mandatory, not advisory. Implement it using
the contract below.

<shared_anchor_implementation_contract>
{SHARED_ANCHOR_IMPLEMENTATION_CONTRACT}
</shared_anchor_implementation_contract>

<native_part_parameter_contract>
{NATIVE_PART_PARAMETER_CONTRACT}
</native_part_parameter_contract>

The object description is the visual source of truth. The compact blueprint is
only an assembly plan. Return code only as required by the system prompt."""


def persist_log(out_dir: Path, log: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def append_flow_event(
    out_dir: Path,
    log: dict,
    event: str,
    detail: str,
    **fields: object,
) -> dict:
    """Append one chronological event to both JSON and readable flow logs."""

    item = {
        "sequence": len(log.setdefault("flow_events", [])) + 1,
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "event": event,
        "detail": detail,
        **fields,
    }
    log["flow_events"].append(item)
    with (out_dir / "flow.log").open("a", encoding="utf-8") as handle:
        handle.write(
            f"{item['sequence']:02d} | {item['timestamp']} | {event} | {detail}\n"
        )
    persist_log(out_dir, log)
    return item


def load_config(path: Path) -> dict:
    config = yaml.safe_load(path.read_text()) or {}
    config.setdefault("api_format", API_FORMAT_LMSTUDIO)
    key = config.get("api_key")
    if isinstance(key, str) and key.startswith("${") and key.endswith("}"):
        config["api_key"] = os.environ.get(key[2:-1])
    missing = [key for key in ("api_url", "api_key", "model") if not config.get(key)]
    if missing:
        raise SystemExit(f"Missing required config key(s) in {path}: {', '.join(missing)}")
    if config["api_format"] not in SUPPORTED_API_FORMATS:
        raise SystemExit(
            f"Unsupported api_format in {path}: {config['api_format']}. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_API_FORMATS))}"
        )
    if str(config["api_key"]).startswith(("YOUR_", "<")):
        raise SystemExit(f"Replace the api_key placeholder in {path}.")
    return config


def iter_instances(data_dir: Path, selected: list[str] | None) -> list[Path]:
    if selected:
        instances = [data_dir / name for name in selected]
    else:
        instances = sorted(p for p in data_dir.iterdir() if p.is_dir())

    missing = [p.name for p in instances if not p.is_dir()]
    if missing:
        raise SystemExit(f"Missing benchmark instance(s): {', '.join(missing)}")
    return instances


def extract_message(response: dict) -> str:
    candidates = response.get("candidates")
    if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict):
        content = candidates[0].get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        if isinstance(parts, list):
            chunks = [
                part.get("text", "")
                for part in parts
                if isinstance(part, dict)
                and not part.get("thought", False)
                and isinstance(part.get("text"), str)
            ]
            if chunks:
                return "".join(chunks)
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    output = response.get("output")
    if isinstance(output, list):
        for part in output:
            if part.get("type") != "message":
                continue
            content = part.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                chunks = [
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                    and item.get("type") in {"output_text", "text"}
                    and isinstance(item.get("text"), str)
                ]
                if chunks:
                    return "".join(chunks)
    if isinstance(response.get("content"), str):
        return response["content"]
    if isinstance(response.get("message"), str):
        return response["message"]
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks = [
                item.get("text", item.get("content", ""))
                for item in content
                if isinstance(item, dict)
                and isinstance(item.get("text", item.get("content", "")), str)
            ]
            if chunks:
                return "".join(chunks)
    raise ValueError("Could not find message content in API response")


def extract_reasoning(response: dict) -> str | None:
    candidates = response.get("candidates")
    if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict):
        content = candidates[0].get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        if isinstance(parts, list):
            chunks = [
                part.get("text", "")
                for part in parts
                if isinstance(part, dict)
                and part.get("thought", False)
                and isinstance(part.get("text"), str)
            ]
            text = "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip())
            if text:
                return text
    output = response.get("output")
    if isinstance(output, list):
        chunks = []
        for part in output:
            if not isinstance(part, dict) or part.get("type") != "reasoning":
                continue
            content = part.get("content")
            if isinstance(content, str):
                chunks.append(content)
            elif isinstance(content, list):
                chunks.extend(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                    and isinstance(item.get("text"), str)
                )
            summary = part.get("summary")
            if isinstance(summary, list):
                chunks.extend(
                    item.get("text", "")
                    for item in summary
                    if isinstance(item, dict)
                    and isinstance(item.get("text"), str)
                )
        text = "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip())
        if text:
            return text
    choices = response.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict):
            for key in ("reasoning_content", "reasoning"):
                value = message.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return None


def persist_response(path: Path, response: dict) -> None:
    path.write_text(json.dumps(response, indent=2) + "\n")
    reasoning = extract_reasoning(response)
    if reasoning:
        path.with_suffix(".reasoning.txt").write_text(reasoning.rstrip() + "\n")


def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped + "\n"


def truncate_error(text: str, max_chars: int = MAX_ERROR_CHARS) -> str:
    if not text:
        return "(no error text recorded)"
    text = text.rstrip()
    if len(text) <= max_chars:
        return text
    head = int(max_chars * 0.7)
    tail = max_chars - head - 80
    return f"{text[:head]}\n\n... [truncated {len(text) - head - tail} chars] ...\n\n{text[-tail:]}"


def lmstudio_input(user_input: str | list[dict]) -> str | list[dict]:
    if isinstance(user_input, str):
        return user_input

    converted = []
    for part in user_input:
        if part["type"] == "text":
            converted.append({"type": "text", "content": part.get("text", part.get("content", ""))})
        elif part["type"] == "image":
            if "data_url" in part:
                data_url = part["data_url"]
            else:
                encoded = base64.b64encode(part["data"]).decode("ascii")
                data_url = f"data:{part.get('mime', 'image/png')};base64,{encoded}"
            converted.append({"type": "image", "data_url": data_url})
        else:
            raise ValueError(f"Unknown input part type: {part['type']!r}")
    return converted


def openai_user_content(user_input: str | list[dict]) -> str | list[dict]:
    """Convert internal text/image parts to OpenAI chat message content."""

    if isinstance(user_input, str):
        return user_input

    converted = []
    for part in user_input:
        if part["type"] == "text":
            converted.append(
                {"type": "text", "text": part.get("text", part.get("content", ""))}
            )
        elif part["type"] == "image":
            if "data_url" in part:
                data_url = part["data_url"]
            else:
                encoded = base64.b64encode(part["data"]).decode("ascii")
                data_url = f"data:{part.get('mime', 'image/png')};base64,{encoded}"
            converted.append(
                {"type": "image_url", "image_url": {"url": data_url}}
            )
        else:
            raise ValueError(f"Unknown input part type: {part['type']!r}")
    return converted


def openai_responses_input(user_input: str | list[dict]) -> str | list[dict]:
    """Convert internal text/image parts to OpenAI Responses API input."""

    if isinstance(user_input, str):
        return user_input

    content = []
    for part in user_input:
        if part["type"] == "text":
            content.append(
                {
                    "type": "input_text",
                    "text": part.get("text", part.get("content", "")),
                }
            )
        elif part["type"] == "image":
            if "data_url" in part:
                data_url = part["data_url"]
            else:
                encoded = base64.b64encode(part["data"]).decode("ascii")
                data_url = f"data:{part.get('mime', 'image/png')};base64,{encoded}"
            content.append({"type": "input_image", "image_url": data_url})
        else:
            raise ValueError(f"Unknown input part type: {part['type']!r}")
    return [{"role": "user", "content": content}]


def gemini_user_parts(user_input: str | list[dict]) -> list[dict]:
    """Convert internal text/image parts to Gemini generateContent Parts."""

    if isinstance(user_input, str):
        return [{"text": user_input}]

    converted = []
    for part in user_input:
        if part["type"] == "text":
            converted.append(
                {"text": part.get("text", part.get("content", ""))}
            )
        elif part["type"] == "image":
            mime_type = part.get("mime", "image/png")
            if "data_url" in part:
                match = re.fullmatch(
                    r"data:([^;,]+);base64,(.*)",
                    part["data_url"],
                    flags=re.DOTALL,
                )
                if not match:
                    raise ValueError("Gemini image data_url must be base64 encoded")
                mime_type, encoded = match.groups()
            else:
                encoded = base64.b64encode(part["data"]).decode("ascii")
            converted.append(
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": encoded,
                    }
                }
            )
        else:
            raise ValueError(f"Unknown input part type: {part['type']!r}")
    return converted


def build_api_payload(
    *,
    api_format: str,
    model: str,
    system_prompt: str,
    user_prompt: str | list[dict],
    max_output_tokens: int | None = None,
    reasoning_effort: str | None = None,
    background: bool = False,
) -> dict:
    """Build either the existing LM Studio body or OpenAI chat/completions."""

    if api_format == API_FORMAT_LMSTUDIO:
        payload = {
            "model": model,
            "system_prompt": system_prompt,
            "input": lmstudio_input(user_prompt),
        }
        if max_output_tokens is not None:
            payload["max_output_tokens"] = max_output_tokens
        return payload
    if api_format == API_FORMAT_GEMINI_GENERATE_CONTENT:
        generation_config = {}
        if max_output_tokens is not None:
            generation_config["maxOutputTokens"] = max_output_tokens
        if reasoning_effort:
            generation_config["thinkingConfig"] = {
                "thinkingLevel": reasoning_effort.lower()
            }
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {"role": "user", "parts": gemini_user_parts(user_prompt)}
            ],
        }
        if generation_config:
            payload["generationConfig"] = generation_config
        return payload
    if api_format == API_FORMAT_OPENAI_RESPONSES:
        payload = {
            "model": model,
            "instructions": system_prompt,
            "input": openai_responses_input(user_prompt),
            "store": False,
        }
        if max_output_tokens is not None:
            payload["max_output_tokens"] = max_output_tokens
        if reasoning_effort:
            payload["reasoning"] = {"effort": reasoning_effort}
        if background:
            payload["background"] = True
        return payload
    if api_format == API_FORMAT_OPENAI_CHAT:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": openai_user_content(user_prompt)},
            ],
            "stream": False,
        }
        if max_output_tokens is not None:
            payload["max_tokens"] = max_output_tokens
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
        return payload
    raise ValueError(f"Unsupported api_format: {api_format}")


def normalize_api_timeout(timeout: int | float | None) -> int | float | None:
    """Treat zero/negative values as an intentional unlimited API wait."""

    if timeout is None or timeout <= 0:
        return None
    return timeout


def background_state_path(response_path: Path) -> Path:
    """Return the durable sidecar used to resume one OpenAI response."""

    return response_path.with_suffix(".background.json")


def _local_timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _write_json_atomic(path: Path, value: dict) -> None:
    """Write state atomically so a killed process cannot leave partial JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _request_json(
    request: urllib.request.Request,
    *,
    timeout: int | float | None,
    ambiguous_on_disconnect: bool,
) -> dict:
    seconds = normalize_api_timeout(timeout)
    if _REQUEST_URLOPEN_OVERRIDE is not None:
        return _request_json_direct(
            request,
            timeout=seconds,
            ambiguous_on_disconnect=ambiguous_on_disconnect,
            opener=_REQUEST_URLOPEN_OVERRIDE,
        )
    if seconds is None:
        return _request_json_direct(
            request,
            timeout=seconds,
            ambiguous_on_disconnect=ambiguous_on_disconnect,
        )

    worker_input = {
        "url": request.full_url,
        "data_base64": (
            base64.b64encode(request.data).decode("ascii")
            if request.data is not None
            else None
        ),
        "headers": dict(request.header_items()),
        "method": request.get_method(),
        "socket_timeout": seconds,
        "ambiguous_on_disconnect": ambiguous_on_disconnect,
    }
    try:
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "core" / "api_request_worker.py")],
            input=json.dumps(worker_input).encode("utf-8"),
            capture_output=True,
            timeout=float(seconds),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ApiWallClockTimeoutError(
            "model API request exceeded the total wall-clock timeout of "
            f"{seconds:g}s; the request worker was terminated so Stage7 can "
            "continue to the next seed"
        ) from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[-1000:]
        raise AmbiguousRemoteResultError(
            "model API request worker exited abnormally; automatic retry "
            f"disabled: {detail}"
        )
    try:
        envelope = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AmbiguousRemoteResultError(
            "model API request worker returned an invalid envelope; automatic "
            f"retry disabled: {exc}"
        ) from exc
    if envelope.get("ok") is True:
        return envelope["value"]
    exception_name = str(envelope.get("exception") or "RuntimeError")
    message = str(envelope.get("message") or "model API request failed")
    if exception_name == "AmbiguousRemoteResultError":
        raise AmbiguousRemoteResultError(message)
    if exception_name == "URLError":
        raise urllib.error.URLError(message)
    if exception_name in {"TimeoutError", "ApiWallClockTimeoutError"}:
        raise TimeoutError(message)
    raise RuntimeError(message)


def _request_json_direct(
    request: urllib.request.Request,
    *,
    timeout: int | float | None,
    ambiguous_on_disconnect: bool,
    opener=None,
) -> dict:
    opener = opener or urllib.request.urlopen
    try:
        with opener(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except json.JSONDecodeError as exc:
        if ambiguous_on_disconnect:
            raise AmbiguousRemoteResultError(
                "remote returned invalid JSON after the request may have been "
                f"billed; automatic retry disabled: {exc}"
            ) from exc
        raise urllib.error.URLError(f"invalid JSON response: {exc}") from exc
    except http.client.RemoteDisconnected as exc:
        if not ambiguous_on_disconnect:
            raise
        raise AmbiguousRemoteResultError(
            "remote closed before returning a response; automatic retry "
            f"disabled: {exc}"
        ) from exc
    except (http.client.HTTPException, OSError) as exc:
        if not ambiguous_on_disconnect:
            raise
        raise AmbiguousRemoteResultError(
            "request transport failed after the remote may have accepted it; "
            f"automatic retry disabled: {type(exc).__name__}: {exc}"
        ) from exc


def _save_background_status(
    state_path: Path,
    state: dict,
    *,
    status: str,
    poll_error: str | None = None,
) -> None:
    now = _local_timestamp()
    previous = state.get("status")
    state["status"] = status
    state["updated_at"] = now
    if status != previous:
        state.setdefault("status_history", []).append(
            {"timestamp": now, "status": status}
        )
    if poll_error is None:
        state.pop("last_poll_error", None)
    else:
        state["last_poll_error"] = poll_error
        state["poll_error_count"] = int(state.get("poll_error_count", 0)) + 1
    _write_json_atomic(state_path, state)


def _archive_mismatched_background_state(state_path: Path) -> Path:
    """Keep an old request id when its prompt no longer matches this call."""

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archived = state_path.with_name(
        f"{state_path.name.removesuffix('.json')}.stale-{stamp}.json"
    )
    counter = 1
    while archived.exists():
        archived = state_path.with_name(
            f"{state_path.name.removesuffix('.json')}.stale-{stamp}-{counter}.json"
        )
        counter += 1
    state_path.replace(archived)
    return archived


def call_openai_background_response(
    *,
    api_url: str,
    api_key: str,
    payload: dict,
    state_path: Path,
    request_timeout: int | float | None = 60,
    poll_interval: float = 5.0,
) -> dict:
    """Submit once, persist the response id, and poll with short GET calls."""

    poll_interval = max(0.1, float(poll_interval))
    request_timeout = 60 if request_timeout is None else request_timeout
    request_hash = sha256_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    state = None
    if state_path.is_file():
        try:
            candidate = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"invalid OpenAI background state {state_path}: {exc}"
            ) from exc
        if (
            candidate.get("api_url") == api_url
            and candidate.get("request_sha256") == request_hash
            and candidate.get("response_id")
        ):
            state = candidate
        else:
            archived = _archive_mismatched_background_state(state_path)
            print(
                "[OpenAI background] request changed; archived old state at "
                f"{archived}",
                flush=True,
            )

    response = None
    if state is None:
        request = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        response = _request_json(
            request,
            timeout=request_timeout,
            ambiguous_on_disconnect=True,
        )
        response_id = response.get("id")
        if not isinstance(response_id, str) or not response_id:
            raise RuntimeError(
                "OpenAI background submission returned no response id"
            )
        status = str(response.get("status") or "unknown")
        now = _local_timestamp()
        state = {
            "schema_version": "stage7-openai-background/v1",
            "api_url": api_url,
            "model": payload.get("model"),
            "request_sha256": request_hash,
            "response_id": response_id,
            "status": None,
            "submitted_at": now,
            "updated_at": now,
            "poll_count": 0,
            "poll_error_count": 0,
            "status_history": [],
        }
        _save_background_status(state_path, state, status=status)
        print(
            f"[OpenAI background] submitted response_id={response_id} "
            f"status={status}",
            flush=True,
        )
    else:
        response_id = str(state["response_id"])
        print(
            f"[OpenAI background] resume response_id={response_id} "
            f"last_status={state.get('status', 'unknown')}",
            flush=True,
        )

    retrieve_url = (
        api_url.rstrip("/")
        + "/"
        + urllib.parse.quote(response_id, safe="")
    )
    last_reported_status = None
    while True:
        if response is None:
            request = urllib.request.Request(
                retrieve_url,
                headers=headers,
                method="GET",
            )
            try:
                response = _request_json(
                    request,
                    timeout=request_timeout,
                    ambiguous_on_disconnect=False,
                )
                state["poll_count"] = int(state.get("poll_count", 0)) + 1
            except (
                RuntimeError,
                urllib.error.URLError,
                TimeoutError,
                http.client.HTTPException,
                OSError,
            ) as exc:
                if isinstance(exc, RuntimeError) and not safe_to_retry_api_error(exc):
                    raise
                _save_background_status(
                    state_path,
                    state,
                    status=str(state.get("status") or "unknown"),
                    poll_error=f"{type(exc).__name__}: {exc}",
                )
                print(
                    "[OpenAI background] poll connection failed; the same "
                    f"response_id will be retried: {type(exc).__name__}: {exc}",
                    flush=True,
                )
                time.sleep(poll_interval)
                continue

        returned_id = response.get("id")
        if returned_id not in (None, response_id):
            raise RuntimeError(
                f"OpenAI retrieve returned unexpected response id {returned_id!r}"
            )
        status = str(response.get("status") or "unknown")
        _save_background_status(state_path, state, status=status)
        if status != last_reported_status:
            print(
                f"[OpenAI background] response_id={response_id} status={status}",
                flush=True,
            )
            last_reported_status = status
        if status == "completed":
            return response
        if status not in {"queued", "in_progress"}:
            detail = response.get("error") or response.get("incomplete_details")
            raise BackgroundResponseError(
                f"OpenAI background response {response_id} ended with "
                f"status={status}: {json.dumps(detail, ensure_ascii=False)}"
            )
        response = None
        time.sleep(poll_interval)


def call_model_api(
    api_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str | list[dict],
    timeout: int | float | None,
    max_output_tokens: int | None = None,
    api_format: str = API_FORMAT_LMSTUDIO,
    reasoning_effort: str | None = None,
    background_state: Path | None = None,
    background_poll_interval: float = 5.0,
    background_request_timeout: int | float | None = 60,
) -> dict:
    payload = build_api_payload(
        api_format=api_format,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_output_tokens=max_output_tokens,
        reasoning_effort=reasoning_effort,
        background=(
            api_format == API_FORMAT_OPENAI_RESPONSES
            and background_state is not None
        ),
    )
    if api_format == API_FORMAT_OPENAI_RESPONSES and background_state is not None:
        return call_openai_background_response(
            api_url=api_url,
            api_key=api_key,
            payload=payload,
            state_path=background_state,
            request_timeout=background_request_timeout,
            poll_interval=background_poll_interval,
        )
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_format == API_FORMAT_GEMINI_GENERATE_CONTENT:
        headers["X-goog-api-key"] = api_key
    else:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        api_url,
        data=body,
        headers=headers,
        method="POST",
    )
    return _request_json(
        request,
        timeout=timeout,
        ambiguous_on_disconnect=True,
    )


def call_configured_model_api(
    config: dict,
    system_prompt: str,
    user_prompt: str | list[dict],
    timeout: int | float | None,
    response_path: Path | None = None,
) -> dict:
    """Call one configured provider, enabling durable OpenAI background mode."""

    api_format = config.get("api_format", API_FORMAT_LMSTUDIO)
    state_path = None
    if (
        api_format == API_FORMAT_OPENAI_RESPONSES
        and bool(config.get("openai_background", True))
        and response_path is not None
    ):
        state_path = background_state_path(response_path)
    return call_model_api(
        api_url=config["api_url"],
        api_key=config["api_key"],
        model=config["model"],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        timeout=timeout,
        max_output_tokens=config.get("max_output_tokens"),
        api_format=api_format,
        reasoning_effort=config.get("reasoning_effort"),
        background_state=state_path,
        background_poll_interval=float(config.get("openai_poll_interval", 5.0)),
        background_request_timeout=config.get("openai_request_timeout", 60),
    )


def call_code(
    config: dict,
    system_prompt: str,
    user_prompt: str | list[dict],
    timeout: int,
    response_path: Path | None = None,
) -> tuple[str, dict]:
    retries = max(0, int(config.get("api_retries", 0)))
    response = None
    for attempt in range(retries + 1):
        try:
            response = call_configured_model_api(
                config=config,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout=timeout,
                response_path=response_path,
            )
            break
        except (RuntimeError, urllib.error.URLError, TimeoutError) as exc:
            if not safe_to_retry_api_error(exc) or attempt >= retries:
                raise
            time.sleep(2 ** attempt)
    assert response is not None
    if response_path is not None:
        persist_response(response_path, response)
    code = strip_code_fence(extract_message(response))
    ast.parse(code)
    return code, response


def archive_renders(out_dir: Path, label: str) -> None:
    renders = out_dir / "renders"
    if not renders.exists():
        return
    history = out_dir / "renders_history"
    history.mkdir(parents=True, exist_ok=True)
    dst = history / label
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(str(renders), str(dst))


def render_script(
    args: argparse.Namespace,
    out_dir: Path,
    script_path: Path,
) -> dict:
    renders_dir = out_dir / "renders"
    log_path = renders_dir / "render_log.json"
    if renders_dir.exists():
        shutil.rmtree(renders_dir)
    renders_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        args.blender,
        "--background",
        "--python",
        str(RENDER_SCRIPT),
        "--",
        "--blender-render",
        "--script",
        str(script_path),
        "--output-dir",
        str(renders_dir),
        "--samples",
        str(args.render_samples),
        "--resolution",
        str(args.render_resolution),
        "--engine",
        args.render_engine,
    ]
    started = time.time()
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=args.render_timeout)
    except subprocess.TimeoutExpired:
        return {
            "status": "ERR_TIMEOUT",
            "n_meshes": 0,
            "n_views_rendered": 0,
            "error": f"Blender subprocess exceeded {args.render_timeout}s",
            "latency_s": round(time.time() - started, 2),
        }

    if not log_path.exists():
        return {
            "status": "ERR_NOLOG",
            "n_meshes": 0,
            "n_views_rendered": 0,
            "error": "Blender exited without writing render_log.json",
            "latency_s": round(time.time() - started, 2),
        }
    result = json.loads(log_path.read_text())
    history = out_dir / "renders_history"
    history.mkdir(parents=True, exist_ok=True)
    prior = []
    for candidate in history.iterdir():
        if candidate.name.startswith("render_attempt"):
            suffix = candidate.name.removeprefix("render_attempt")
            if suffix.isdigit():
                prior.append(int(suffix))
    snapshot = history / f"render_attempt{max(prior, default=0) + 1}"
    shutil.copytree(renders_dir, snapshot)
    result["render_snapshot"] = snapshot.name
    log_path.write_text(json.dumps(result, indent=2) + "\n")
    (snapshot / "render_log.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def build_trace_feedback_prompt(
    original_prompt: str,
    previous_code: str,
    render_log: dict,
    attempt_num: int,
    max_attempts: int,
) -> str:
    error_text = truncate_error(str(render_log.get("error") or ""))
    return f"""Original text-to-3D task:

{original_prompt}

Previous Blender Python script:

<previous_code>
{previous_code.rstrip()}
</previous_code>

Blender validation failed.

status: {render_log.get("status", "?")}
n_meshes: {render_log.get("n_meshes", 0)}
n_views_rendered: {render_log.get("n_views_rendered", 0)}

Traceback / error:

{error_text}

This is repair attempt {attempt_num} of {max_attempts}.

Return a complete corrected Blender 5.0 Python script only. Do not include prose, Markdown fences, XML tags, or explanations."""


def validate_with_trace_repair(
    args: argparse.Namespace,
    config: dict,
    system_prompt: str,
    original_prompt: str,
    code: str,
    out_dir: Path,
    script_path: Path,
    log: dict,
) -> tuple[str, bool]:
    script_path.write_text(code)
    max_attempts = args.max_trace_retries + 1

    for attempt in range(max_attempts):
        append_flow_event(
            out_dir,
            log,
            "blender_render_start",
            f"Render validation attempt {attempt + 1}/{max_attempts}",
            attempt=attempt + 1,
        )
        render_log = render_script(args, out_dir, script_path)
        log["render_history"].append({
            "stage": "trace",
            "attempt": attempt,
            "status": render_log.get("status"),
            "n_meshes": render_log.get("n_meshes", 0),
            "n_views_rendered": render_log.get("n_views_rendered", 0),
            "error": truncate_error(str(render_log.get("error") or ""), 600),
        })
        append_flow_event(
            out_dir,
            log,
            "blender_render_result",
            f"status={render_log.get('status')} meshes={render_log.get('n_meshes', 0)} views={render_log.get('n_views_rendered', 0)}",
            attempt=attempt + 1,
            status=render_log.get("status"),
            n_meshes=render_log.get("n_meshes", 0),
            n_views_rendered=render_log.get("n_views_rendered", 0),
        )

        if render_log.get("status") == "OK" and (render_log.get("n_meshes") or 0) > 0:
            append_flow_event(
                out_dir,
                log,
                "render_validation_passed",
                "Generated Blender script executed and rendered successfully",
            )
            return code, True

        archive_renders(out_dir, f"trace_attempt{attempt}_failed")
        if attempt == max_attempts - 1:
            append_flow_event(
                out_dir,
                log,
                "trace_repair_exhausted",
                "All Blender traceback repair attempts were exhausted",
            )
            return code, False

        feedback = build_trace_feedback_prompt(
            original_prompt=original_prompt,
            previous_code=code,
            render_log=render_log,
            attempt_num=attempt + 2,
            max_attempts=max_attempts,
        )
        (out_dir / f"trace_feedback_attempt{attempt + 1}.txt").write_text(feedback)
        append_flow_event(
            out_dir,
            log,
            "trace_repair_request",
            f"Ask the model to repair Blender failure {attempt + 1}",
            repair_attempt=attempt + 1,
        )
        try:
            code, response = call_code(
                config,
                system_prompt,
                feedback,
                args.timeout,
                out_dir / f"trace_response_attempt{attempt + 1}.json",
            )
            (out_dir / f"{script_path.stem}.trace{attempt + 1}.py").write_text(code)
            script_path.write_text(code)
            append_flow_event(
                out_dir,
                log,
                "trace_repair_response",
                "Received syntactically valid replacement Blender Python",
                repair_attempt=attempt + 1,
            )
        except Exception as exc:
            log["render_history"].append({
                "stage": "trace",
                "attempt": attempt + 1,
                "status": "ERR_LM_REPAIR",
                "error": f"{type(exc).__name__}: {exc}",
            })
            append_flow_event(
                out_dir,
                log,
                "trace_repair_error",
                f"{type(exc).__name__}: {exc}",
                repair_attempt=attempt + 1,
            )
            return code, False

    return code, False


def build_structure_feedback_prompt(
    *,
    original_prompt: str,
    previous_code: str,
    score: dict,
    attempt_num: int,
    max_attempts: int,
) -> str:
    """Build a user-side repair request from deterministic validation evidence."""

    issue_counts: dict[str, int] = {}
    failing_relations: list[dict] = []
    failing_part_ids: set[str] = set()
    issue_details: list[dict] = []
    seen_relations: set[tuple] = set()
    for issue in score.get("issues") or []:
        code = str(issue.get("code") or "UNKNOWN")
        issue_counts[code] = issue_counts.get(code, 0) + 1
        if issue.get("part_id") is not None:
            failing_part_ids.add(str(issue["part_id"]))
        if len(issue_details) < 32:
            issue_details.append({
                "code": code,
                "part_id": issue.get("part_id"),
                "parent": issue.get("parent", issue.get("node_a")),
                "child": issue.get("child", issue.get("node_b")),
                "message": issue.get("message"),
            })
        parent = issue.get("parent", issue.get("node_a"))
        child = issue.get("child", issue.get("node_b"))
        key = (code, parent, child)
        if key in seen_relations or len(failing_relations) >= 16:
            continue
        seen_relations.add(key)
        failing_relations.append({
            "code": code,
            "parent": parent,
            "child": child,
            "anchor_gap": issue.get("anchor_gap"),
            "anchor_tolerance": issue.get("anchor_tolerance"),
        })
    diagnostic = {
        "score": score.get("score"),
        "minimum_score": score.get("minimum_score"),
        "summary": score.get("summary"),
        "issue_counts": issue_counts,
        "failing_part_ids": sorted(failing_part_ids),
        "issues": issue_details,
        "failing_relations": failing_relations,
    }
    return f"""The previous Blender 5.0 Python script executed and rendered, but
validation_test rejected its parent-to-child structure or shared anchors.

Original object request:

<original_request>
{original_prompt}
</original_request>

Previous complete code:

<previous_code>
{previous_code}
</previous_code>

Machine-generated validation_test report:

<structural_report>
{json.dumps(diagnostic, ensure_ascii=False, indent=2)}
</structural_report>

This is structural repair attempt {attempt_num} of {max_attempts}.

Repair only the failed structural or attachment logic while preserving the
frozen visual design. The structure blueprint, not accidental helper objects in
the previous script, defines the complete semantic unit inventory. Keep its
quantities, silhouette, proportions, mesh detail, materials, colors, and
declared integrated features unchanged. If the report shows missing blueprint
parts or a PART_PARAMS schema mismatch, make PART_PARAMS and semantic Mesh
objects match the blueprint ids exactly; combine repeated visual primitives
into their declared owner Mesh without removing their visible geometry.
Otherwise do not add, remove, merge, split, rename, or replace construction
units unless a listed broken junction requires a local geometric adjustment.

Every independent non-root part needs one primary parent. Derive its parent and
child anchors from current geometry, align them, and retain surface contact.
Parent data must drive child placement. Do not fake a pass with metadata,
proximity labels, marker objects, or post-hoc nearest-surface movement.

Apply this exact implementation contract to every missing or broken primary
relation:

<shared_anchor_implementation_contract>
{SHARED_ANCHOR_IMPLEMENTATION_CONTRACT}
</shared_anchor_implementation_contract>

<native_part_parameter_contract>
{NATIVE_PART_PARAMETER_CONTRACT}
</native_part_parameter_contract>

Return the complete corrected Blender 5.0 Python script because the executor
requires a full file, but make the smallest logical change necessary. Return
code only, without prose, Markdown fences, XML tags, or explanations."""


def run_structural_validation(
    *,
    args: argparse.Namespace,
    out_dir: Path,
    script_path: Path,
    log: dict,
    attempt: int,
) -> dict:
    """Run validation_test and persist raw, scored, and readable reports."""

    out_dir.mkdir(parents=True, exist_ok=True)
    probe = (
        args.validation_test_root
        / "algorithm"
        / "runtime"
        / "blender_probe.py"
    ).resolve()
    raw_path = out_dir / f"structural_probe_attempt{attempt}.raw.json"
    score_path = out_dir / f"structural_score_attempt{attempt}.json"
    markdown_path = out_dir / f"structural_score_attempt{attempt}.md"
    append_flow_event(
        out_dir,
        log,
        "structural_validation_start",
        f"Run validation_test parent/child and shared-anchor probe, attempt {attempt}",
        attempt=attempt,
        probe=str(probe),
    )
    report = run_validation_probe(
        blender=Path(args.blender),
        probe=probe,
        script=script_path,
        output=raw_path,
        timeout=args.structure_timeout,
    )
    # The probe can fail before producing a raw file (for example on timeout).
    # Persist that failure in the same location so every attempt is auditable.
    if not raw_path.is_file():
        raw_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    expected_part_count = None
    expected_attachment_count = None
    expected_part_ids = None
    expected_attachment_pairs = None
    structure_context_path = out_dir / "structure_context.json"
    try:
        structure_context = json.loads(
            structure_context_path.read_text(encoding="utf-8")
        )
        expected_part_count = len(structure_context.get("parts") or [])
        expected_part_ids = [
            str(part.get("id"))
            for part in structure_context.get("parts") or []
            if isinstance(part, dict) and part.get("id") is not None
        ]
        expected_attachment_count = len(
            structure_context.get("attachments") or []
        )
        expected_attachment_pairs = [
            (
                str(attachment.get("parent_part_id")),
                str(attachment.get("child_part_id")),
            )
            for attachment in structure_context.get("attachments") or []
            if isinstance(attachment, dict)
            and attachment.get("parent_part_id") is not None
            and attachment.get("child_part_id") is not None
        ]
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    score = score_structure_report(
        report,
        minimum_score=args.min_structure_score,
        expected_part_ids=expected_part_ids,
        expected_attachment_pairs=expected_attachment_pairs,
        expected_part_count=expected_part_count,
        expected_attachment_count=expected_attachment_count,
    )
    part_ids = native_part_parameter_ids(script_path)
    if not part_ids:
        score.setdefault("issues", []).append({
            "severity": "error",
            "code": "MISSING_NATIVE_PART_PARAMS",
            "message": (
                "脚本没有有效的顶层字面量 PART_PARAMS；无法验证父/子尺寸变化后的锚点。"
            ),
        })
        score["passed"] = False
        score["parameter_invariance"] = {
            "mode": "missing",
            "tested_parts": 0,
            "passed_parts": 0,
            "results": [],
        }
    elif expected_part_ids is not None and set(part_ids) != set(expected_part_ids):
        missing_params = sorted(set(expected_part_ids) - set(part_ids))
        unexpected_params = sorted(set(part_ids) - set(expected_part_ids))
        score.setdefault("issues", []).append({
            "severity": "error",
            "code": "PART_PARAM_SCHEMA_MISMATCH",
            "message": (
                "PART_PARAMS 必须与结构蓝图的语义零件一一对应；"
                "装饰性辅助 Mesh 不应成为独立参数零件。"
            ),
            "missing": missing_params,
            "unexpected": unexpected_params,
        })
        score["passed"] = False
        score["parameter_invariance"] = {
            "mode": "schema_mismatch",
            "tested_parts": 0,
            "passed_parts": 0,
            "results": [],
        }
    elif score.get("passed"):
        perturbation_reports: dict[str, dict] = {}
        for part_id in part_ids[:32]:
            safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", part_id).strip("._") or "part"
            perturb_path = out_dir / (
                f"structural_probe_attempt{attempt}.scale_{safe_id}.raw.json"
            )
            variant = run_validation_probe(
                blender=Path(args.blender),
                probe=probe,
                script=script_path,
                output=perturb_path,
                timeout=args.structure_timeout,
                part_param_scales={part_id: 1.35},
            )
            if not perturb_path.is_file():
                perturb_path.write_text(
                    json.dumps(variant, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            perturbation_reports[part_id] = variant
        score = apply_parameter_invariance_gate(
            score,
            report,
            perturbation_reports,
            expected_part_ids=expected_part_ids,
            expected_attachment_pairs=expected_attachment_pairs,
            expected_part_count=expected_part_count,
            expected_attachment_count=expected_attachment_count,
        )
    score_path.write_text(
        json.dumps(score, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(score_markdown(score), encoding="utf-8")
    history_item = {
        "attempt": attempt,
        "status": "PASS" if score.get("passed") else "FAIL",
        "score": score.get("score"),
        "minimum_score": score.get("minimum_score"),
        "summary": score.get("summary"),
        "issues": score.get("issues"),
        "raw_report": raw_path.name,
        "score_report": score_path.name,
    }
    log.setdefault("structure_history", []).append(history_item)
    issue_codes = [str(item.get("code")) for item in score.get("issues") or []]
    append_flow_event(
        out_dir,
        log,
        "structural_validation_result",
        (
            f"score={score.get('score')}/100 status={history_item['status']} "
            f"issues={','.join(issue_codes) if issue_codes else 'none'}"
        ),
        attempt=attempt,
        passed=bool(score.get("passed")),
        score=score.get("score"),
        issue_codes=issue_codes,
    )
    return score


def validate_with_structure_repair(
    args: argparse.Namespace,
    config: dict,
    system_prompt: str,
    original_prompt: str,
    code: str,
    out_dir: Path,
    script_path: Path,
    log: dict,
) -> tuple[str, bool]:
    """Gate a valid render through validation_test, repairing when necessary."""

    if args.no_structure_verify:
        append_flow_event(
            out_dir,
            log,
            "structural_validation_skipped",
            "validation_test structural verification disabled by command line",
        )
        return code, True

    max_attempts = args.max_structure_retries + 1
    script_path.write_text(code)
    for attempt in range(1, max_attempts + 1):
        score = run_structural_validation(
            args=args,
            out_dir=out_dir,
            script_path=script_path,
            log=log,
            attempt=len(log.get("structure_history") or []) + 1,
        )
        if score.get("passed"):
            log.pop("failure_stage", None)
            append_flow_event(
                out_dir,
                log,
                "structural_validation_passed",
                "Parent/child hierarchy and authored shared anchors passed validation_test",
                score=score.get("score"),
            )
            return code, True

        if attempt == max_attempts:
            log["failure_stage"] = "structure"
            append_flow_event(
                out_dir,
                log,
                "structural_repair_exhausted",
                "All validation_test structural repair attempts were exhausted",
                score=score.get("score"),
            )
            return code, False

        feedback = build_structure_feedback_prompt(
            original_prompt=original_prompt,
            previous_code=code,
            score=score,
            attempt_num=attempt + 1,
            max_attempts=max_attempts,
        )
        repair_number = len(log.get("structure_history") or [])
        (out_dir / f"structural_feedback_attempt{repair_number}.txt").write_text(
            feedback,
            encoding="utf-8",
        )
        append_flow_event(
            out_dir,
            log,
            "structural_repair_request",
            "Ask the model to repair validation_test structural failures",
            repair_attempt=attempt,
        )
        try:
            repair_config = dict(config)
            if config.get("structure_repair_max_output_tokens") is not None:
                repair_config["max_output_tokens"] = config[
                    "structure_repair_max_output_tokens"
                ]
            if config.get("structure_repair_reasoning_effort"):
                repair_config["reasoning_effort"] = config[
                    "structure_repair_reasoning_effort"
                ]
            code, response = call_code(
                repair_config,
                system_prompt,
                feedback,
                args.timeout,
                out_dir / f"structural_response_attempt{repair_number}.json",
            )
            candidate = out_dir / f"{script_path.stem}.structural{repair_number}.py"
            candidate.write_text(code, encoding="utf-8")
            script_path.write_text(code, encoding="utf-8")
            append_flow_event(
                out_dir,
                log,
                "structural_repair_response",
                "Received syntactically valid structural replacement code",
                repair_attempt=attempt,
            )
        except Exception as exc:
            log["failure_stage"] = "structure"
            append_flow_event(
                out_dir,
                log,
                "structural_repair_error",
                f"{type(exc).__name__}: {exc}",
                repair_attempt=attempt,
            )
            return code, False

        code, render_ok = validate_with_trace_repair(
            args=args,
            config=config,
            system_prompt=system_prompt,
            original_prompt=original_prompt,
            code=code,
            out_dir=out_dir,
            script_path=script_path,
            log=log,
        )
        if not render_ok:
            log["failure_stage"] = "render"
            return code, False

    log["failure_stage"] = "structure"
    return code, False


def visual_feedback_loop(
    args: argparse.Namespace,
    config: dict,
    system_prompt: str,
    original_prompt: str,
    code: str,
    out_dir: Path,
    script_path: Path,
    log: dict,
) -> tuple[str, bool]:
    if args.max_visual_iterations <= 0:
        return code, True

    visual_system_prompt = critique_system_prompt("text_to_3d")
    baseline_render_dir = None
    if args.visual_baseline_dir is not None:
        candidate = args.visual_baseline_dir
        if (candidate / "renders").is_dir():
            candidate = candidate / "renders"
        if candidate.is_dir():
            baseline_render_dir = candidate
    for iteration in range(1, args.max_visual_iterations + 1):
        append_flow_event(
            out_dir,
            log,
            "visual_feedback_start",
            f"Visual feedback iteration {iteration}/{args.max_visual_iterations}",
            iteration=iteration,
        )
        user_content = build_critique_user_content(
            original_user_content=original_prompt,
            prev_code=code,
            render_dir=out_dir / "renders",
            iter_num=iteration,
            max_iter=args.max_visual_iterations,
            task="text_to_3d",
            baseline_render_dir=baseline_render_dir,
        )
        try:
            retries = max(0, int(config.get("api_retries", 0)))
            response = None
            for api_attempt in range(retries + 1):
                try:
                    response_path = (
                        out_dir / f"visual_response_iter{iteration}.json"
                    )
                    response = call_configured_model_api(
                        config=config,
                        system_prompt=visual_system_prompt,
                        user_prompt=user_content,
                        timeout=args.timeout,
                        response_path=response_path,
                    )
                    break
                except (RuntimeError, urllib.error.URLError, TimeoutError) as exc:
                    if not safe_to_retry_api_error(exc) or api_attempt >= retries:
                        raise
                    time.sleep(2 ** api_attempt)
            assert response is not None
            persist_response(response_path, response)
            text = extract_message(response)
            decision, assessment, fixed_code = parse_critique_response(text)
            if assessment:
                (out_dir / f"visual_assessment_iter{iteration}.txt").write_text(assessment + "\n")
        except Exception as exc:
            log["visual_history"].append({
                "iteration": iteration,
                "status": "ERR_VISUAL_CALL",
                "error": f"{type(exc).__name__}: {exc}",
            })
            append_flow_event(
                out_dir,
                log,
                "visual_feedback_error",
                f"{type(exc).__name__}: {exc}",
                iteration=iteration,
            )
            return code, True

        append_flow_event(
            out_dir,
            log,
            "visual_feedback_decision",
            f"Visual model decision: {decision}",
            iteration=iteration,
            decision=decision,
        )

        if decision == "DONE":
            log["visual_history"].append({
                "iteration": iteration,
                "status": "DONE",
                "assessment": assessment,
            })
            append_flow_event(
                out_dir,
                log,
                "visual_feedback_complete",
                "Visual model accepted the current rendered model",
                iteration=iteration,
            )
            return code, True

        if decision != "FIX" or not fixed_code:
            log["visual_history"].append({
                "iteration": iteration,
                "status": "ERR_VISUAL_PARSE",
                "assessment": assessment,
            })
            append_flow_event(
                out_dir,
                log,
                "visual_feedback_unusable",
                "Visual response did not contain a usable fix; current valid render is retained",
                iteration=iteration,
            )
            return code, True

        try:
            fixed_code = strip_code_fence(fixed_code)
            ast.parse(fixed_code)
        except SyntaxError as exc:
            log["visual_history"].append({
                "iteration": iteration,
                "status": "ERR_VISUAL_CODE_PARSE",
                "error": f"SyntaxError: {exc}",
            })
            append_flow_event(
                out_dir,
                log,
                "visual_fix_parse_error",
                f"SyntaxError: {exc}",
                iteration=iteration,
            )
            return code, True

        archive_renders(out_dir, f"visual_iter{iteration}_before")
        (out_dir / f"{script_path.stem}.visual{iteration}.py").write_text(fixed_code)
        append_flow_event(
            out_dir,
            log,
            "visual_fix_adopted",
            "Visual feedback produced valid Python; re-enter Blender validation",
            iteration=iteration,
        )
        fixed_code, render_ok = validate_with_trace_repair(
            args=args,
            config=config,
            system_prompt=system_prompt,
            original_prompt=original_prompt,
            code=fixed_code,
            out_dir=out_dir,
            script_path=script_path,
            log=log,
        )
        code = fixed_code
        structure_ok = False
        if render_ok:
            code, structure_ok = validate_with_structure_repair(
                args=args,
                config=config,
                system_prompt=system_prompt,
                original_prompt=original_prompt,
                code=code,
                out_dir=out_dir,
                script_path=script_path,
                log=log,
            )
        log["visual_history"].append({
            "iteration": iteration,
            "status": (
                "FIX_APPLIED"
                if render_ok and structure_ok
                else ("FIX_STRUCTURE_FAILED" if render_ok else "FIX_RENDER_FAILED")
            ),
            "assessment": assessment,
        })
        if not render_ok or not structure_ok:
            return code, False

    return code, True


def write_failure(out_dir: Path, instance: str, message: str, response: dict | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "error.txt").write_text(message)
    if response is not None:
        (out_dir / "response.json").write_text(json.dumps(response, indent=2))
    print(f"[ERR] {instance}: {message}", flush=True)


def main() -> None:
    args = parse_args()
    args.config = args.config.expanduser().resolve()
    args.data_dir = args.data_dir.expanduser().resolve()
    args.output_dir = args.output_dir.expanduser().resolve()
    args.structure_context_dir = args.structure_context_dir.expanduser().resolve()
    args.system_prompt = args.system_prompt.expanduser().resolve()
    args.validation_test_root = args.validation_test_root.expanduser().resolve()
    if args.visual_baseline_dir is not None:
        args.visual_baseline_dir = args.visual_baseline_dir.expanduser().resolve()
    try:
        output_instance_name("probe", args.output_prefix, args.output_suffix)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    args.blender = HARD_CODED_BLENDER
    config = load_config(args.config)
    if config.get("code_max_output_tokens") is not None:
        config["max_output_tokens"] = config["code_max_output_tokens"]
    if config.get("code_reasoning_effort"):
        config["reasoning_effort"] = config["code_reasoning_effort"]
    if args.model:
        config["model"] = args.model
    system_prompt = args.system_prompt.read_text(encoding="utf-8")
    instances = iter_instances(args.data_dir, args.instances)
    validation_probe = (
        args.validation_test_root / "algorithm" / "runtime" / "blender_probe.py"
    )
    if (
        not args.no_render_verify
        and not args.no_structure_verify
        and not validation_probe.is_file()
    ):
        raise SystemExit(
            "Missing validation_test runtime probe: "
            f"{validation_probe.resolve()}"
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    run_manifest = {
        "schema_version": "stage7-run-manifest/v1",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "pipeline": "copied_3dcodebench_lmstudio_text_to_3d",
        "inherits_structgen3d": False,
        "inherits_stage_2_to_6": False,
        "system_prompt": {
            "path": str(args.system_prompt.resolve()),
            "characters": len(system_prompt),
            "sha256": sha256_text(system_prompt),
            "role": "system",
            "modified_by_stage7": False,
        },
        "effective_system_prompt": {
            "path": None,
            "characters": len(system_prompt),
            "sha256": sha256_text(system_prompt),
            "identical_to_base": True,
        },
        "structure_context": {
            "directory": str(args.structure_context_dir.resolve()),
            "source": "extract_structure.py output",
            "message_role": "user",
            "injection": "direct_json_context",
        },
        "structural_validation": {
            "enabled": not args.no_structure_verify,
            "validation_test_root": str(args.validation_test_root.resolve()),
            "probe": str(validation_probe.resolve()),
            "minimum_score": args.min_structure_score,
            "repair_rounds": args.max_structure_retries,
            "timeout_seconds": args.structure_timeout,
        },
        "visual_baseline": (
            str(args.visual_baseline_dir.resolve())
            if args.visual_baseline_dir is not None
            else None
        ),
        "flow": [
            "load benchmark text prompt",
            "load and validate extracted structure JSON",
            "inject description plus structure JSON as ordinary user context",
            "initial model generation",
            "Python syntax validation",
            "Blender 5.0 render validation",
            "traceback repair only after render failure",
            "validation_test parent/child and shared-anchor scoring",
            "structural repair followed by Blender and validation_test reruns",
            "visual feedback only after a valid render",
            "revalidate any visual fix in Blender 5.0 and validation_test",
            "write final status and chronological logs",
        ],
        "model": config["model"],
        "api_format": config.get("api_format", API_FORMAT_LMSTUDIO),
        "openai_background": (
            bool(config.get("openai_background", True))
            if config.get("api_format") == API_FORMAT_OPENAI_RESPONSES
            else False
        ),
        "openai_poll_interval": config.get("openai_poll_interval", 5.0),
        "openai_request_timeout": config.get("openai_request_timeout", 60),
        "output_prefix": args.output_prefix,
        "output_suffix": args.output_suffix,
        "instances": [path.name for path in instances],
    }

    print(f"Model: {config['model']}", flush=True)
    print(
        f"API format: {config.get('api_format', API_FORMAT_LMSTUDIO)}",
        flush=True,
    )
    print(f"Instances: {len(instances)}", flush=True)
    print(f"Output: {args.output_dir}", flush=True)
    print(f"Output prefix: {args.output_prefix or '(none)'}", flush=True)
    print(f"Output suffix: {args.output_suffix or '(none)'}", flush=True)
    print(f"System prompt: {len(system_prompt)} chars (unchanged base)", flush=True)
    print("Effective system prompt identical to base: True", flush=True)
    print(f"Structure user context: {args.structure_context_dir.resolve()}", flush=True)
    print(f"Render verify: {not args.no_render_verify}", flush=True)
    if not args.no_render_verify:
        print(f"Trace retries: {args.max_trace_retries}", flush=True)
        print(f"Structural verify: {not args.no_structure_verify}", flush=True)
        if not args.no_structure_verify:
            print(f"validation_test: {args.validation_test_root.resolve()}", flush=True)
            print(f"Minimum structural score: {args.min_structure_score}", flush=True)
            print(f"Structural retries: {args.max_structure_retries}", flush=True)
        print(f"Visual iterations: {args.max_visual_iterations}", flush=True)
        print(
            "Visual baseline: "
            + (
                str(args.visual_baseline_dir.resolve())
                if args.visual_baseline_dir is not None
                else "(none)"
            ),
            flush=True,
        )

    ok = skipped = failed = 0
    for index, instance_dir in enumerate(instances, start=1):
        name = instance_dir.name
        output_name = output_instance_name(
            name,
            args.output_prefix,
            args.output_suffix,
        )
        prompt_path = instance_dir / f"prompt_{args.prompt_type}.txt"
        out_dir = args.output_dir / output_name
        script_path = out_dir / f"{output_name}.py"
        log_path = out_dir / "log.json"

        resuming_existing = bool(args.resume_existing and script_path.is_file())
        if script_path.exists() and not args.overwrite and not resuming_existing:
            skipped += 1
            print(f"[SKIP] {index}/{len(instances)} {name}", flush=True)
            continue
        if out_dir.exists() and args.overwrite:
            clear_generation_artifacts(out_dir)
        if not prompt_path.exists():
            failed += 1
            write_failure(out_dir, name, f"Missing {prompt_path.name}")
            continue

        prompt = prompt_path.read_text().strip()
        try:
            structure_blueprint, structure_path = load_structure_context(
                args.structure_context_dir,
                name,
                output_name,
            )
        except (FileNotFoundError, OSError, ValueError) as exc:
            failed += 1
            write_failure(out_dir, name, f"{type(exc).__name__}: {exc}")
            continue
        generation_user_prompt = compose_generation_user_prompt(
            prompt,
            structure_blueprint,
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        effective_prompt_path = out_dir / "effective_system_prompt.txt"
        effective_prompt_path.write_text(system_prompt, encoding="utf-8")
        seed_manifest = json.loads(json.dumps(run_manifest))
        seed_manifest["effective_system_prompt"]["path"] = str(
            effective_prompt_path.resolve()
        )
        seed_manifest["structure_context"]["directory"] = str(
            structure_path.parent.resolve()
        )
        seed_manifest["instances"] = [name]
        seed_manifest["output_instance"] = output_name
        (out_dir / "run_manifest.json").write_text(
            json.dumps(seed_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_dir / "prompt.txt").write_text(prompt + "\n")
        (out_dir / "structure_context.json").write_text(
            json.dumps(structure_blueprint, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_dir / "effective_user_prompt.txt").write_text(
            generation_user_prompt + "\n",
            encoding="utf-8",
        )
        if resuming_existing and log_path.is_file():
            try:
                log = json.loads(log_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                log = {}
        else:
            log = {}
        log.update(
            {
                "schema_version": "stage7-instance-log/v1",
                "instance": name,
                "output_instance": output_name,
                "model": config["model"],
                "api_format": config.get("api_format", API_FORMAT_LMSTUDIO),
                "status": None,
                "pipeline": "copied_3dcodebench_lmstudio_text_to_3d",
                "inherits_stage_2_to_6": False,
                "effective_system_prompt_identical_to_base": True,
                "structure_context": {
                    "path": str(structure_path.resolve()),
                    "role": "user",
                    "sha256": sha256_text(
                        json.dumps(
                            structure_blueprint,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                    ),
                    "parts": len(structure_blueprint.get("parts") or []),
                    "attachments": len(structure_blueprint.get("attachments") or []),
                },
            }
        )
        for history_key in (
            "render_history",
            "structure_history",
            "visual_history",
            "flow_events",
        ):
            log.setdefault(history_key, [])
        log.pop("error", None)
        log.pop("failure_stage", None)
        append_flow_event(
            out_dir,
            log,
            "instance_resume" if resuming_existing else "instance_start",
            (
                "Resume existing Blender Python without a new initial model request"
                if resuming_existing
                else "Loaded one 3DCodeBench text-to-3D instance"
            ),
        )
        append_flow_event(
            out_dir,
            log,
            "prompt_loaded",
            (
                f"Loaded {prompt_path.name} and validated ordinary user structure "
                f"context with {len(structure_blueprint.get('parts') or [])} parts"
            ),
        )

        response = None
        last_error = None
        generated = False
        if resuming_existing:
            try:
                code = script_path.read_text(encoding="utf-8")
                ast.parse(code)
                generated = True
                append_flow_event(
                    out_dir,
                    log,
                    "initial_generation_resumed",
                    "Loaded existing canonical Python and passed syntax validation",
                    code_characters=len(code),
                )
            except (OSError, SyntaxError) as exc:
                append_flow_event(
                    out_dir,
                    log,
                    "initial_generation_resume_error",
                    f"{type(exc).__name__}: {exc}",
                )
        for attempt in range(args.retries + 1) if not generated else ():
            append_flow_event(
                out_dir,
                log,
                "initial_generation_start",
                f"Initial model generation attempt {attempt + 1}/{args.retries + 1}",
                attempt=attempt + 1,
            )
            try:
                code, response = call_code(
                    config,
                    system_prompt,
                    generation_user_prompt,
                    args.timeout,
                    out_dir / f"response_initial_attempt{attempt + 1}.json",
                )
                script_path.write_text(code)
                persist_response(out_dir / "response_initial.json", response)
                generated = True
                append_flow_event(
                    out_dir,
                    log,
                    "initial_generation_valid",
                    "Model response was received and passed Python syntax validation",
                    attempt=attempt + 1,
                    code_characters=len(code),
                )
                break
            except (RuntimeError, urllib.error.URLError, TimeoutError, ValueError, SyntaxError) as exc:
                last_error = exc
                append_flow_event(
                    out_dir,
                    log,
                    "initial_generation_error",
                    f"{type(exc).__name__}: {exc}",
                    attempt=attempt + 1,
                )
                safe_to_retry = (
                    isinstance(exc, (ValueError, SyntaxError))
                    or safe_to_retry_api_error(exc)
                )
                if safe_to_retry and attempt < args.retries:
                    time.sleep(2 ** attempt)
                    continue
                failed += 1
                message = f"{type(exc).__name__}: {exc}"
                write_failure(out_dir, name, message, response)
                log["status"] = (
                    "ERR_GENERATE_AMBIGUOUS_REMOTE"
                    if isinstance(exc, AmbiguousRemoteResultError)
                    else "ERR_GENERATE"
                )
                log["error"] = message
                append_flow_event(
                    out_dir,
                    log,
                    "instance_complete",
                    "Initial generation failed after all retries",
                    status=log["status"],
                )
                break

        if not generated:
            continue

        if args.no_render_verify:
            log["status"] = "OK_NO_RENDER_VERIFY"
            ok += 1
            print(f"[OK] {index}/{len(instances)} {name}", flush=True)
            append_flow_event(
                out_dir,
                log,
                "instance_complete",
                "Generation finished without Blender validation by explicit request",
                status=log["status"],
            )
            if args.sleep:
                time.sleep(args.sleep)
            continue

        code, render_ok = validate_with_trace_repair(
            args=args,
            config=config,
            system_prompt=system_prompt,
            original_prompt=generation_user_prompt,
            code=code,
            out_dir=out_dir,
            script_path=script_path,
            log=log,
        )
        structure_ok = False
        if render_ok:
            code, structure_ok = validate_with_structure_repair(
                args=args,
                config=config,
                system_prompt=system_prompt,
                original_prompt=generation_user_prompt,
                code=code,
                out_dir=out_dir,
                script_path=script_path,
                log=log,
            )
        final_ok = bool(render_ok and structure_ok)
        if final_ok:
            code, final_ok = visual_feedback_loop(
                args=args,
                config=config,
                system_prompt=system_prompt,
                original_prompt=generation_user_prompt,
                code=code,
                out_dir=out_dir,
                script_path=script_path,
                log=log,
            )

        if final_ok:
            ok += 1
            log["status"] = "OK"
            print(f"[OK] {index}/{len(instances)} {name}", flush=True)
        else:
            failed += 1
            if log.get("failure_stage") == "structure":
                log["status"] = "ERR_STRUCTURE_REPAIR_EXHAUSTED"
                detail = "validation_test structural repair exhausted"
            else:
                log["status"] = "ERR_RENDER_REPAIR_EXHAUSTED"
                detail = "render repair exhausted"
            print(f"[ERR] {index}/{len(instances)} {name}: {detail}", flush=True)
        append_flow_event(
            out_dir,
            log,
            "instance_complete",
            "Stage 7 instance finished",
            status=log["status"],
        )

        if args.sleep:
            time.sleep(args.sleep)

    print(f"Done. ok={ok} skipped={skipped} failed={failed}", flush=True)


if __name__ == "__main__":
    main()
