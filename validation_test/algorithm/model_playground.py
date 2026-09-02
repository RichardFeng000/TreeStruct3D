#!/usr/bin/env python3
"""Local parameter editor and Blender-to-GLB preview server.

The browser UI never executes Blender Python directly.  It sends a bounded
request to this localhost server, which runs the selected benchmark script in
Blender, exports a fresh GLB, and returns that model to the Three.js viewer.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import mimetypes
import os
import subprocess
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    from .code_structure_tree import SourceStructure, _interactive_data
except ImportError:  # Support direct execution: python3 algorithm/model_playground.py
    from code_structure_tree import SourceStructure, _interactive_data


ALGORITHM_DIR = Path(__file__).resolve().parent
APP_DIR = ALGORITHM_DIR.parent
FRONTEND_DIR = APP_DIR / "frontend"
DATASETS_DIR = APP_DIR / "datasets"
DEFAULT_BENCHMARK = DATASETS_DIR / "benchmark" / "categories"
DEFAULT_STAGE1_OUTPUT = DATASETS_DIR / "stage1_output"
DEFAULT_STAGE1_GPT56_SOL = DATASETS_DIR / "stage1_output_openai5.6sol"
DEFAULT_BLENDER = Path(
    "/Users/fengruiding/Downloads/3d_code/tools/"
    "Blender-5.0.app/Contents/MacOS/Blender"
)
PINNED_BLENDER_VERSION = "5.0.0"
RUNTIME_GRAPH_VERSION = "9-native-anchor-edges-only"
NATIVE_PART_PARAMS_NAME = "PART_PARAMS"
RENDER_WORKER_VERSION = "9-semantic-highlight-overlays"
RUNTIME_GRAPH_PROBE = ALGORITHM_DIR / "runtime" / "blender_probe.py"
DEFAULT_CACHE = APP_DIR / ".model_playground_cache"
MAX_REQUEST_BYTES = 256 * 1024

BIRD_PART_CREATORS = {
    "body": "create_nurbs_body",
    "head": "create_head",
    "beak": "create_beak_part",
    "eye": "create_eye",
    "wing": "create_wing",
    "tail": "create_tail",
    "leg": "create_leg",
    "foot": "create_foot_legacy",
}


@dataclass(frozen=True)
class ModelEntry:
    source_id: str
    model_id: str
    label: str
    source: Path


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve a local parameter editor with live Blender previews."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument(
        "--dataset",
        type=Path,
        action="append",
        help=(
            "extra dataset root, one model directory, or one canonical Python file; "
            "repeat the option to expose multiple sources; the first becomes "
            "the initially selected source"
        ),
    )
    parser.add_argument(
        "--dataset-label",
        action="append",
        help=(
            "browser label for the matching --dataset (defaults to the path name); "
            "repeat in the same order as --dataset"
        ),
    )
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--open", action="store_true", help="open the browser")
    parser.add_argument("--render-timeout", type=int, default=60)
    return parser.parse_args()


def _model_catalog(root: Path, source_id: str) -> dict[str, ModelEntry]:
    """Catalog canonical model scripts from a dataset, model folder, or file."""
    root = root.resolve()
    entries: dict[str, ModelEntry] = {}

    if root.is_file():
        if root.suffix == ".py":
            model_id = f"{root.stem}/{root.stem}"
            entries[model_id] = ModelEntry(
                source_id,
                model_id,
                root.stem,
                root,
            )
        return entries

    direct_source = root / f"{root.name}.py"
    if direct_source.is_file():
        model_id = f"{root.name}/{root.name}"
        entries[model_id] = ModelEntry(
            source_id,
            model_id,
            root.name,
            direct_source.resolve(),
        )
        return entries

    for model_dir in sorted(path for path in root.glob("*") if path.is_dir()):
        source = model_dir / f"{model_dir.name}.py"
        if not source.is_file():
            continue
        relative = source.relative_to(root).as_posix()
        model_id = relative.removesuffix(".py")
        entries[model_id] = ModelEntry(
            source_id,
            model_id,
            source.stem,
            source.resolve(),
        )
    return entries


def _literal_value(node: ast.AST) -> Any:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return None
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return None


def _numeric_bounds(value: int | float) -> tuple[float, float, float]:
    number = float(value)
    if isinstance(value, int) and not isinstance(value, bool):
        span = max(abs(value), 4)
        return float(max(0, value - span)), float(value + span), 1.0
    if abs(number) < 1e-10:
        return -1.0, 1.0, 0.01
    span = max(abs(number) * 1.5, 0.1)
    step = max(abs(number) / 100.0, 0.001)
    return number - span, number + span, step


def _boolean_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "off", "no"}
    return bool(value)


def _source_controls(source: Path) -> list[dict[str, Any]]:
    """Expose simple globals and ``main`` defaults without executing source."""
    try:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []

    found: dict[str, tuple[Any, str]] = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value_node = node.value
            value = _literal_value(value_node)
            if value is None and not isinstance(value_node, ast.Constant):
                continue
            for target in targets:
                if (
                    isinstance(target, ast.Name)
                    and not target.id.startswith("_")
                    and target.id != NATIVE_PART_PARAMS_NAME
                    and isinstance(value, (str, int, float, bool, type(None)))
                ):
                    found[f"global:{target.id}"] = (value, target.id)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main":
            positional = [*node.args.posonlyargs, *node.args.args]
            offset = len(positional) - len(node.args.defaults)
            for argument, default in zip(positional[offset:], node.args.defaults):
                value = _literal_value(default)
                if value is None and not isinstance(default, ast.Constant):
                    continue
                found[f"main:{argument.arg}"] = (value, f"main.{argument.arg}")

    controls: list[dict[str, Any]] = []
    for key, (value, label) in list(found.items())[:80]:
        control: dict[str, Any] = {
            "id": f"source_override:{key}",
            "label": label,
            "group": "代码参数",
            "value": value,
        }
        if isinstance(value, bool):
            control["type"] = "checkbox"
        elif isinstance(value, (int, float)):
            low, high, step = _numeric_bounds(value)
            control.update(type="number", min=low, max=high, step=step)
        elif value is None:
            control.update(type="text", value="")
        else:
            control["type"] = "text"
        controls.append(control)
    return controls


def _native_part_params(source: Path) -> dict[str, dict[str, Any]]:
    """Read Stage7's literal, category-neutral native parameter protocol."""

    try:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name) and target.id == NATIVE_PART_PARAMS_NAME
            for target in targets
        ):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError, SyntaxError):
            return {}
        if not isinstance(value, dict):
            return {}
        result: dict[str, dict[str, Any]] = {}
        for raw_part_id, raw_params in value.items():
            part_id = str(raw_part_id)
            if not part_id or not isinstance(raw_params, dict):
                continue
            params = {
                str(key): item
                for key, item in raw_params.items()
                if isinstance(item, (str, int, float, bool, type(None)))
            }
            if isinstance(params.get("scale"), (int, float)) and not isinstance(
                params.get("scale"), bool
            ):
                result[part_id] = params
        return result
    return {}


def _native_part_controls(source: Path) -> list[dict[str, Any]]:
    """Expose source-native parameters that rebuild geometry before anchoring."""

    controls: list[dict[str, Any]] = []
    for part_id, params in _native_part_params(source).items():
        for parameter, value in params.items():
            control: dict[str, Any] = {
                "id": f"part_param|{part_id}|{parameter}",
                "label": f"{part_id} · {parameter}",
                "group": f"原生部件参数 · {part_id}",
                "value": value,
                "node_id": part_id,
                "parameter_mode": "native_rebuild",
            }
            if parameter == "scale" and isinstance(value, (int, float)):
                control.update(
                    type="range",
                    min=0.25,
                    max=3.0,
                    step=0.05,
                    visibility_id=f"part_object_visible|{part_id}|{part_id}",
                    visibility_value=True,
                    is_leaf=False,
                )
            elif isinstance(value, bool):
                control["type"] = "checkbox"
            elif isinstance(value, (int, float)):
                low, high, step = _numeric_bounds(value)
                control.update(type="number", min=low, max=high, step=step)
            elif value is None:
                control.update(type="text", value="")
            else:
                control["type"] = "text"
            controls.append(control)
    return controls


def _runtime_controls(is_bird: bool) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = [
        {
            "id": "scale_x",
            "label": "整体长度 X",
            "group": "整体模型",
            "type": "range",
            "min": 0.25,
            "max": 3.0,
            "step": 0.05,
            "value": 1.0,
        },
        {
            "id": "scale_y",
            "label": "整体宽度 Y",
            "group": "整体模型",
            "type": "range",
            "min": 0.25,
            "max": 3.0,
            "step": 0.05,
            "value": 1.0,
        },
        {
            "id": "scale_z",
            "label": "整体高度 Z",
            "group": "整体模型",
            "type": "range",
            "min": 0.25,
            "max": 3.0,
            "step": 0.05,
            "value": 1.0,
        },
    ]
    if not is_bird:
        return controls

    controls.append(
        {
            "id": "beak_select",
            "label": "喙类型",
            "group": "Bird 参数",
            "type": "select",
            "value": "",
            "options": [
                {"value": "", "label": "原始混合"},
                {"value": "normal", "label": "普通"},
                {"value": "duck", "label": "鸭嘴"},
                {"value": "eagle", "label": "鹰嘴"},
                {"value": "short", "label": "短喙"},
            ],
        }
    )
    role_labels = [
        ("body", "create_nurbs_body() · body（最大父节点 Mesh）"),
        ("head", "create_head() · head"),
        ("beak", "create_beak_part() · beak"),
        ("eye", "create_eye() · eye"),
        ("wing", "create_wing() · wing"),
        ("tail", "create_tail() · tail"),
        ("leg", "create_leg() · leg"),
        ("foot", "create_foot_legacy() · foot"),
    ]
    controls.extend(
        {
            "id": f"part_scale_{role}",
            "label": label,
            "group": "Bird 零件尺寸",
            "type": "range",
            "min": 0.25,
            "max": 3.0,
            "step": 0.05,
            "value": 1.0,
            "visibility_id": f"part_visible_{role}",
            "visibility_value": True,
            "part_role": role,
            "is_leaf": role != "body",
        }
        for role, label in role_labels
    )
    return controls


def _part_node_controls(structure_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose legacy nodes as approximate post-construction uniform scales."""
    view = structure_data.get("views", {}).get("parts", {})
    nodes = view.get("nodes", [])
    edges = view.get("edges", [])
    roots = set(view.get("roots", []))
    parents = {str(edge.get("parent")) for edge in edges}
    children = {str(edge.get("child")) for edge in edges}
    controls: list[dict[str, Any]] = []
    for node in nodes:
        node_id = str(node.get("id", ""))
        if not node_id:
            continue
        label = str(node.get("label") or node_id)
        creator = node.get("creator_function")
        runtime_variable = str(node.get("runtime_variable") or node_id)
        if node_id.startswith("model:"):
            control_id = f"part_model_scale|{node_id}"
        elif creator:
            control_id = (
                f"part_creator_scale|{creator}|{node_id}|{runtime_variable}"
            )
        else:
            control_id = f"part_object_scale|{runtime_variable}|{node_id}"

        is_parent = node_id in parents or node_id in roots
        is_child = node_id in children
        if is_parent and is_child:
            relation_label = "父/子节点"
        elif is_parent:
            relation_label = "父节点"
        else:
            relation_label = "子节点"
        controls.append(
            {
                "id": control_id,
                "label": f"{relation_label} · {label}",
                "group": "代码参数 · 父子节点（旧代码近似缩放）",
                "type": "range",
                "min": 0.25,
                "max": 3.0,
                "step": 0.05,
                "value": 1.0,
                "node_id": node_id,
                "creator_function": creator,
                **(
                    {
                        "visibility_id": (
                            f"part_creator_visible|{creator}|{node_id}|{runtime_variable}"
                            if creator
                            else f"part_object_visible|{runtime_variable}|{node_id}"
                        ),
                        "visibility_value": True,
                        "is_leaf": not is_parent,
                    }
                    if not node_id.startswith("model:")
                    else {}
                ),
            }
        )
    return controls


class PlaygroundState:
    def __init__(self, args: argparse.Namespace):
        source_specs: list[tuple[str, str, Path]] = []
        custom_catalogs: dict[str, dict[str, ModelEntry]] = {}
        dataset_values = getattr(args, "dataset", None)
        if dataset_values is None:
            dataset_roots: list[Path] = []
        elif isinstance(dataset_values, (str, Path)):
            dataset_roots = [Path(dataset_values)]
        else:
            dataset_roots = [Path(value) for value in dataset_values]
        label_values = getattr(args, "dataset_label", None)
        if label_values is None:
            dataset_labels: list[str | None] = []
        elif isinstance(label_values, str):
            dataset_labels = [label_values]
        else:
            dataset_labels = list(label_values)

        for index, dataset_value in enumerate(dataset_roots):
            dataset_root = dataset_value.expanduser().resolve()
            source_id = "dataset" if index == 0 else f"dataset_{index + 1}"
            label_override = (
                dataset_labels[index]
                if index < len(dataset_labels)
                else None
            )
            dataset_label = label_override or dataset_root.name
            custom_models = _model_catalog(dataset_root, source_id)
            if not custom_models:
                raise SystemExit(
                    "指定的数据集没有可运行模型。目录需要包含 "
                    f"<seed>/<seed>.py，或本身是带同名 Python 的 seed 目录：{dataset_root}"
                )
            custom_catalogs[source_id] = custom_models
            source_specs.append((source_id, dataset_label, dataset_root))
        source_specs.extend((
            ("benchmark", "Benchmark 验证集", args.benchmark),
            ("stage1", "Stage 1 Output", DEFAULT_STAGE1_OUTPUT),
            ("gpt5_6_sol", "Stage 1 · GPT-5.6-sol", DEFAULT_STAGE1_GPT56_SOL),
        ))
        self.source_labels: dict[str, str] = {}
        self.source_roots: dict[str, Path] = {}
        self.models_by_source: dict[str, dict[str, ModelEntry]] = {}
        for source_id, label, root in source_specs:
            models = custom_catalogs.get(source_id) or _model_catalog(root, source_id)
            if not models:
                continue
            self.source_labels[source_id] = label
            self.source_roots[source_id] = root.resolve()
            self.models_by_source[source_id] = models
        self.must_watch_labels = {
            entry.label
            for entry in self.models_by_source.get("gpt5_6_sol", {}).values()
        }
        self.default_source = (
            "dataset"
            if "dataset" in self.models_by_source
            else (
                "benchmark"
                if "benchmark" in self.models_by_source
                else next(iter(self.models_by_source), "")
            )
        )
        # Retain the original attribute for callers that mean the default source.
        self.models = self.models_by_source.get(self.default_source, {})
        # This workspace is Blender 5.0-only.  Keep the CLI flag for backward
        # compatibility, but deliberately pin every render to the verified
        # local 5.0 executable so environment/config drift cannot select 4.x.
        self.blender = DEFAULT_BLENDER.resolve()
        self.cache = args.cache_dir.expanduser().resolve()
        self.timeout = args.render_timeout
        self.cache.mkdir(parents=True, exist_ok=True)
        self.render_lock = threading.Lock()
        self.structure_lock = threading.Lock()
        self.structure_cache: dict[str, tuple[int, dict[str, Any]]] = {}

    def sources(self) -> list[dict[str, Any]]:
        return [
            {
                "id": source_id,
                "label": self.source_labels[source_id],
                "count": len(models),
            }
            for source_id, models in self.models_by_source.items()
        ]

    def source_models(self, source_id: str | None) -> dict[str, ModelEntry] | None:
        return self.models_by_source.get(source_id or self.default_source)

    def schema(self, entry: ModelEntry) -> dict[str, Any]:
        is_bird = entry.source_id == "benchmark" and entry.label == "Bird_seed0"
        controls = _runtime_controls(is_bird)
        native_controls = [] if is_bird else _native_part_controls(entry.source)
        # Bird has a dedicated adapter with meaningful part controls.  Its two
        # simple globals are implementation switches already covered by that
        # adapter, so avoid showing duplicate/no-op fields in the UI.
        if not is_bird:
            controls.extend(_source_controls(entry.source))
            if native_controls:
                controls.extend(native_controls)
            else:
                controls.extend(_part_node_controls(self.structure(entry)))
        return {
            "source": entry.source_id,
            "model": entry.model_id,
            "label": entry.label,
            "adapter": "bird" if is_bird else "generic",
            "parameter_mode": (
                "native_rebuild"
                if native_controls
                else ("bird_native_adapter" if is_bird else "legacy_approx")
            ),
            "controls": controls,
        }

    def sanitize_params(
        self,
        entry: ModelEntry,
        params: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Clamp browser values to the schema so one typo cannot explode geometry."""
        controls = self.schema(entry).get("controls", [])
        by_id = {str(control["id"]): control for control in controls}
        for control in controls:
            visibility_id = control.get("visibility_id")
            if visibility_id:
                by_id[str(visibility_id)] = {
                    "id": visibility_id,
                    "type": "checkbox",
                    "value": control.get("visibility_value", True),
                }

        sanitized: dict[str, Any] = {}
        adjusted: dict[str, Any] = {}
        for key, raw_value in params.items():
            control = by_id.get(str(key))
            if control is None:
                continue
            control_type = control.get("type")
            value = raw_value
            if control_type in {"number", "range"}:
                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    value = float(control.get("value", 0.0))
                if control.get("min") is not None:
                    value = max(value, float(control["min"]))
                if control.get("max") is not None:
                    value = min(value, float(control["max"]))
                default = control.get("value")
                step = control.get("step")
                if (
                    isinstance(default, int)
                    and not isinstance(default, bool)
                    and isinstance(step, (int, float))
                    and float(step).is_integer()
                ):
                    value = int(round(value))
            elif control_type == "checkbox":
                value = _boolean_value(raw_value)
            elif control_type == "select":
                allowed = {option.get("value") for option in control.get("options", [])}
                if value not in allowed:
                    value = control.get("value")
            elif value is not None:
                value = str(value)[:2048]
            sanitized[str(key)] = value
            if value != raw_value:
                adjusted[str(key)] = value
        return sanitized, adjusted

    def structure(self, entry: ModelEntry) -> dict[str, Any]:
        """Return the definition, call, and complete parent-to-child trees."""
        modified = entry.source.stat().st_mtime_ns
        cache_key = f"{entry.source_id}:{entry.model_id}:{entry.source}"
        cached = self.structure_cache.get(cache_key)
        if cached is not None and cached[0] == modified:
            return cached[1]
        with self.structure_lock:
            cached = self.structure_cache.get(cache_key)
            if cached is not None and cached[0] == modified:
                return cached[1]
            source = entry.source.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(entry.source))
            structure = SourceStructure(entry.source, source, tree)
            structure.analyze()
            data = _interactive_data(structure)
            if entry.source_id == "benchmark" and entry.label == "Bird_seed0":
                for node in data["views"]["parts"]["nodes"]:
                    part_name = str(node["id"])
                    role = part_name.split("_", 1)[0]
                    creator = BIRD_PART_CREATORS.get(role)
                    if creator is None:
                        continue
                    node["part_name"] = part_name
                    node["creator_function"] = creator
                    node["label"] = f"{creator}()"
            self.structure_cache[cache_key] = (modified, data)
            return data

    @staticmethod
    def _runtime_graph_view(report: dict[str, Any]) -> dict[str, Any]:
        """Condense the Blender probe report into the browser graph schema."""
        raw_nodes = list(report.get("nodes", []))
        # Bird's preview adapter keeps one final union object solely for GLB
        # export.  It duplicates every observed part and would create a dense
        # star of zero-gap relationships, so keep the semantic pre-join parts.
        if len(raw_nodes) > 1:
            raw_nodes = [
                node
                for node in raw_nodes
                if not str(node.get("id", "")).endswith("_codex")
            ]
        nodes = [
            {
                "id": str(node["id"]),
                "label": str(node["id"]),
                "kind": "runtime_part",
                "line": 0,
                "end_line": 0,
                "parameters": [],
                "docstring": None,
                "evidence": [],
                "group": "Blender 运行时零件",
                "origin": node.get("origin"),
                "center": node.get("center"),
                "dimensions": node.get("dimensions"),
                "bbox_min": node.get("bbox_min"),
                "bbox_max": node.get("bbox_max"),
            }
            for node in raw_nodes
        ]
        node_ids = {node["id"] for node in nodes}
        edges: list[dict[str, Any]] = []
        incoming: set[str] = set()
        for raw in report.get("edges", []):
            relation = str(raw.get("relation") or "UNOBSERVABLE")
            contact = bool(raw.get("contact"))
            declarations = raw.get("declared_directions") or []
            declared_directions = {
                (str(item.get("parent")), str(item.get("child")))
                for item in declarations
                if item.get("parent") in node_ids
                and item.get("child") in node_ids
                and item.get("parent") != item.get("child")
            }
            raw_parent = raw.get("parent")
            raw_child = raw.get("child")
            runtime_direction = (
                relation in {"DIRECTED", "DIRECTED_CODE"}
                and raw_parent in node_ids
                and raw_child in node_ids
                and raw_parent != raw_child
            )
            if runtime_direction:
                parent = str(raw_parent)
                child = str(raw_child)
                direction_source = (
                    "runtime" if relation == "DIRECTED" else "code"
                )
            elif len(declared_directions) == 1:
                parent, child = next(iter(declared_directions))
                direction_source = "declared_parent"
            else:
                parent = str(raw.get("node_a"))
                child = str(raw.get("node_b"))
                direction_source = None
            parent_child_known = direction_source is not None

            # The Blender probe's A/B points are the closest pair among a
            # bounded set of evaluated-mesh vertex samples.  They are useful
            # attachment candidates, but proximity plus parenting does not
            # prove that the source authored one persistent shared anchor.
            # Reserve the green/shared state for an explicit anchor contract.
            raw_shared_evidence = str(raw.get("shared_anchor_evidence") or "")
            explicit_shared_evidence = raw_shared_evidence in {
                "explicit_anchor_id",
                "declared_world_anchor",
                "authored_anchor_pair",
            }
            shared_anchor = bool(
                raw.get("shared_anchor")
                and explicit_shared_evidence
                and contact
            )
            geometric_anchor_aligned = bool(
                raw.get("geometric_anchor_aligned", False)
            )
            authored_anchor_observed = raw.get("authored_anchor_valid") is not None
            strict_shared_direction = bool(
                runtime_direction and contact and shared_anchor
            )
            if parent not in node_ids or child not in node_ids or parent == child:
                continue
            line = next(
                (
                    int(item.get("line") or 0)
                    for item in declarations
                    if int(item.get("line") or 0) > 0
                ),
                0,
            )
            edge = {
                "parent": parent,
                "child": child,
                "relation": relation,
                "line": line,
                "evidence": (
                    "共享锚点：父子方向、几何接触和显式共享锚点证据均通过"
                    if strict_shared_direction
                    else (
                        "父子方向已知；A/B 坐标来自最近 Mesh 顶点采样，属于非共享锚点候选"
                        if parent_child_known
                        else "运行时几何关系；A/B 坐标来自最近 Mesh 顶点采样"
                    )
                ),
                "directed_verified": runtime_direction,
                "parent_child_known": parent_child_known,
                "direction_source": direction_source,
                "contact": contact,
                "shared_anchor": shared_anchor,
                "geometric_anchor_aligned": geometric_anchor_aligned,
                "shared_anchor_evidence": (
                    raw_shared_evidence if shared_anchor else None
                ),
                "anchor_estimated": not authored_anchor_observed,
                "anchor_method": (
                    "authored_local_mesh_vertices"
                    if authored_anchor_observed
                    else "nearest_evaluated_mesh_vertex_samples"
                ),
                "anchor_a": raw.get("anchor_a"),
                "anchor_b": raw.get("anchor_b"),
                "anchor_gap": raw.get("anchor_gap"),
                "anchor_tolerance": raw.get("anchor_tolerance"),
                "authored_anchor_valid": raw.get("authored_anchor_valid"),
                "child_anchor_vertex_gap": raw.get("child_anchor_vertex_gap"),
                "parent_anchor_vertex_gap": raw.get("parent_anchor_vertex_gap"),
                "aabb_gap": raw.get("aabb_gap"),
                "declared_directions": declarations,
            }
            edges.append(edge)
            if parent_child_known:
                incoming.add(child)
        roots = sorted(node_ids - incoming) or sorted(node_ids)
        relation_counts: dict[str, int] = {}
        for edge in edges:
            relation = str(edge["relation"])
            relation_counts[relation] = relation_counts.get(relation, 0) + 1
        summary = {
            "nodes": len(nodes),
            "edges": len(edges),
            "relations": relation_counts,
            "directed_edges": sum(bool(edge["parent_child_known"]) for edge in edges),
            "runtime_directed_edges": sum(
                bool(edge["directed_verified"]) for edge in edges
            ),
            "shared_anchor_edges": sum(bool(edge["shared_anchor"]) for edge in edges),
            "estimated_anchor_edges": sum(
                bool(edge["anchor_estimated"]) for edge in edges
            ),
            "geometric_anchor_candidates": sum(
                bool(edge["geometric_anchor_aligned"]) for edge in edges
            ),
            "unverified_anchor_candidates": sum(
                bool(edge["geometric_anchor_aligned"])
                and not bool(edge["shared_anchor"])
                for edge in edges
            ),
            "misaligned_anchor_edges": sum(
                not bool(edge["geometric_anchor_aligned"]) for edge in edges
            ),
        }
        valid_bounds = [
            node
            for node in raw_nodes
            if isinstance(node.get("bbox_min"), list)
            and len(node["bbox_min"]) == 3
            and isinstance(node.get("bbox_max"), list)
            and len(node["bbox_max"]) == 3
        ]
        source_bounds = None
        if valid_bounds:
            source_bounds = {
                "min": [
                    min(float(node["bbox_min"][axis]) for node in valid_bounds)
                    for axis in range(3)
                ],
                "max": [
                    max(float(node["bbox_max"][axis]) for node in valid_bounds)
                    for axis in range(3)
                ],
            }
        return {
            "label": "运行时锚点关系图",
            "roots": roots,
            "nodes": nodes,
            "edges": edges,
            "summary": summary,
            "source_bounds": source_bounds,
            "scene_extent": report.get("scene_extent"),
            "contact_threshold": report.get("contact_threshold"),
            "shared_anchor_tolerance": report.get("shared_anchor_tolerance"),
            "native_part_params": report.get("native_part_params"),
        }

    @staticmethod
    def _apply_native_parameter_invariance(
        view: dict[str, Any],
        variants: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Downgrade shared edges unless parent and child scale probes pass."""

        default_nodes = {
            str(node.get("id")): node for node in view.get("nodes") or []
        }
        default_edges = list(view.get("edges") or [])
        results: dict[str, dict[str, Any]] = {}
        for part_id, variant in sorted(variants.items()):
            variant_nodes = {
                str(node.get("id")): node for node in variant.get("nodes") or []
            }
            before = default_nodes.get(part_id)
            after = variant_nodes.get(part_id)
            before_dims = [float(value) for value in (before or {}).get("dimensions") or []]
            after_dims = [float(value) for value in (after or {}).get("dimensions") or []]
            dimensions_changed = bool(
                len(before_dims) == len(after_dims) == 3
                and any(
                    abs(current - original) > max(abs(original) * 0.05, 1e-5)
                    for original, current in zip(before_dims, after_dims)
                )
            )
            variant_edges = {
                (str(edge.get("parent")), str(edge.get("child"))): edge
                for edge in variant.get("edges") or []
            }
            affected = [
                edge
                for edge in default_edges
                if edge.get("relation") == "DIRECTED"
                and bool(edge.get("shared_anchor"))
                and (
                    edge.get("parent") == part_id
                    or edge.get("child") == part_id
                )
            ]
            # Only default, confirmed parent->child shared anchors belong to
            # the invariance contract.  Incidental UNDIRECTED_CONTACT edges can
            # appear or disappear when a part grows and must not veto a real
            # authored attachment.
            anchors_passed = all(
                bool(
                    variant_edges.get(
                        (str(edge.get("parent")), str(edge.get("child"))),
                        {},
                    ).get("shared_anchor")
                )
                for edge in affected
            )
            results[part_id] = {
                "part_id": part_id,
                "passed": bool(dimensions_changed and anchors_passed),
                "dimensions_changed": dimensions_changed,
                "anchors_passed": anchors_passed,
                "affected_edges": len(affected),
            }

        for edge in default_edges:
            parent_result = results.get(str(edge.get("parent")), {})
            child_result = results.get(str(edge.get("child")), {})
            invariant = bool(
                parent_result.get("passed") and child_result.get("passed")
            )
            edge["parameter_invariance"] = {
                "passed": invariant,
                "parent_scale_passed": bool(parent_result.get("passed")),
                "child_scale_passed": bool(child_result.get("passed")),
            }
            if edge.get("shared_anchor") and not invariant:
                edge["shared_anchor"] = False
                edge["parameter_invariance_failed"] = True
                edge["shared_anchor_evidence"] = None
                edge["evidence"] = (
                    "默认锚点成立，但父节点或子节点单独改变尺寸后失效"
                )

        summary = view.setdefault("summary", {})
        summary["shared_anchor_edges"] = sum(
            bool(edge.get("shared_anchor")) for edge in default_edges
        )
        summary["parameter_invariance_parts"] = len(results)
        summary["parameter_invariance_passed_parts"] = sum(
            bool(item.get("passed")) for item in results.values()
        )
        view["parameter_invariance"] = {
            "mode": "native_rebuild",
            "scale_factor": 1.35,
            "results": list(results.values()),
        }
        return view

    def runtime_graph(self, entry: ModelEntry) -> dict[str, Any]:
        """Run the strict Blender-5 anchor/direction probe and cache its view."""
        if not RUNTIME_GRAPH_PROBE.is_file():
            raise RuntimeError(f"找不到运行时锚点探针：{RUNTIME_GRAPH_PROBE}")
        source_stat = entry.source.stat()
        probe_stat = RUNTIME_GRAPH_PROBE.stat()
        payload = {
            "source": entry.source_id,
            "model": entry.model_id,
            "source_path": str(entry.source),
            "source_mtime_ns": source_stat.st_mtime_ns,
            "source_size": source_stat.st_size,
            "probe_mtime_ns": probe_stat.st_mtime_ns,
            "runtime_graph_version": RUNTIME_GRAPH_VERSION,
            "blender_executable": str(self.blender),
            "blender_version": PINNED_BLENDER_VERSION,
            "contact_ratio": 0.025,
            "anchor_ratio": 0.025,
            "samples": 96,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
        output = self.cache / f"{entry.label}-runtime-graph-{digest}.json"
        raw_output = self.cache / f".{entry.label}-runtime-graph-{digest}.raw.json"
        if output.is_file():
            return json.loads(output.read_text(encoding="utf-8"))

        command = [
            str(self.blender),
            "--background",
            "--factory-startup",
            "--python",
            str(RUNTIME_GRAPH_PROBE),
            "--",
            "--script",
            str(entry.source),
            "--source-root",
            str(entry.source.parent),
            "--output",
            str(raw_output),
            "--contact-ratio",
            "0.025",
            "--anchor-ratio",
            "0.025",
            "--max-nodes",
            "128",
            "--max-edges",
            "512",
            "--samples",
            "96",
        ]
        native_parts = _native_part_params(entry.source)
        with self.render_lock:
            if output.is_file():
                return json.loads(output.read_text(encoding="utf-8"))
            try:
                completed = subprocess.run(
                    command,
                    cwd=entry.source.parent,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                raw_output.unlink(missing_ok=True)
                raise
            if not raw_output.is_file():
                details = "\n".join(
                    (completed.stdout + "\n" + completed.stderr).splitlines()[-24:]
                )
                raise RuntimeError(
                    f"Blender 运行时锚点分析失败（退出码 {completed.returncode}）\n"
                    f"{details}"
                )
            report = json.loads(raw_output.read_text(encoding="utf-8"))
            raw_output.unlink(missing_ok=True)
            if report.get("status") != "ok":
                raise RuntimeError(str(report.get("error") or "运行时锚点分析失败"))
            view = self._runtime_graph_view(report)
            if native_parts:
                variants: dict[str, dict[str, Any]] = {}
                for part_id in list(native_parts)[:32]:
                    variant_digest = hashlib.sha256(
                        f"{digest}:{part_id}:1.35".encode("utf-8")
                    ).hexdigest()[:16]
                    variant_output = self.cache / (
                        f".{entry.label}-runtime-graph-{variant_digest}.raw.json"
                    )
                    variant_command = [
                        *command,
                        "--part-param-scale",
                        f"{part_id}=1.35",
                    ]
                    output_index = variant_command.index("--output")
                    variant_command[output_index + 1] = str(variant_output)
                    try:
                        variant_completed = subprocess.run(
                            variant_command,
                            cwd=entry.source.parent,
                            text=True,
                            capture_output=True,
                            timeout=self.timeout,
                            check=False,
                        )
                    except subprocess.TimeoutExpired:
                        variants[part_id] = {"nodes": [], "edges": []}
                        variant_output.unlink(missing_ok=True)
                        continue
                    if not variant_output.is_file():
                        variants[part_id] = {"nodes": [], "edges": []}
                        continue
                    variant_report = json.loads(
                        variant_output.read_text(encoding="utf-8")
                    )
                    variant_output.unlink(missing_ok=True)
                    if variant_report.get("status") != "ok":
                        variants[part_id] = {"nodes": [], "edges": []}
                    else:
                        variants[part_id] = self._runtime_graph_view(variant_report)
                view = self._apply_native_parameter_invariance(view, variants)
            else:
                view["parameter_invariance"] = {
                    "mode": "legacy_approx",
                    "scale_factor": None,
                    "results": [],
                }
            output.write_text(
                json.dumps(view, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            return view

    def render(self, entry: ModelEntry, params: dict[str, Any]) -> dict[str, Any]:
        if not self.blender.is_file() or not os.access(self.blender, os.X_OK):
            raise RuntimeError(f"找不到 Blender：{self.blender}")

        source_stat = entry.source.stat()
        worker = ALGORITHM_DIR / "blender_live_export.py"
        worker_stat = worker.stat()
        payload = {
            "source": entry.source_id,
            "model": entry.model_id,
            "source_path": str(entry.source),
            "source_mtime_ns": source_stat.st_mtime_ns,
            "source_size": source_stat.st_size,
            "params": params,
            "adapter": (
                "bird"
                if entry.source_id == "benchmark" and entry.label == "Bird_seed0"
                else "generic"
            ),
            "blender_executable": str(self.blender),
            "blender_version": PINNED_BLENDER_VERSION,
            "render_worker_version": RENDER_WORKER_VERSION,
            "render_worker_mtime_ns": worker_stat.st_mtime_ns,
            "render_worker_size": worker_stat.st_size,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
        output = self.cache / f"{entry.label}-{digest}.glb"
        params_file = self.cache / f"{entry.label}-{digest}.json"

        started = time.monotonic()
        with self.render_lock:
            params_file.write_text(canonical, encoding="utf-8")
            render_output = self.cache / (
                f".{entry.label}-{digest}-{time.time_ns()}.rendering.glb"
            )
            command = [
                str(self.blender),
                "--background",
                "--factory-startup",
                "--python",
                str(worker),
                "--",
                "--source",
                str(entry.source),
                "--output",
                str(render_output),
                "--request",
                str(params_file),
            ]
            completed = subprocess.run(
                command,
                cwd=entry.source.parent,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
            if completed.returncode != 0 or not render_output.is_file():
                render_output.unlink(missing_ok=True)
                details = "\n".join(
                    line
                    for line in (completed.stdout + "\n" + completed.stderr).splitlines()
                    if line.strip()
                )
                raise RuntimeError(
                    f"Blender 生成失败（退出码 {completed.returncode}）\n"
                    + "\n".join(details.splitlines()[-24:])
                )
            worker_report: dict[str, Any] = {}
            for line in reversed(completed.stdout.splitlines()):
                try:
                    candidate = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict) and candidate.get("output"):
                    worker_report = candidate
                    break
            os.replace(render_output, output)

        return {
            "url": f"/generated/{output.name}",
            "cached": False,
            "seconds": round(time.monotonic() - started, 2),
            "bytes": output.stat().st_size,
            "execution": worker_report.get("execution"),
            "execution_id": worker_report.get("execution_id"),
        }


class PlaygroundHandler(BaseHTTPRequestHandler):
    server_version = "ModelPlayground/1.0"

    @property
    def state(self) -> PlaygroundState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format_string % args}")

    def _json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, content_type: str | None = None) -> None:
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        guessed = content_type or mimetypes.guess_type(path.name)[0]
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", guessed or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _entry(
        self,
        source_id: str | None,
        model_id: str | None,
    ) -> ModelEntry | None:
        models = self.state.source_models(source_id)
        return models.get(model_id or "") if models is not None else None

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path in ("/", "/index.html", "/model_playground.html"):
            self._file(
                FRONTEND_DIR / "model_playground.html",
                "text/html; charset=utf-8",
            )
            return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        if parsed.path == "/api/sources":
            self._json(
                {
                    "sources": self.state.sources(),
                    "default": self.state.default_source,
                    "must_watch_count": len(self.state.must_watch_labels),
                }
            )
            return
        if parsed.path == "/api/models":
            query = urllib.parse.parse_qs(parsed.query)
            source_id = (query.get("source") or [self.state.default_source])[0]
            source_models = self.state.source_models(source_id)
            if source_models is None:
                self._json({"error": "未知代码源"}, HTTPStatus.NOT_FOUND)
                return
            models = [
                {
                    "id": entry.model_id,
                    "label": entry.label,
                    "must_watch": entry.label in self.state.must_watch_labels,
                }
                for entry in source_models.values()
            ]
            self._json(
                {
                    "source": source_id,
                    "models": models,
                    "count": len(models),
                    "must_watch_count": sum(
                        bool(model["must_watch"]) for model in models
                    ),
                }
            )
            return
        if parsed.path == "/api/schema":
            query = urllib.parse.parse_qs(parsed.query)
            entry = self._entry(
                (query.get("source") or [None])[0],
                (query.get("model") or [None])[0],
            )
            if entry is None:
                self._json({"error": "未知模型"}, HTTPStatus.NOT_FOUND)
                return
            self._json(self.state.schema(entry))
            return
        if parsed.path == "/api/structure":
            query = urllib.parse.parse_qs(parsed.query)
            entry = self._entry(
                (query.get("source") or [None])[0],
                (query.get("model") or [None])[0],
            )
            if entry is None:
                self._json({"error": "未知模型"}, HTTPStatus.NOT_FOUND)
                return
            try:
                self._json(self.state.structure(entry))
            except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                self._json(
                    {"error": f"结构解析失败：{exc}"},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return
        if parsed.path == "/api/runtime-graph":
            query = urllib.parse.parse_qs(parsed.query)
            entry = self._entry(
                (query.get("source") or [None])[0],
                (query.get("model") or [None])[0],
            )
            if entry is None:
                self._json({"error": "未知模型"}, HTTPStatus.NOT_FOUND)
                return
            try:
                self._json(self.state.runtime_graph(entry))
            except subprocess.TimeoutExpired:
                self._json(
                    {"error": f"Blender 锚点分析超过 {self.state.timeout} 秒"},
                    HTTPStatus.GATEWAY_TIMEOUT,
                )
            except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                self._json(
                    {"error": f"运行时锚点分析失败：{exc}"},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return
        if parsed.path.startswith("/vendor/"):
            name = Path(parsed.path).name
            if name not in {
                "three.module.min.js",
                "OrbitControls.js",
                "GLTFLoader.js",
                "BufferGeometryUtils.js",
            }:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._file(
                FRONTEND_DIR / "vendor" / name,
                "text/javascript; charset=utf-8",
            )
            return
        if parsed.path.startswith("/generated/"):
            name = Path(parsed.path).name
            if not name.endswith(".glb"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._file(self.state.cache / name, "model/gltf-binary")
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urllib.parse.urlsplit(self.path).path != "/api/render":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._json({"error": "请求大小无效"}, HTTPStatus.BAD_REQUEST)
            return
        try:
            request = json.loads(self.rfile.read(length).decode("utf-8"))
            entry = self._entry(request.get("source"), request.get("model"))
            params = request.get("params", {})
            if entry is None or not isinstance(params, dict):
                raise ValueError("模型或参数无效")
            params, adjusted = self.state.sanitize_params(entry, params)
            result = self.state.render(entry, params)
            if adjusted:
                result["adjusted_params"] = adjusted
        except subprocess.TimeoutExpired:
            self._json(
                {"error": f"Blender 生成超过 {self.state.timeout} 秒"},
                HTTPStatus.GATEWAY_TIMEOUT,
            )
            return
        except ValueError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        except (RuntimeError, OSError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._json(result)


def main() -> None:
    args = _arguments()
    state = PlaygroundState(args)
    if not state.models_by_source:
        raise SystemExit("没有找到任何可用的模型代码源")

    server = ThreadingHTTPServer((args.host, args.port), PlaygroundHandler)
    server.state = state  # type: ignore[attr-defined]
    url = f"http://{args.host}:{args.port}/"
    print(
        "代码源: "
        + ", ".join(
            f"{state.source_labels[source_id]}={len(models)}"
            for source_id, models in state.models_by_source.items()
        )
    )
    print(f"Blender: {state.blender}")
    print(f"Blender version pin: {PINNED_BLENDER_VERSION}")
    print(f"打开: {url}")
    if args.open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
