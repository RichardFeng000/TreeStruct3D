"""Execute one Blender script and build a runtime causal attachment graph.

This module is intentionally standalone: Blender runs it in its own Python.
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
import math
import os
import random
import sys
import traceback
from pathlib import Path


GEOMETRY_TYPES = {"MESH", "CURVE", "SURFACE", "FONT", "META"}
CHILD_TOKENS = ("child", "dependent", "attached", "part")
PARENT_TOKENS = ("parent", "target", "host", "support", "base", "body")
NON_PART_ROOTS = {"Matrix", "Vector", "bpy", "bmesh", "math", "np", "numpy"}
SHARED_ANCHOR_RELATIONS = {
    "DIRECTED",
    "DIRECTED_CODE",
    "COUPLED",
    "DECLARED_CONSTRUCTION",
}


def _arguments():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pythonpath")
    parser.add_argument("--contact-ratio", type=float, default=0.025)
    parser.add_argument(
        "--anchor-ratio",
        type=float,
        default=None,
        help=(
            "maximum world-space anchor gap as a fraction of scene extent; "
            "defaults to --contact-ratio"
        ),
    )
    parser.add_argument("--max-nodes", type=int, default=128)
    parser.add_argument("--max-edges", type=int, default=512)
    parser.add_argument("--samples", type=int, default=96)
    return parser.parse_args(argv)


def _clear_scene(bpy):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for item in list(collection):
            collection.remove(item)


def _names_in(value):
    return {
        node.id
        for node in ast.walk(value)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }


def _assigned_names(target):
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        return {
            name
            for item in target.elts
            for name in _assigned_names(item)
        }
    return set()


def _root_name(value):
    while isinstance(value, (ast.Attribute, ast.Subscript)):
        value = value.value
    return value.id if isinstance(value, ast.Name) else None


def _expression_sources(value, taints):
    sources = set()
    for node in ast.walk(value):
        if isinstance(node, ast.Attribute):
            root = _root_name(node)
            if root is not None:
                sources.add(root)
        elif isinstance(node, ast.Name):
            sources.update(taints.get(node.id, ()))
    return sources


def _scope_nodes(scope):
    """Walk one lexical scope without leaking names across definitions."""
    stack = list(reversed(getattr(scope, "body", [])))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        yield node
        stack.extend(reversed(list(ast.iter_child_nodes(node))))


def _method_dataflow_links(tree):
    """Find `source.attr -> value -> sink.method(value)` paths by source line."""
    scopes = [tree, *(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))]
    result = {}
    for scope in scopes:
        taints = {}
        nodes = sorted(
            (
                node
                for node in _scope_nodes(scope)
                if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Call))
            ),
            key=lambda node: (
                int(getattr(node, "lineno", 0)),
                int(getattr(node, "col_offset", 0)),
                0 if isinstance(node, (ast.Assign, ast.AnnAssign)) else 1,
            ),
        )
        for node in nodes:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = getattr(node, "value", None)
                if value is None:
                    continue
                sources = _expression_sources(value, taints)
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    for name in _assigned_names(target):
                        taints[name] = set(sources)
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            sink = _root_name(node.func.value)
            if sink is None or sink in NON_PART_ROOTS:
                continue
            values = [*node.args, *(keyword.value for keyword in node.keywords)]
            sources = {
                source
                for value in values
                for source in _expression_sources(value, taints)
                if source != sink and source not in NON_PART_ROOTS
            }
            if sources:
                result.setdefault(
                    (int(node.lineno), int(node.col_offset)),
                    set(),
                ).update((sink, source) for source in sources)
    return result


def _one_way_dataflow(function, source_name, sink_name):
    """Prove a simple source-parameter -> sink-object mutation path."""
    tainted = {source_name}
    statements = sorted(
        (
            node
            for node in ast.walk(function)
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
        ),
        key=lambda node: int(getattr(node, "lineno", 0)),
    )
    changed = True
    while changed:
        changed = False
        for statement in statements:
            value = getattr(statement, "value", None)
            if value is None or not (_names_in(value) & tainted):
                continue
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
            )
            assigned = {
                name
                for target in targets
                for name in _assigned_names(target)
            }
            if not assigned <= tainted:
                tainted.update(assigned)
                changed = True

    for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
        if not isinstance(call.func, ast.Attribute):
            continue
        if _root_name(call.func.value) != sink_name:
            continue
        values = [*call.args, *(item.value for item in call.keywords)]
        if any(_names_in(value) & tainted for value in values):
            return True
    for assignment in (
        node
        for node in ast.walk(function)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
    ):
        value = getattr(assignment, "value", None)
        if value is None or not (_names_in(value) & tainted):
            continue
        targets = (
            assignment.targets
            if isinstance(assignment, ast.Assign)
            else [assignment.target]
        )
        if any(
            isinstance(target, ast.Attribute)
            and _root_name(target.value) == sink_name
            for target in targets
        ):
            return True
    return False


def _attachment_specs(tree):
    specs = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        names = [argument.arg for argument in node.args.args]
        child = next(
            (name for name in names if any(token in name.lower() for token in CHILD_TOKENS)),
            None,
        )
        parent = next(
            (name for name in names if any(token in name.lower() for token in PARENT_TOKENS)),
            None,
        )
        if child is not None and parent is not None and child != parent:
            forward = _one_way_dataflow(node, parent, child)
            reverse = _one_way_dataflow(node, child, parent)
            called_names = {
                str(_call_name(call) or "").lower()
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
            }
            specs[node.name] = {
                "names": names,
                "child": child,
                "parent": parent,
                "code_directed": bool(forward and not reverse),
                "authored_anchor": any(
                    "raycast" in name or "anchor" in name
                    for name in called_names
                ),
            }
    return specs


def _call_argument(call, names, wanted):
    for keyword in call.keywords:
        if keyword.arg == wanted:
            return keyword.value
    index = names.index(wanted)
    if index < len(call.args):
        return call.args[index]
    return None


def _call_name(call):
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


class _Instrumenter(ast.NodeTransformer):
    def __init__(self, specs, method_links):
        self.specs = specs
        self.method_links = method_links

    def visit_Expr(self, node):
        node = self.generic_visit(node)
        if not isinstance(node.value, ast.Call):
            return node
        call = node.value
        name = _call_name(call)
        before = []
        after = []
        if name == "join":
            before.append(
                ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id="__pcg_capture_join__", ctx=ast.Load()),
                        args=[],
                        keywords=[],
                    )
                )
            )
        if name in self.specs:
            spec = self.specs[name]
            names = spec["names"]
            child_name = spec["child"]
            parent_name = spec["parent"]
            child = _call_argument(call, names, child_name)
            parent = _call_argument(call, names, parent_name)
            if child is not None and parent is not None:
                after.append(
                    ast.Expr(
                        value=ast.Call(
                            func=ast.Name(id="__pcg_record_link__", ctx=ast.Load()),
                            args=[
                                copy.deepcopy(child),
                                copy.deepcopy(parent),
                                ast.Constant(
                                    value=(
                                        f"attachment_call:{name}"
                                        + (
                                            ":code_directed"
                                            if spec["code_directed"]
                                            else ""
                                        )
                                        + (
                                            ":authored_anchor"
                                            if spec["authored_anchor"]
                                            else ""
                                        )
                                    )
                                ),
                                ast.Constant(value=int(getattr(node, "lineno", 0))),
                            ],
                            keywords=[],
                        )
                    )
                )
        for sink, source in sorted(
            self.method_links.get(
                (int(getattr(call, "lineno", 0)), int(getattr(call, "col_offset", 0))),
                (),
            )
        ):
            # Static data-flow analysis can see assignments that live inside a
            # conditional branch even when that branch is not taken at runtime.
            # Looking up those names directly would raise UnboundLocalError and
            # abort the whole probe (for example Pinecone's optional ``align``
            # node when ``align_factor == 0``).  Missing runtime endpoints are
            # not links, so pass None to ``record_link`` and let it ignore them.
            safe_sink = ast.Call(
                func=ast.Attribute(
                    value=ast.Call(
                        func=ast.Name(id="locals", ctx=ast.Load()),
                        args=[],
                        keywords=[],
                    ),
                    attr="get",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=sink)],
                keywords=[],
            )
            safe_source = ast.Call(
                func=ast.Attribute(
                    value=ast.Call(
                        func=ast.Name(id="locals", ctx=ast.Load()),
                        args=[],
                        keywords=[],
                    ),
                    attr="get",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=source)],
                keywords=[],
            )
            recorder = ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="__pcg_record_link__", ctx=ast.Load()),
                    args=[
                        safe_sink,
                        safe_source,
                        ast.Constant(value="method_dataflow:code_directed"),
                        ast.Constant(value=int(getattr(node, "lineno", 0))),
                    ],
                    keywords=[],
                )
            )
            ast.copy_location(recorder, node)
            after.append(recorder)
        for item in before + after:
            ast.copy_location(item, node)
        return [*before, node, *after]

    def visit_Assign(self, node):
        node = self.generic_visit(node)
        after = []
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr == "parent":
                if isinstance(node.value, ast.Constant) and node.value.value is None:
                    continue
                recorder = ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id="__pcg_record_link__", ctx=ast.Load()),
                        args=[
                            copy.deepcopy(target.value),
                            copy.deepcopy(node.value),
                            ast.Constant(value="parent_assignment"),
                            ast.Constant(value=int(getattr(node, "lineno", 0))),
                        ],
                        keywords=[],
                    )
                )
                ast.copy_location(recorder, node)
                after.append(recorder)
        return [node, *after] if after else node


def _instrumented_code(path):
    source = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=path)
    specs = _attachment_specs(tree)
    method_links = _method_dataflow_links(tree)
    tree = _Instrumenter(specs, method_links).visit(tree)
    # Blender 5 removed the legacy Boolean modifier solver name ``FLOAT``.
    # Keep the benchmark source unchanged and patch only solver assignments in
    # the in-memory AST used by the runtime probe.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Attribute) and target.attr == "solver"
            for target in targets
        ):
            continue
        if isinstance(node.value, ast.Constant) and node.value.value == "FLOAT":
            node.value = ast.copy_location(ast.Constant(value="EXACT"), node.value)
    ast.fix_missing_locations(tree)
    public_specs = [
        {
            "function": name,
            "child_parameter": spec["child"],
            "parent_parameter": spec["parent"],
            "code_directed": spec["code_directed"],
            "authored_anchor": spec["authored_anchor"],
        }
        for name, spec in sorted(specs.items())
    ]
    return compile(tree, path, "exec"), public_specs


def _vector(value):
    return [float(value.x), float(value.y), float(value.z)]


def _distance(first, second):
    return math.sqrt(sum((first[i] - second[i]) ** 2 for i in range(3)))


def _aabb_gap(first, second):
    squared = 0.0
    for axis in range(3):
        if first["bbox_max"][axis] < second["bbox_min"][axis]:
            delta = second["bbox_min"][axis] - first["bbox_max"][axis]
        elif second["bbox_max"][axis] < first["bbox_min"][axis]:
            delta = first["bbox_min"][axis] - second["bbox_max"][axis]
        else:
            delta = 0.0
        squared += delta * delta
    return math.sqrt(squared)


def _closest_samples(first, second):
    first_points = first["samples"] or [first["center"]]
    second_points = second["samples"] or [second["center"]]
    best = None
    for point_a in first_points:
        for point_b in second_points:
            gap = _distance(point_a, point_b)
            if best is None or gap < best[0]:
                best = (gap, point_a, point_b)
    return best


def _world_anchors_aligned(anchor_a, anchor_b, tolerance):
    """Return whether two candidate anchors coincide in world space."""
    if anchor_a is None or anchor_b is None:
        return False, None
    gap = _distance(anchor_a, anchor_b)
    return gap <= tolerance, gap


def _deterministic_spatial_samples(points, sample_limit):
    """Select repeatable, spatially distributed world-space mesh samples."""
    ordered = sorted(
        ([float(value) for value in point] for point in points),
        key=lambda point: (point[0], point[1], point[2]),
    )
    sample_count = max(int(sample_limit), 1)
    if len(ordered) <= sample_count:
        return ordered

    selected = [0]
    minimum_squared_distances = [
        sum((point[axis] - ordered[0][axis]) ** 2 for axis in range(3))
        for point in ordered
    ]
    minimum_squared_distances[0] = -1.0
    while len(selected) < sample_count:
        next_index = max(
            range(len(ordered)),
            key=lambda index: minimum_squared_distances[index],
        )
        selected.append(next_index)
        next_point = ordered[next_index]
        minimum_squared_distances[next_index] = -1.0
        for index, point in enumerate(ordered):
            if minimum_squared_distances[index] < 0.0:
                continue
            squared_distance = sum(
                (point[axis] - next_point[axis]) ** 2
                for axis in range(3)
            )
            minimum_squared_distances[index] = min(
                minimum_squared_distances[index],
                squared_distance,
            )
    return [ordered[index] for index in selected]


def _unwrap_object(value, bpy):
    if isinstance(value, bpy.types.Object):
        return value
    for attribute in ("obj", "object"):
        candidate = getattr(value, attribute, None)
        if isinstance(candidate, bpy.types.Object):
            return candidate
    return None


def _observe_object(obj, depsgraph, sample_limit):
    if obj is None or obj.type not in GEOMETRY_TYPES:
        return None
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        if not mesh.vertices:
            return None
        matrix = evaluated.matrix_world
        points = [_vector(matrix @ vertex.co) for vertex in mesh.vertices]
        count = len(points)
        sampled_points = _deterministic_spatial_samples(points, sample_limit)
        lower = [min(point[axis] for point in points) for axis in range(3)]
        upper = [max(point[axis] for point in points) for axis in range(3)]
        center = [(lower[axis] + upper[axis]) * 0.5 for axis in range(3)]
        properties = {}
        for key in obj.keys():
            value = obj.get(key)
            if isinstance(value, (str, int, float, bool)):
                properties[str(key)] = value
        return {
            "id": obj.name,
            "object_type": obj.type,
            "vertex_count": count,
            "bbox_min": lower,
            "bbox_max": upper,
            "center": center,
            "origin": _vector(evaluated.matrix_world.translation),
            "dimensions": [upper[i] - lower[i] for i in range(3)],
            "samples": sampled_points,
            "properties": properties,
            "is_final": obj.name in {item.name for item in obj.users_scene[0].objects}
            if obj.users_scene
            else False,
        }
    finally:
        evaluated.to_mesh_clear()


def _semantic_rank(observation):
    name = observation["id"].lower()
    role = " ".join(str(value).lower() for value in observation["properties"].values())
    preferred = any(
        token in name or token in role
        for token in (
            "body",
            "head",
            "leg",
            "foot",
            "wing",
            "tail",
            "frame",
            "base",
            "shelf",
            "support",
            "panel",
        )
    )
    volume = math.prod(max(value, 1e-9) for value in observation["dimensions"])
    return (0 if preferred else 1, -volume, observation["id"])


def _influence_trials(bpy, final_objects, source_names, extent):
    baseline = {
        name: _vector(obj.matrix_world.translation)
        for name, obj in final_objects.items()
    }
    delta = max(extent * 0.035, 1e-4)
    influence = {}
    for source_name in sorted(source_names):
        source = final_objects.get(source_name)
        if source is None:
            continue
        original = source.location.copy()
        per_axis = []
        try:
            for axis in (0, 2):
                source.location[axis] += delta
                bpy.context.view_layer.update()
                current = {
                    name: _vector(obj.matrix_world.translation)
                    for name, obj in final_objects.items()
                }
                source_delta = [
                    current[source_name][i] - baseline[source_name][i]
                    for i in range(3)
                ]
                source_motion = math.sqrt(sum(value * value for value in source_delta))
                trial = {
                    "axis": axis,
                    "source_motion": source_motion,
                    "source_delta": source_delta,
                    "targets": {},
                }
                if source_motion > delta * 0.25:
                    for target_name in final_objects:
                        if target_name == source_name:
                            continue
                        target_delta = [
                            current[target_name][i] - baseline[target_name][i]
                            for i in range(3)
                        ]
                        target_motion = math.sqrt(
                            sum(value * value for value in target_delta)
                        )
                        follow_error = math.sqrt(
                            sum(
                                (target_delta[i] - source_delta[i]) ** 2
                                for i in range(3)
                            )
                        )
                        follow_score = max(
                            0.0,
                            min(1.0, 1.0 - follow_error / source_motion),
                        )
                        trial["targets"][target_name] = {
                            "motion": target_motion,
                            "delta": target_delta,
                            "follow_score": follow_score,
                        }
                per_axis.append(trial)
                source.location = original.copy()
                bpy.context.view_layer.update()
        finally:
            source.location = original
            bpy.context.view_layer.update()
        influence[source_name] = per_axis
    return influence


def _influences(influence, source, target):
    trials = [
        trial
        for trial in influence.get(source, [])
        if trial["source_motion"] > 0 and target in trial["targets"]
    ]
    if not trials:
        return None
    scores = [trial["targets"][target]["follow_score"] for trial in trials]
    motions = [
        trial["targets"][target]["motion"] / trial["source_motion"]
        for trial in trials
    ]
    return {
        "verified": all(score >= 0.8 and ratio >= 0.8 for score, ratio in zip(scores, motions)),
        "minimum_follow_score": min(scores),
        "minimum_motion_ratio": min(motions),
        "trials": len(trials),
    }


def _classify_pair(
    first,
    second,
    *,
    contact,
    anchor_aligned,
    first_to_second,
    second_to_first,
    declared_links,
):
    forward = bool(first_to_second and first_to_second["verified"])
    reverse = bool(second_to_first and second_to_first["verified"])
    if declared_links and (not contact or not anchor_aligned):
        return "BROKEN_ATTACHMENT", None, None
    if not contact:
        return "UNOBSERVABLE", None, None
    if not anchor_aligned:
        return "UNDIRECTED_CONTACT", None, None
    if forward and not reverse:
        return "DIRECTED", first, second
    if reverse and not forward:
        return "DIRECTED", second, first
    if forward and reverse:
        return "COUPLED", None, None
    code_directions = {
        (link["parent"], link["child"])
        for link in declared_links
        if ":code_directed" in link["source"]
        or ":authored_anchor" in link["source"]
    }
    if len(code_directions) == 1:
        parent, child = next(iter(code_directions))
        return "DIRECTED_CODE", parent, child
    if len(code_directions) > 1:
        return "COUPLED", None, None
    if declared_links:
        return "DECLARED_CONSTRUCTION", None, None
    if first_to_second is None and second_to_first is None:
        return "UNOBSERVABLE", None, None
    return "UNDIRECTED_CONTACT", None, None


def _shared_anchor_verified(relation, *, contact, anchor_aligned, declared_links):
    """Reserve shared-anchor status for an authored attachment calculation."""
    authored = any(
        ":authored_anchor" in str(link.get("source") or "")
        for link in declared_links
    )
    return bool(
        contact
        and anchor_aligned
        and authored
        and relation in SHARED_ANCHOR_RELATIONS
    )


def _shared_anchor_evidence(relation, declared_links):
    if any(
        ":authored_anchor" in str(link.get("source") or "")
        for link in declared_links
    ):
        return "authored_anchor_pair"
    if relation == "DIRECTED":
        return "runtime_direction"
    if relation == "DIRECTED_CODE":
        return "code_direction"
    if relation == "COUPLED":
        return "runtime_or_code_coupling"
    if relation == "DECLARED_CONSTRUCTION":
        return "code_construction"
    return None


def main():
    args = _arguments()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"status": "error", "script": args.script}
    try:
        if args.pythonpath:
            dependency_root = str(Path(args.pythonpath).resolve())
            if dependency_root not in sys.path:
                sys.path.insert(0, dependency_root)
        import bpy

        _clear_scene(bpy)
        random.seed(0)
        try:
            import numpy as np

            np.random.seed(0)
        except Exception:
            pass
        source_root = str(Path(args.source_root).resolve())
        if source_root not in sys.path:
            sys.path.insert(0, source_root)
        os.chdir(source_root)

        registry = {}
        declared_links = []

        def remember(obj):
            try:
                existing = registry.get(getattr(obj, "name", ""))
                if existing is not None:
                    return existing
                bpy.context.view_layer.update()
                observation = _observe_object(
                    obj,
                    bpy.context.evaluated_depsgraph_get(),
                    args.samples,
                )
                if observation is not None:
                    registry[observation["id"]] = observation
                return observation
            except Exception:
                return None

        def capture_join():
            # Recording every nested join forces large procedural models to be
            # converted to evaluated meshes many times.  Authored attachment
            # calls and Blender parent/constraint links preserve the semantic
            # pre-join parts without this expensive broad snapshot.
            return None

        def record_link(child_value, parent_value, source, line):
            child = _unwrap_object(child_value, bpy)
            parent = _unwrap_object(parent_value, bpy)
            if child is None or parent is None or child == parent:
                return
            child_observation = remember(child)
            parent_observation = remember(parent)
            if child_observation is None or parent_observation is None:
                return
            declared_links.append(
                {
                    "parent": parent.name,
                    "child": child.name,
                    "source": str(source),
                    "line": int(line),
                }
            )

        code, attachment_helpers = _instrumented_code(args.script)
        namespace = {
            "__name__": "__main__",
            "__file__": args.script,
            "__package__": None,
            "__pcg_capture_join__": capture_join,
            "__pcg_record_link__": record_link,
        }
        exec(code, namespace)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()

        final_objects = {}
        for obj in bpy.context.scene.objects:
            if obj.type not in GEOMETRY_TYPES:
                continue
            final_objects[obj.name] = obj
            has_runtime_link = (
                obj.parent is not None and obj.parent.type in GEOMETRY_TYPES
            ) or any(
                getattr(constraint, "target", None) is not None
                and constraint.target.type in GEOMETRY_TYPES
                for constraint in obj.constraints
            )
            # When authored pre-join links already supplied semantic objects,
            # a huge final union mesh adds no attachment information.  Skip
            # evaluating it unless it is itself linked or already registered.
            if declared_links and obj.name not in registry and not has_runtime_link:
                continue
            observation = remember(obj)
            if observation is None:
                continue
            registry[obj.name] = observation
            if obj.parent is not None and obj.parent.type in GEOMETRY_TYPES:
                declared_links.append(
                    {
                        "parent": obj.parent.name,
                        "child": obj.name,
                        "source": "final_parent",
                        "line": 0,
                    }
                )
            for constraint in obj.constraints:
                target = getattr(constraint, "target", None)
                if target is not None and target.type in GEOMETRY_TYPES:
                    declared_links.append(
                        {
                            "parent": target.name,
                            "child": obj.name,
                            "source": f"constraint:{constraint.type}",
                            "line": 0,
                        }
                    )

        deduplicated_links = {}
        for link in declared_links:
            key = (link["parent"], link["child"], link["source"], link["line"])
            deduplicated_links[key] = link
        declared_links = list(deduplicated_links.values())

        semantic_ids = {
            endpoint
            for link in declared_links
            for endpoint in (link["parent"], link["child"])
            if endpoint in registry
        }
        semantic_ids.update(
            node_id
            for node_id, item in registry.items()
            if item["properties"]
        )
        selected = (
            [registry[node_id] for node_id in semantic_ids]
            if len(semantic_ids) >= 2
            else [registry[node_id] for node_id in final_objects if node_id in registry]
        )
        selected = sorted(selected, key=_semantic_rank)[: args.max_nodes]
        nodes = {item["id"]: item for item in selected}
        if not nodes:
            raise RuntimeError("script produced no observable geometry nodes")

        lower = [min(item["bbox_min"][axis] for item in nodes.values()) for axis in range(3)]
        upper = [max(item["bbox_max"][axis] for item in nodes.values()) for axis in range(3)]
        extent = max(upper[axis] - lower[axis] for axis in range(3)) or 1.0
        threshold = extent * args.contact_ratio
        anchor_ratio = (
            args.contact_ratio
            if args.anchor_ratio is None
            else args.anchor_ratio
        )
        anchor_threshold = extent * anchor_ratio

        declared_by_pair = {}
        for link in declared_links:
            if link["parent"] not in nodes or link["child"] not in nodes:
                continue
            pair = tuple(sorted((link["parent"], link["child"])))
            declared_by_pair.setdefault(pair, []).append(link)

        candidates = {}
        node_items = sorted(nodes.items())
        for index, (first_id, first) in enumerate(node_items):
            for second_id, second in node_items[index + 1 :]:
                aabb_gap = _aabb_gap(first, second)
                if aabb_gap <= threshold:
                    sample_gap, anchor_a, anchor_b = _closest_samples(first, second)
                    if sample_gap <= threshold * 3.0 or aabb_gap == 0.0:
                        anchor_aligned, anchor_gap = _world_anchors_aligned(
                            anchor_a,
                            anchor_b,
                            anchor_threshold,
                        )
                        candidates[(first_id, second_id)] = {
                            "node_a": first_id,
                            "node_b": second_id,
                            "aabb_gap": aabb_gap,
                            "sample_gap": sample_gap,
                            "anchor_a": anchor_a,
                            "anchor_b": anchor_b,
                            "anchor_gap": anchor_gap,
                            "anchor_tolerance": anchor_threshold,
                            "geometric_anchor_aligned": anchor_aligned,
                            "contact": True,
                        }
        for pair, links in declared_by_pair.items():
            if pair in candidates:
                continue
            first, second = nodes[pair[0]], nodes[pair[1]]
            sample_gap, anchor_a, anchor_b = _closest_samples(first, second)
            anchor_aligned, anchor_gap = _world_anchors_aligned(
                anchor_a,
                anchor_b,
                anchor_threshold,
            )
            candidates[pair] = {
                "node_a": pair[0],
                "node_b": pair[1],
                "aabb_gap": _aabb_gap(first, second),
                "sample_gap": sample_gap,
                "anchor_a": anchor_a,
                "anchor_b": anchor_b,
                "anchor_gap": anchor_gap,
                "anchor_tolerance": anchor_threshold,
                "geometric_anchor_aligned": anchor_aligned,
                "contact": _aabb_gap(first, second) <= threshold,
            }

        ranked_pairs = sorted(
            candidates,
            key=lambda pair: (
                0 if pair in declared_by_pair else 1,
                candidates[pair]["aabb_gap"],
                candidates[pair]["sample_gap"],
            ),
        )[: args.max_edges]
        source_names = {
            endpoint
            for pair in ranked_pairs
            for endpoint in pair
            if endpoint in final_objects
        }
        influence = _influence_trials(
            bpy,
            final_objects,
            source_names,
            extent,
        )

        edges = []
        for pair in ranked_pairs:
            edge = candidates[pair]
            first, second = pair
            pair_declarations = declared_by_pair.get(pair, [])
            first_to_second = _influences(influence, first, second)
            second_to_first = _influences(influence, second, first)
            relation, parent, child = _classify_pair(
                first,
                second,
                contact=edge["contact"],
                anchor_aligned=edge["geometric_anchor_aligned"],
                first_to_second=first_to_second,
                second_to_first=second_to_first,
                declared_links=pair_declarations,
            )
            shared_anchor = _shared_anchor_verified(
                relation,
                contact=edge["contact"],
                anchor_aligned=edge["geometric_anchor_aligned"],
                declared_links=pair_declarations,
            )
            edge.update(
                relation=relation,
                parent=parent,
                child=child,
                shared_anchor=shared_anchor,
                shared_anchor_evidence=(
                    _shared_anchor_evidence(relation, pair_declarations)
                    if shared_anchor
                    else None
                ),
                a_influences_b=first_to_second,
                b_influences_a=second_to_first,
                declared_directions=pair_declarations,
            )
            edges.append(edge)

        counts = {}
        for edge in edges:
            counts[edge["relation"]] = counts.get(edge["relation"], 0) + 1
        report = {
            "status": "ok",
            "script": args.script,
            "attachment_helpers": attachment_helpers,
            "scene_extent": extent,
            "contact_threshold": threshold,
            "shared_anchor_tolerance": anchor_threshold,
            "nodes": list(nodes.values()),
            "declared_links": declared_links,
            "influence_trials": influence,
            "edges": edges,
            "summary": {
                "nodes": len(nodes),
                "edges": len(edges),
                "relations": counts,
                "directed_edges": (
                    counts.get("DIRECTED", 0)
                    + counts.get("DIRECTED_CODE", 0)
                ),
                "shared_anchor_edges": sum(
                    bool(edge["shared_anchor"]) for edge in edges
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
            },
        }
    except Exception as error:
        report = {
            "status": "error",
            "script": args.script,
            "error": f"{type(error).__name__}: {error}\n{traceback.format_exc()}",
        }
    output.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
