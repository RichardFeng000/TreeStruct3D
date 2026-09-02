#!/usr/bin/env python3
"""Extract TreeStruct3D structure blueprints without generating Blender code."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from treestruct3d.structure_extraction import (
    blueprint_markdown,
    extract_json_object,
    validate_blueprint,
)
from generate_3d import (
    AmbiguousRemoteResultError,
    API_FORMAT_LMSTUDIO,
    DEFAULT_CONFIG,
    DEFAULT_DATA_DIR,
    DEFAULT_OUTPUT_DIR,
    REPO_ROOT,
    call_configured_model_api,
    extract_message,
    load_config,
    output_instance_name,
    persist_response,
    safe_to_retry_api_error,
    sha256_text,
)


DEFAULT_EXTRACTION_PROMPT = (
    REPO_ROOT
    / "prompts"
    / "structure_blueprint_system_prompt.txt"
)
DEFAULT_EXTRACTION_OUTPUT = DEFAULT_OUTPUT_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Use a planning model to extract parent/child and anchor structure "
            "from 3DCodeBench text prompts. This does not generate Blender code."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Provider and model configuration (default: config.local.yaml).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the extraction model; use the strongest available planner.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing 3DCodeBench instance directories.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_EXTRACTION_OUTPUT,
        help="Root directory for structure-blueprint artifacts.",
    )
    parser.add_argument(
        "--output-prefix",
        default="",
        help=(
            "Prefix for the result instance directory, for example "
            "kimi_k3_. Extraction files are stored only under "
            "<output-dir>/<prefix><instance>/structure_extraction/."
        ),
    )
    parser.add_argument(
        "--output-suffix",
        default="",
        help=(
            "Suffix for the result instance directory, for example (1). "
            "Use the same suffix for extraction and generation."
        ),
    )
    parser.add_argument(
        "--system-prompt",
        type=Path,
        default=DEFAULT_EXTRACTION_PROMPT,
        help="Dedicated extraction prompt; never injected into Blender generation.",
    )
    parser.add_argument(
        "--prompt-type",
        choices=("description", "instruction"),
        default="description",
    )
    parser.add_argument("--instances", nargs="*", default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--api-timeout",
        "--timeout",
        dest="timeout",
        type=int,
        default=0,
        help=(
            "Total model API wall-clock timeout in seconds; 0 means no "
            "client-side limit. The old --timeout spelling remains accepted."
        ),
    )
    parser.add_argument(
        "--extraction-retries",
        "--retries",
        dest="retries",
        type=int,
        default=2,
        help=(
            "Retries after a safely retryable API error or invalid blueprint. "
            "The old --retries spelling remains accepted."
        ),
    )
    parser.add_argument(
        "--request-delay",
        "--sleep",
        dest="sleep",
        type=float,
        default=0.0,
        help=(
            "Delay in seconds between completed instances. The old --sleep "
            "spelling remains accepted."
        ),
    )
    return parser.parse_args()


def iter_instances(data_dir: Path, selected: list[str] | None) -> list[Path]:
    if selected:
        instances = [data_dir / item for item in selected]
    else:
        instances = sorted(path for path in data_dir.iterdir() if path.is_dir())
    missing = [path.name for path in instances if not path.is_dir()]
    if missing:
        raise SystemExit(f"Missing benchmark instances: {', '.join(missing)}")
    return instances


def initial_user_prompt(instance: str, description: str) -> str:
    return f"""Extract a connected procedural-assembly structure blueprint for this
benchmark instance.

Exercise full category-general judgment. First choose the decomposition for
visual fidelity and parameter control without considering anchors. Freeze that
inventory, then annotate its parent-child relations and shared anchors. Do not
use a fixed part library or optimize the decomposition for graph score.

Instance label: {instance}

Object description:

<object_description>
{description}
</object_description>

Return the required JSON object only."""


def repair_user_prompt(
    instance: str,
    description: str,
    previous_text: str,
    errors: list[str],
) -> str:
    return f"""Repair the invalid structure extraction below. Preserve the object
description and the previous visual decomposition inventory, quantities,
geometry summaries, representation reasons, and integrated features. Correct
only schema and graph annotation errors unless an inventory item itself is
invalid. Return one complete JSON object only.

Instance label: {instance}

Object description:

<object_description>
{description}
</object_description>

Previous extraction:

<previous_extraction>
{previous_text[:30000]}
</previous_extraction>

Validation errors:

{json.dumps(errors, ensure_ascii=False, indent=2)}"""


def write_log(out_dir: Path, log: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "extraction_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def append_attempt(log: dict, **fields: object) -> None:
    log.setdefault("attempts", []).append(
        {
            "attempt": len(log.get("attempts") or []) + 1,
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat(
                timespec="seconds"
            ),
            **fields,
        }
    )


def extract_one(
    *,
    config: dict,
    system_prompt: str,
    instance: str,
    description: str,
    out_dir: Path,
    timeout: int,
    retries: int,
) -> tuple[dict | None, dict]:
    log = {
        "schema_version": "treestruct3d.structure-extraction-log/v1",
        "instance": instance,
        "model": config["model"],
        "api_format": config.get("api_format", API_FORMAT_LMSTUDIO),
        "status": None,
        "input": "prompt_description_only",
        "reads_reference_python": False,
        "attempts": [],
    }
    (out_dir / "source_prompt.txt").write_text(description + "\n", encoding="utf-8")
    user_prompt = initial_user_prompt(instance, description)
    previous_text = ""
    for attempt in range(1, retries + 2):
        response_path = out_dir / f"response_attempt{attempt}.json"
        try:
            response = call_configured_model_api(
                config=config,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout=timeout,
                response_path=response_path,
            )
            persist_response(response_path, response)
            previous_text = extract_message(response)
            (out_dir / f"extraction_attempt{attempt}.txt").write_text(
                previous_text + "\n",
                encoding="utf-8",
            )
            blueprint = extract_json_object(previous_text)
            errors = validate_blueprint(blueprint)
            if not errors:
                append_attempt(log, status="VALID", errors=[])
                log["status"] = "OK"
                log["parts"] = len(blueprint.get("parts") or [])
                log["attachments"] = len(blueprint.get("attachments") or [])
                write_log(out_dir, log)
                return blueprint, log
            append_attempt(log, status="INVALID_BLUEPRINT", errors=errors)
        except AmbiguousRemoteResultError as exc:
            errors = [f"{type(exc).__name__}: {exc}"]
            append_attempt(log, status="AMBIGUOUS_REMOTE_RESULT", errors=errors)
            log["status"] = "ERR_EXTRACTION_AMBIGUOUS_REMOTE"
            log["errors"] = errors
            write_log(out_dir, log)
            return None, log
        except (RuntimeError, urllib.error.URLError, TimeoutError) as exc:
            errors = [f"{type(exc).__name__}: {exc}"]
            append_attempt(log, status="EXTRACTION_ERROR", errors=errors)
            if not safe_to_retry_api_error(exc):
                log["status"] = "ERR_EXTRACTION_API_UNCERTAIN"
                log["errors"] = errors
                write_log(out_dir, log)
                return None, log
        except Exception as exc:
            errors = [f"{type(exc).__name__}: {exc}"]
            append_attempt(log, status="EXTRACTION_ERROR", errors=errors)
        write_log(out_dir, log)
        if attempt > retries:
            log["status"] = "ERR_EXTRACTION_INVALID"
            log["errors"] = errors
            write_log(out_dir, log)
            return None, log
        user_prompt = repair_user_prompt(
            instance,
            description,
            previous_text,
            errors,
        )
        time.sleep(min(2 ** (attempt - 1), 4))
    return None, log


def extraction_output_dir(
    output_root: Path,
    instance: str,
    output_prefix: str,
    output_suffix: str = "",
) -> Path:
    """Keep every extraction artifact inside its model-specific seed result."""

    return (
        output_root
        / output_instance_name(instance, output_prefix, output_suffix)
        / "structure_extraction"
    )


def write_seed_catalog(out_dir: Path, instance: str, blueprint: dict) -> None:
    """Write a machine-readable catalog record beside its source extraction."""

    record = {"instance": instance, "blueprint": blueprint}
    (out_dir / "structure_catalog.jsonl").write_text(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    try:
        output_instance_name("probe", args.output_prefix, args.output_suffix)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    config = load_config(args.config)
    if config.get("structure_max_output_tokens") is not None:
        config["max_output_tokens"] = config["structure_max_output_tokens"]
    if config.get("structure_reasoning_effort"):
        config["reasoning_effort"] = config["structure_reasoning_effort"]
    if args.model:
        config["model"] = args.model
    system_prompt = args.system_prompt.read_text(encoding="utf-8")
    instances = iter_instances(args.data_dir, args.instances)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "treestruct3d.structure-extraction-manifest/v1",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(
            timespec="seconds"
        ),
        "model": config["model"],
        "input": "3DCodeBench natural-language prompt only",
        "reads_reference_python": False,
        "injected_into_generation": False,
        "system_prompt": {
            "path": str(args.system_prompt.resolve()),
            "sha256": sha256_text(system_prompt),
        },
        "instances": [path.name for path in instances],
    }
    ok = skipped = failed = 0
    for index, instance_dir in enumerate(instances, start=1):
        instance = instance_dir.name
        prompt_path = instance_dir / f"prompt_{args.prompt_type}.txt"
        out_dir = extraction_output_dir(
            args.output_dir,
            instance,
            args.output_prefix,
            args.output_suffix,
        )
        structure_path = out_dir / "structure.json"
        if structure_path.is_file() and not args.overwrite:
            skipped += 1
            print(f"[SKIP] {index}/{len(instances)} {instance}", flush=True)
            continue
        if not prompt_path.is_file():
            failed += 1
            print(f"[ERR] {index}/{len(instances)} {instance}: missing prompt", flush=True)
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        seed_manifest = {
            **manifest,
            "instance": instance,
            "output_instance": output_instance_name(
                instance,
                args.output_prefix,
                args.output_suffix,
            ),
            "output_prefix": args.output_prefix,
            "output_suffix": args.output_suffix,
        }
        (out_dir / "extraction_manifest.json").write_text(
            json.dumps(seed_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        description = prompt_path.read_text(encoding="utf-8").strip()
        blueprint, _ = extract_one(
            config=config,
            system_prompt=system_prompt,
            instance=instance,
            description=description,
            out_dir=out_dir,
            timeout=args.timeout,
            retries=args.retries,
        )
        if blueprint is None:
            failed += 1
            print(f"[ERR] {index}/{len(instances)} {instance}: invalid extraction", flush=True)
            continue
        structure_path.write_text(
            json.dumps(blueprint, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_dir / "structure.md").write_text(
            blueprint_markdown(blueprint),
            encoding="utf-8",
        )
        write_seed_catalog(out_dir, instance, blueprint)
        ok += 1
        print(
            f"[OK] {index}/{len(instances)} {instance}: "
            f"parts={len(blueprint.get('parts') or [])} "
            f"attachments={len(blueprint.get('attachments') or [])}",
            flush=True,
        )
        if args.sleep:
            time.sleep(args.sleep)

    print(
        f"Done. ok={ok} skipped={skipped} failed={failed}",
        flush=True,
    )


if __name__ == "__main__":
    main()
