"""Blender-side worker for ``model_playground.py``.

Run only through Blender:
    blender --background --python blender_live_export.py -- \
        --source model.py --output model.glb --request request.json
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


_HIDDEN_OBJECT_POINTERS: set[int] = set()
_SCALED_COMPONENT_KEYS: set[tuple[int, str]] = set()
_SEMANTIC_SNAPSHOTS: dict[int, dict[str, object]] = {}

_ATTACHMENT_CHILD_TOKENS = ("child", "dependent", "attached", "part")
_ATTACHMENT_PARENT_TOKENS = ("parent", "target", "host", "support", "base", "body")


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    return parser.parse_args(argv)


def _creator_scale_factors(overrides: dict[str, object]) -> dict[str, float]:
    factors: dict[str, float] = {}
    for key, raw_value in overrides.items():
        if not key.startswith("part_creator_scale|"):
            continue
        fields = key.split("|", 3)
        if len(fields) < 3:
            continue
        try:
            factor = min(max(float(raw_value), 0.05), 10.0)
        except (TypeError, ValueError):
            continue
        creator = fields[1]
        factors[creator] = factors.get(creator, 1.0) * factor
    return factors


def _object_scale_factors(overrides: dict[str, object]) -> dict[str, float]:
    factors: dict[str, float] = {}
    for key, raw_value in overrides.items():
        if not key.startswith("part_object_scale|"):
            continue
        fields = key.split("|", 2)
        if len(fields) != 3 or not fields[1].isidentifier():
            continue
        try:
            factor = min(max(float(raw_value), 0.05), 10.0)
        except (TypeError, ValueError):
            continue
        variable = fields[1]
        factors[variable] = factors.get(variable, 1.0) * factor
    return factors


class _CreatorScaleTransformer(ast.NodeTransformer):
    """Scale Blender objects returned by selected creator functions."""

    def __init__(self, factors: dict[str, float]) -> None:
        self.factors = factors
        self.scope: list[str] = []
        self.token_index = 0

    def _visit_function(self, node: ast.AST, name: str) -> ast.AST:
        self.scope.append(name)
        qualname = ".".join(self.scope)
        node = self.generic_visit(node)
        factor = self.factors.get(qualname)
        if factor is not None and abs(factor - 1.0) >= 1e-8:
            self.token_index += 1
            token_name = f"__codex_scale_snapshot_{self.token_index}"
            original_body = list(node.body)
            node.body = [
                ast.Assign(
                    targets=[ast.Name(id=token_name, ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Name(id="__codex_hidden_snapshot__", ctx=ast.Load()),
                        args=[],
                        keywords=[],
                    ),
                ),
                ast.Try(
                    body=original_body,
                    handlers=[],
                    orelse=[],
                    finalbody=[
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Name(
                                    id="__codex_scale_new_objects__",
                                    ctx=ast.Load(),
                                ),
                                args=[
                                    ast.Name(id=token_name, ctx=ast.Load()),
                                    ast.Constant(value=factor),
                                    ast.Constant(value=qualname),
                                ],
                                keywords=[],
                            )
                        )
                    ],
                ),
            ]
        self.scope.pop()
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        self.scope.append(node.name)
        node = self.generic_visit(node)
        self.scope.pop()
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        return self._visit_function(node, node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self._visit_function(node, node.name)

    def visit_Return(self, node: ast.Return) -> ast.AST:
        node = self.generic_visit(node)
        if node.value is None or not self.scope:
            return node
        qualname = ".".join(self.scope)
        factor = self.factors.get(qualname)
        if factor is None or abs(factor - 1.0) < 1e-8:
            return node
        node.value = ast.copy_location(
            ast.Call(
                func=ast.Name(id="__codex_scale_component_result__", ctx=ast.Load()),
                args=[node.value, ast.Constant(value=factor), ast.Constant(value=qualname)],
                keywords=[],
            ),
            node.value,
        )
        return node


class _ObjectScaleTransformer(ast.NodeTransformer):
    """Scale selected runtime variables immediately when source assigns them."""

    def __init__(self, factors: dict[str, float]) -> None:
        self.factors = factors

    @staticmethod
    def _target_names(target: ast.AST) -> set[str]:
        if isinstance(target, ast.Name):
            return {target.id}
        if isinstance(target, (ast.Tuple, ast.List)):
            names: set[str] = set()
            for item in target.elts:
                names.update(_ObjectScaleTransformer._target_names(item))
            return names
        return set()

    @staticmethod
    def _scale_call(value: ast.AST, factor: float, label: str) -> ast.Call:
        return ast.Call(
            func=ast.Name(id="__codex_scale_component_result__", ctx=ast.Load()),
            args=[value, ast.Constant(value=factor), ast.Constant(value=label)],
            keywords=[],
        )

    def _selected(self, targets: list[ast.AST]) -> list[str]:
        names = set().union(*(self._target_names(target) for target in targets))
        return sorted(name for name in names if name in self.factors)

    def _post_scale(self, node: ast.stmt, selected: list[str]):
        if not selected:
            return node
        statements: list[ast.stmt] = [node]
        for name in selected:
            statements.append(
                ast.copy_location(
                    ast.Assign(
                        targets=[ast.Name(id=name, ctx=ast.Store())],
                        value=self._scale_call(
                            ast.Name(id=name, ctx=ast.Load()),
                            self.factors[name],
                            name,
                        ),
                    ),
                    node,
                )
            )
        return statements

    def visit_Assign(self, node: ast.Assign):
        node = self.generic_visit(node)
        return self._post_scale(node, self._selected(list(node.targets)))

    def visit_AnnAssign(self, node: ast.AnnAssign):
        node = self.generic_visit(node)
        if node.value is None:
            return node
        return self._post_scale(node, self._selected([node.target]))

    def visit_NamedExpr(self, node: ast.NamedExpr) -> ast.AST:
        node = self.generic_visit(node)
        selected = self._selected([node.target])
        if not selected:
            return node
        name = selected[0]
        node.value = ast.copy_location(
            self._scale_call(node.value, self.factors[name], name),
            node.value,
        )
        return node

    def visit_For(self, node: ast.For):
        node = self.generic_visit(node)
        selected = self._selected([node.target])
        prefix = []
        for name in selected:
            prefix.append(
                ast.copy_location(
                    ast.Assign(
                        targets=[ast.Name(id=name, ctx=ast.Store())],
                        value=self._scale_call(
                            ast.Name(id=name, ctx=ast.Load()),
                            self.factors[name],
                            name,
                        ),
                    ),
                    node,
                )
            )
        node.body = [*prefix, *node.body]
        return node

    def visit_AsyncFor(self, node: ast.AsyncFor):
        node = self.generic_visit(node)
        selected = self._selected([node.target])
        prefix = []
        for name in selected:
            prefix.append(
                ast.copy_location(
                    ast.Assign(
                        targets=[ast.Name(id=name, ctx=ast.Store())],
                        value=self._scale_call(
                            ast.Name(id=name, ctx=ast.Load()),
                            self.factors[name],
                            name,
                        ),
                    ),
                    node,
                )
            )
        node.body = [*prefix, *node.body]
        return node


def _is_visible_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "off", "no"}
    return bool(value)


def _hidden_part_targets(
    tree: ast.Module,
    overrides: dict[str, object],
) -> tuple[set[str], set[str]]:
    """Return assignment variables and creator qualnames selected for hiding."""
    assigned_names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    variables: set[str] = set()
    creators: set[str] = set()
    for key, raw_value in overrides.items():
        if _is_visible_value(raw_value):
            continue
        if key.startswith("part_creator_visible|"):
            fields = key.split("|", 3)
            if len(fields) != 4:
                continue
            creator, _node_id, runtime_variable = fields[1:]
            if runtime_variable.isidentifier() and runtime_variable in assigned_names:
                variables.add(runtime_variable)
            else:
                creators.add(creator)
        elif key.startswith("part_object_visible|"):
            fields = key.split("|", 2)
            if len(fields) != 3:
                continue
            runtime_variable = fields[1]
            if runtime_variable.isidentifier() and runtime_variable in assigned_names:
                variables.add(runtime_variable)
    return variables, creators


class _PartVisibilityTransformer(ast.NodeTransformer):
    """Mark selected assignment results/creator results and protect all joins."""

    def __init__(self, variables: set[str], creators: set[str]) -> None:
        self.variables = variables
        self.creators = creators
        self.scope: list[str] = []
        self.token_index = 0

    @staticmethod
    def _target_names(target: ast.AST) -> set[str]:
        if isinstance(target, ast.Name):
            return {target.id}
        if isinstance(target, (ast.Tuple, ast.List)):
            names: set[str] = set()
            for item in target.elts:
                names.update(_PartVisibilityTransformer._target_names(item))
            return names
        return set()

    @staticmethod
    def _mark_call(value: ast.AST, label: str) -> ast.Call:
        return ast.Call(
            func=ast.Name(id="__codex_mark_component_hidden__", ctx=ast.Load()),
            args=[value, ast.Constant(value=label)],
            keywords=[],
        )

    def _visit_function(self, node: ast.AST, name: str) -> ast.AST:
        self.scope.append(name)
        qualname = ".".join(self.scope)
        node = self.generic_visit(node)
        if qualname in self.creators:
            self.token_index += 1
            token_name = f"__codex_hidden_snapshot_{self.token_index}"
            original_body = list(node.body)
            node.body = [
                ast.Assign(
                    targets=[ast.Name(id=token_name, ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Name(id="__codex_hidden_snapshot__", ctx=ast.Load()),
                        args=[],
                        keywords=[],
                    ),
                ),
                ast.Try(
                    body=original_body,
                    handlers=[],
                    orelse=[],
                    finalbody=[
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Name(
                                    id="__codex_mark_new_objects_hidden__",
                                    ctx=ast.Load(),
                                ),
                                args=[
                                    ast.Name(id=token_name, ctx=ast.Load()),
                                    ast.Constant(value=qualname),
                                ],
                                keywords=[],
                            )
                        )
                    ],
                ),
            ]
        self.scope.pop()
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        self.scope.append(node.name)
        node = self.generic_visit(node)
        self.scope.pop()
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        return self._visit_function(node, node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self._visit_function(node, node.name)

    def visit_Return(self, node: ast.Return) -> ast.AST:
        node = self.generic_visit(node)
        if node.value is not None and ".".join(self.scope) in self.creators:
            node.value = ast.copy_location(
                self._mark_call(node.value, ".".join(self.scope)),
                node.value,
            )
        return node

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        node = self.generic_visit(node)
        names = set().union(*(self._target_names(target) for target in node.targets))
        selected = sorted(names & self.variables)
        if selected:
            node.value = ast.copy_location(
                self._mark_call(node.value, ",".join(selected)),
                node.value,
            )
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AST:
        node = self.generic_visit(node)
        selected = sorted(self._target_names(node.target) & self.variables)
        if selected and node.value is not None:
            node.value = ast.copy_location(
                self._mark_call(node.value, ",".join(selected)),
                node.value,
            )
        return node

    def visit_NamedExpr(self, node: ast.NamedExpr) -> ast.AST:
        node = self.generic_visit(node)
        selected = sorted(self._target_names(node.target) & self.variables)
        if selected:
            node.value = ast.copy_location(
                self._mark_call(node.value, ",".join(selected)),
                node.value,
            )
        return node

    def visit_Call(self, node: ast.Call) -> ast.AST:
        node = self.generic_visit(node)
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "join"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "object"
            and isinstance(func.value.value, ast.Attribute)
            and func.value.value.attr == "ops"
            and isinstance(func.value.value.value, ast.Name)
            and func.value.value.value.id == "bpy"
        ):
            return node
        node.func = ast.copy_location(
            ast.Name(id="__codex_join_visible__", ctx=ast.Load()),
            node.func,
        )
        return node


def _short_call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _semantic_attachment_specs(tree: ast.Module) -> dict[str, dict[str, object]]:
    """Find attachment helpers with an identifiable child and parent argument."""
    specs: dict[str, dict[str, object]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        names = [argument.arg for argument in [*node.args.posonlyargs, *node.args.args]]
        child = next(
            (
                name
                for name in names
                if any(token in name.lower() for token in _ATTACHMENT_CHILD_TOKENS)
            ),
            None,
        )
        parent = next(
            (
                name
                for name in names
                if any(token in name.lower() for token in _ATTACHMENT_PARENT_TOKENS)
            ),
            None,
        )
        if child is None or parent is None or child == parent:
            continue
        specs[node.name] = {"names": names, "child": child, "parent": parent}
    return specs


def _semantic_call_argument(
    call: ast.Call,
    names: list[str],
    wanted: str,
) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == wanted:
            return keyword.value
    index = names.index(wanted)
    return call.args[index] if index < len(call.args) else None


class _SemanticAttachmentTransformer(ast.NodeTransformer):
    """Snapshot semantic attachment endpoints after their authored placement call."""

    def __init__(self, specs: dict[str, dict[str, object]]) -> None:
        self.specs = specs

    def visit_Expr(self, node: ast.Expr):
        node = self.generic_visit(node)
        if not isinstance(node.value, ast.Call):
            return node
        call = node.value
        name = _short_call_name(call)
        spec = self.specs.get(name or "")
        if spec is None:
            return node
        names = spec["names"]
        child = _semantic_call_argument(call, names, str(spec["child"]))
        parent = _semantic_call_argument(call, names, str(spec["parent"]))
        if child is None or parent is None:
            return node
        capture = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="__codex_capture_semantic_pair__", ctx=ast.Load()),
                args=[
                    copy.deepcopy(child),
                    copy.deepcopy(parent),
                    ast.Constant(value=name or "attachment"),
                    ast.Constant(value=int(getattr(node, "lineno", 0))),
                ],
                keywords=[],
            )
        )
        return [node, ast.copy_location(capture, node)]


def _override_ast(
    tree: ast.Module,
    overrides: dict[str, object],
    remove_main_call: bool,
) -> ast.Module:
    globals_map = {
        key.removeprefix("source_override:global:"): value
        for key, value in overrides.items()
        if key.startswith("source_override:global:")
    }
    main_map = {
        key.removeprefix("source_override:main:"): value
        for key, value in overrides.items()
        if key.startswith("source_override:main:")
    }

    def constant(value: object, original: ast.AST) -> ast.AST:
        if value == "" and isinstance(original, ast.Constant) and original.value is None:
            value = None
        return ast.copy_location(ast.Constant(value=value), original)

    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in globals_map:
                    node.value = constant(globals_map[target.id], node.value)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main":
            positional = [*node.args.posonlyargs, *node.args.args]
            offset = len(positional) - len(node.args.defaults)
            for index, argument in enumerate(positional[offset:]):
                if argument.arg in main_map:
                    node.args.defaults[index] = constant(
                        main_map[argument.arg], node.args.defaults[index]
                    )

    # Blender 4.5 removed the legacy Boolean modifier solver name "FLOAT".
    # Apply this only to ``*.solver = "FLOAT"`` so benchmark source remains
    # untouched and unrelated string literals keep their original meaning.
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

    if remove_main_call:
        tree.body = [
            node
            for node in tree.body
            if not (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "main"
            )
        ]
    creator_factors = _creator_scale_factors(overrides)
    if creator_factors:
        tree = _CreatorScaleTransformer(creator_factors).visit(tree)
    object_factors = _object_scale_factors(overrides)
    if object_factors:
        tree = _ObjectScaleTransformer(object_factors).visit(tree)
    hidden_variables, hidden_creators = _hidden_part_targets(tree, overrides)
    if hidden_variables or hidden_creators:
        tree = _PartVisibilityTransformer(hidden_variables, hidden_creators).visit(tree)
    attachment_specs = _semantic_attachment_specs(tree)
    if attachment_specs:
        tree = _SemanticAttachmentTransformer(attachment_specs).visit(tree)
    return ast.fix_missing_locations(tree)


def _bird_part_scale_factors(params: dict[str, object]) -> dict[str, float]:
    factors: dict[str, float] = {}
    for role in ("body", "head", "beak", "eye", "wing", "tail", "leg", "foot"):
        try:
            factor = float(params.get(f"part_scale_{role}", 1.0))
        except (TypeError, ValueError):
            factor = 1.0
        factors[role] = min(max(factor, 0.05), 10.0)
    return factors


def _scale_bird_created_mesh(obj: bpy.types.Object, factor: float) -> None:
    """Scale a newly-created Bird mesh about its source-code attachment origin."""
    if (
        abs(factor - 1.0) < 1e-8
        or obj.type != "MESH"
        or obj.data is None
        or not obj.data.vertices
    ):
        return
    for vertex in obj.data.vertices:
        vertex.co *= factor
    obj.data.update()
    bpy.context.view_layer.update()


def _scale_bird_created_skeleton(skeleton, factor: float):
    if skeleton is None or abs(factor - 1.0) < 1e-8:
        return skeleton
    return skeleton * factor


def _install_bird_creation_scales(
    namespace: dict[str, object],
    params: dict[str, object],
) -> None:
    """Inject size edits before the original build_bird attachment code runs."""
    factors = _bird_part_scale_factors(params)
    trace = {
        "execution": "original_main_from_empty_scene",
        "creator_calls": {
            role: 0
            for role in ("body", "head", "beak", "eye", "wing", "tail", "leg", "foot")
        },
        "attach_calls": [],
        "foot_anchors": [],
    }
    namespace["__codex_bird_source_trace__"] = trace

    original_body = namespace["create_nurbs_body"]

    def create_nurbs_body_scaled():
        trace["creator_calls"]["body"] += 1
        obj, body_length, skeleton = original_body()
        factor = factors["body"]
        _scale_bird_created_mesh(obj, factor)
        skeleton = _scale_bird_created_skeleton(skeleton, factor)
        # Keep body_length unchanged: the body slider changes this part only;
        # wing/leg sizes have their own independent controls.
        return obj, body_length, skeleton

    namespace["create_nurbs_body"] = create_nurbs_body_scaled

    original_head = namespace["create_head"]

    def create_head_scaled():
        trace["creator_calls"]["head"] += 1
        obj, skeleton, head_length = original_head()
        factor = factors["head"]
        _scale_bird_created_mesh(obj, factor)
        skeleton = _scale_bird_created_skeleton(skeleton, factor)
        return obj, skeleton, head_length

    namespace["create_head"] = create_head_scaled

    original_beak = namespace["create_beak_part"]

    def create_beak_part_scaled(*args, **kwargs):
        trace["creator_calls"]["beak"] += 1
        part = original_beak(*args, **kwargs)
        factor = factors["beak"]
        _scale_bird_created_mesh(part.obj, factor)
        part.skeleton = _scale_bird_created_skeleton(part.skeleton, factor)
        part.invalidate_bvh()
        return part

    namespace["create_beak_part"] = create_beak_part_scaled

    original_eye = namespace["create_eye"]

    def create_eye_scaled(*args, **kwargs):
        trace["creator_calls"]["eye"] += 1
        obj = original_eye(*args, **kwargs)
        _scale_bird_created_mesh(obj, factors["eye"])
        return obj

    namespace["create_eye"] = create_eye_scaled

    for creator_name, role in (
        ("create_wing", "wing"),
        ("create_tail", "tail"),
        ("create_leg", "leg"),
    ):
        original_creator = namespace[creator_name]

        def create_part_scaled(
            *args,
            __original=original_creator,
            __role=role,
            **kwargs,
        ):
            trace["creator_calls"][__role] += 1
            obj, skeleton, extra = (*__original(*args, **kwargs), None)[:3]
            factor = factors[__role]
            _scale_bird_created_mesh(obj, factor)
            skeleton = _scale_bird_created_skeleton(skeleton, factor)
            if __role == "wing":
                return obj, skeleton, extra
            return obj, skeleton

        namespace[creator_name] = create_part_scaled

    original_foot = namespace["create_foot_legacy"]

    def create_foot_scaled(*args, **kwargs):
        trace["creator_calls"]["foot"] += 1
        obj = original_foot(*args, **kwargs)
        _scale_bird_created_mesh(obj, factors["foot"])
        return obj

    namespace["create_foot_legacy"] = create_foot_scaled

    original_attach = namespace["attach_part"]

    def attach_part_traced(child, target, *args, **kwargs):
        coord = kwargs.get("coord", args[0] if args else None)
        if coord is None:
            raise ValueError("Bird attach_part call did not provide coord")
        location, _normal, _tangent = namespace["raycast_surface"](target, coord)
        result = original_attach(child, target, *args, **kwargs)
        trace["attach_calls"].append(
            {
                "parent": str(target.label),
                "child": str(child.label),
                "coord": [float(value) for value in coord],
                "source_anchor": [float(value) for value in location],
            }
        )
        return result

    namespace["attach_part"] = attach_part_traced


def _execute_source(source: Path, params: dict[str, object], adapter: str):
    text = source.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(source))
    tree = _override_ast(tree, params, remove_main_call=adapter == "bird")
    namespace = {
        "__file__": str(source),
        "__name__": "__main__",
        "__package__": None,
        "__codex_scale_component_result__": _scale_component_result,
        "__codex_scale_new_objects__": _scale_new_objects,
        "__codex_mark_component_hidden__": _mark_component_hidden,
        "__codex_hidden_snapshot__": _hidden_snapshot,
        "__codex_mark_new_objects_hidden__": _mark_new_objects_hidden,
        "__codex_join_visible__": _join_visible,
        "__codex_capture_semantic_pair__": _capture_semantic_pair,
    }
    previous_cwd = Path.cwd()
    previous_argv = sys.argv[:]
    sys.path.insert(0, str(source.parent))
    try:
        os.chdir(source.parent)
        sys.argv = [str(source)]
        exec(compile(tree, str(source), "exec"), namespace)
        if adapter == "bird":
            _install_bird_creation_scales(namespace, params)
            captured: dict[str, object] = {}
            original_build_bird = namespace["build_bird"]

            def build_bird_captured(*args, **kwargs):
                result, parts = original_build_bird(*args, **kwargs)
                captured["parts"] = parts
                return result, parts

            namespace["build_bird"] = build_bird_captured
            beak = params.get("beak_select") or None
            result = namespace["main"](
                beak_select=beak,
                join_result=False,
            )
            parts = list(captured.get("parts", []))
            parts_by_label = {str(part.label): part for part in parts}
            trace = namespace["__codex_bird_source_trace__"]
            for side in (-1, 1):
                leg = parts_by_label[f"leg_{side}"]
                foot = parts_by_label[f"foot_{side}"]
                source_anchor = namespace["lerp_sample"](
                    leg.skeleton,
                    namespace["np"].array(
                        [0.9 * (len(leg.skeleton) - 1)],
                        dtype=float,
                    ),
                ).reshape(-1)
                foot_anchor = foot.skeleton[0]
                gap = float(namespace["np"].linalg.norm(source_anchor - foot_anchor))
                trace["foot_anchors"].append(
                    {
                        "parent": str(leg.label),
                        "child": str(foot.label),
                        "gap": gap,
                    }
                )
            trace["main_completed"] = True
            return namespace, result, parts
        return namespace, None, []
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)
        try:
            sys.path.remove(str(source.parent))
        except ValueError:
            pass


def _scale_mesh_about_local_origin(obj: bpy.types.Object, factor: float) -> None:
    if obj.type != "MESH" or abs(factor - 1.0) < 1e-8 or not obj.data.vertices:
        return
    for vertex in obj.data.vertices:
        vertex.co *= factor
    obj.data.update()


def _scale_geometry_node_tree(node_tree: bpy.types.NodeTree, factor: float) -> None:
    """Insert source-time transforms before every linked geometry output."""
    if abs(factor - 1.0) < 1e-8 or node_tree.bl_idname != "GeometryNodeTree":
        return
    output_nodes = [node for node in node_tree.nodes if node.type == "GROUP_OUTPUT"]
    for output_node in output_nodes:
        for socket in output_node.inputs:
            if socket.type != "GEOMETRY" or not socket.is_linked:
                continue
            link = socket.links[0]
            source_socket = link.from_socket
            node_tree.links.remove(link)
            transform = node_tree.nodes.new("GeometryNodeTransform")
            transform.label = "Codex source parameter scale"
            transform.inputs["Scale"].default_value = (factor, factor, factor)
            node_tree.links.new(source_socket, transform.inputs["Geometry"])
            node_tree.links.new(transform.outputs["Geometry"], socket)


def _scale_component_result(value, factor: float, _creator: str = ""):
    """Scale object-like creator returns in place and preserve return shape."""
    seen_objects: set[int] = set()
    seen_meshes: set[int] = set()
    seen_companions: set[int] = set()

    def scale(item) -> None:
        if isinstance(item, bpy.types.NodeTree):
            tree_pointer = item.as_pointer()
            global_key = (tree_pointer, _creator)
            if global_key in _SCALED_COMPONENT_KEYS:
                return
            _SCALED_COMPONENT_KEYS.add(global_key)
            _scale_geometry_node_tree(item, factor)
            return
        if isinstance(item, bpy.types.Object):
            object_pointer = item.as_pointer()
            global_key = (object_pointer, _creator)
            if global_key in _SCALED_COMPONENT_KEYS:
                return
            _SCALED_COMPONENT_KEYS.add(global_key)
            if object_pointer in seen_objects:
                return
            seen_objects.add(object_pointer)
            if item.type == "MESH" and item.data is not None:
                mesh_pointer = item.data.as_pointer()
                if mesh_pointer not in seen_meshes:
                    _scale_mesh_about_local_origin(item, factor)
                    seen_meshes.add(mesh_pointer)
            else:
                item.scale = tuple(float(axis) * factor for axis in item.scale)
            return
        component_object = getattr(item, "obj", None)
        if isinstance(component_object, bpy.types.Object):
            scale(component_object)
            skeleton = getattr(item, "skeleton", None)
            if skeleton is not None:
                scale(skeleton)
            invalidate = getattr(item, "invalidate_bvh", None)
            if callable(invalidate):
                invalidate()
            return
        if isinstance(item, Vector):
            pointer = id(item)
            if pointer not in seen_companions:
                seen_companions.add(pointer)
                item *= factor
            return
        shape = getattr(item, "shape", None)
        if shape and shape[-1] == 3 and hasattr(item, "__imul__"):
            pointer = id(item)
            if pointer not in seen_companions:
                seen_companions.add(pointer)
                try:
                    item *= factor
                except (TypeError, ValueError, ArithmeticError):
                    pass
            return
        if isinstance(item, dict):
            for nested in item.values():
                scale(nested)
            return
        if isinstance(item, (list, tuple, set)):
            for nested in item:
                scale(nested)

    scale(value)
    return value


def _scale_new_objects(before: set[int], factor: float, creator: str) -> None:
    """Scale surviving objects created inside a selected source function."""
    for obj in bpy.data.objects:
        if obj.as_pointer() not in before:
            _scale_component_result(obj, factor, creator)


def _walk_component_objects(value):
    """Yield Blender objects from the return shapes used by benchmark creators."""
    seen_containers: set[int] = set()

    def walk(item):
        if isinstance(item, bpy.types.Object):
            yield item
            return
        if isinstance(item, dict):
            pointer = id(item)
            if pointer in seen_containers:
                return
            seen_containers.add(pointer)
            for nested in item.values():
                yield from walk(nested)
            return
        if isinstance(item, (list, tuple, set)):
            pointer = id(item)
            if pointer in seen_containers:
                return
            seen_containers.add(pointer)
            for nested in item:
                yield from walk(nested)

    yield from walk(value)


def _snapshot_semantic_object(
    obj: bpy.types.Object,
    role: str,
    helper: str,
    line: int,
) -> None:
    if obj.type != "MESH" or obj.data is None:
        return
    pointer = obj.as_pointer()
    if pointer in _SEMANTIC_SNAPSHOTS:
        return
    duplicate = obj.copy()
    duplicate.data = obj.data.copy()
    duplicate.animation_data_clear()
    duplicate.name = f"__codex_semantic__{obj.name}"
    duplicate.data.name = f"__codex_semantic_mesh__{obj.name}"
    duplicate.matrix_world = obj.matrix_world.copy()
    duplicate["codex_semantic_overlay"] = True
    duplicate["codex_semantic_node_id"] = obj.name
    duplicate["codex_semantic_role"] = role
    duplicate["codex_attachment_helper"] = helper
    duplicate["codex_attachment_line"] = int(line)
    bpy.context.scene.collection.objects.link(duplicate)
    _SEMANTIC_SNAPSHOTS[pointer] = {
        "source_name": obj.name,
        "source_data_pointer": obj.data.as_pointer(),
        "source_vertex_count": len(obj.data.vertices),
        "duplicate": duplicate,
    }


def _capture_semantic_pair(child, parent, helper: str, line: int) -> None:
    """Preserve attachment endpoints if a later join destroys their identity."""
    for obj in _walk_component_objects(parent):
        _snapshot_semantic_object(obj, "parent", helper, line)
    for obj in _walk_component_objects(child):
        _snapshot_semantic_object(obj, "child", helper, line)


def _remove_semantic_duplicate(snapshot: dict[str, object]) -> None:
    duplicate = snapshot.get("duplicate")
    if not isinstance(duplicate, bpy.types.Object):
        return
    data = duplicate.data
    bpy.data.objects.remove(duplicate, do_unlink=True)
    if data is not None and data.users == 0:
        bpy.data.meshes.remove(data)


def _finalize_semantic_snapshots() -> int:
    """Keep only snapshots whose source object was deleted or changed by joining."""
    current_by_pointer = {obj.as_pointer(): obj for obj in bpy.data.objects}
    kept = 0
    for pointer, snapshot in list(_SEMANTIC_SNAPSHOTS.items()):
        source = current_by_pointer.get(pointer)
        source_unchanged = bool(
            source is not None
            and source.type == "MESH"
            and source.data is not None
            and source.name == snapshot["source_name"]
            and source.data.as_pointer() == snapshot["source_data_pointer"]
            and len(source.data.vertices) == snapshot["source_vertex_count"]
        )
        if pointer in _HIDDEN_OBJECT_POINTERS or source_unchanged:
            _remove_semantic_duplicate(snapshot)
            continue
        kept += 1
    return kept


def _mark_component_hidden(value, _label: str = ""):
    """Remember objects to omit while preserving them for later source operations."""
    for obj in _walk_component_objects(value):
        _HIDDEN_OBJECT_POINTERS.add(obj.as_pointer())
    return value


def _hidden_snapshot() -> set[int]:
    return {obj.as_pointer() for obj in bpy.data.objects}


def _mark_new_objects_hidden(before: set[int], _creator: str = "") -> None:
    for obj in bpy.data.objects:
        if obj.as_pointer() not in before:
            _HIDDEN_OBJECT_POINTERS.add(obj.as_pointer())


def _join_visible(*args, **kwargs):
    """Run Blender join after removing hidden part objects from the selection."""
    hidden_selected = [
        obj
        for obj in bpy.context.selected_objects
        if obj.as_pointer() in _HIDDEN_OBJECT_POINTERS
    ]
    for obj in hidden_selected:
        obj.select_set(False)
    visible_selected = list(bpy.context.selected_objects)
    if not visible_selected:
        return {"CANCELLED"}
    active = bpy.context.view_layer.objects.active
    if active is None or active.as_pointer() in _HIDDEN_OBJECT_POINTERS:
        bpy.context.view_layer.objects.active = visible_selected[0]
    return bpy.ops.object.join(*args, **kwargs)


def _finalize_hidden_objects() -> None:
    """Hide surviving marked objects immediately before normalization/export."""
    for obj in bpy.context.scene.objects:
        if obj.as_pointer() not in _HIDDEN_OBJECT_POINTERS:
            continue
        obj.hide_render = True
        obj.hide_set(True)
        obj.select_set(False)


def _apply_generic_part_scales(
    _namespace: dict[str, object],
    params: dict[str, object],
) -> None:
    """Apply only whole-model scaling; part edits already ran inside source."""
    model_factor = 1.0
    for key, raw_value in params.items():
        try:
            factor = min(max(float(raw_value), 0.05), 10.0)
        except (TypeError, ValueError):
            continue
        if key.startswith("part_model_scale|"):
            model_factor *= factor

    if abs(model_factor - 1.0) >= 1e-8:
        _transform_roots(Matrix.Diagonal((model_factor, model_factor, model_factor, 1.0)))


def _apply_generic_part_visibility(
    namespace: dict[str, object],
    params: dict[str, object],
) -> None:
    """Catch module-level/object-name visibility targets after source execution."""
    for key, raw_value in params.items():
        if _is_visible_value(raw_value):
            continue
        runtime_variable = ""
        node_id = ""
        if key.startswith("part_creator_visible|"):
            fields = key.split("|", 3)
            if len(fields) == 4:
                _creator, node_id, runtime_variable = fields[1:]
        elif key.startswith("part_object_visible|"):
            fields = key.split("|", 2)
            if len(fields) == 3:
                runtime_variable, node_id = fields[1:]
        else:
            continue

        if runtime_variable in namespace:
            _mark_component_hidden(namespace[runtime_variable], node_id)
        for obj in bpy.context.scene.objects:
            if obj.name in {runtime_variable, node_id}:
                _mark_component_hidden(obj, node_id)


def _apply_bird_part_visibility(params: dict[str, object]) -> None:
    hidden_roles = {
        role
        for role in ("body", "head", "beak", "eye", "wing", "tail", "leg", "foot")
        if not _is_visible_value(params.get(f"part_visible_{role}", True))
    }
    if not hidden_roles:
        return
    for obj in bpy.context.scene.objects:
        if obj.get("bird_role") in hidden_roles:
            _mark_component_hidden(obj, str(obj.get("bird_role")))


def _mesh_objects() -> list[bpy.types.Object]:
    return [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and not obj.hide_render
    ]


def _world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not points:
        return Vector((-1.0, -1.0, 0.0)), Vector((1.0, 1.0, 2.0))
    mins = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    maxs = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    return mins, maxs


def _transform_roots(matrix: Matrix) -> None:
    for obj in bpy.context.scene.objects:
        if obj.parent is None:
            obj.matrix_world = matrix @ obj.matrix_world
    bpy.context.view_layer.update()


def _normalize_scene(params: dict[str, object]) -> list[bpy.types.Object]:
    sx = min(max(float(params.get("scale_x", 1.0)), 0.05), 10.0)
    sy = min(max(float(params.get("scale_y", 1.0)), 0.05), 10.0)
    sz = min(max(float(params.get("scale_z", 1.0)), 0.05), 10.0)
    _transform_roots(Matrix.Diagonal((sx, sy, sz, 1.0)))
    objects = _mesh_objects()
    mins, maxs = _world_bounds(objects)
    center = Vector(((mins.x + maxs.x) * 0.5, (mins.y + maxs.y) * 0.5, mins.z))
    _transform_roots(Matrix.Translation(-center))
    return objects


def _ensure_materials(objects: list[bpy.types.Object]) -> None:
    colors = {
        "body": (0.28, 0.45, 0.72, 1.0),
        "head": (0.34, 0.53, 0.80, 1.0),
        "beak": (0.93, 0.55, 0.16, 1.0),
        "eye": (0.025, 0.03, 0.04, 1.0),
        "wing": (0.20, 0.34, 0.58, 1.0),
        "tail": (0.16, 0.28, 0.48, 1.0),
        "leg": (0.77, 0.47, 0.20, 1.0),
        "foot": (0.70, 0.39, 0.17, 1.0),
        "default": (0.32, 0.52, 0.76, 1.0),
    }
    materials: dict[str, bpy.types.Material] = {}
    semantic_material: bpy.types.Material | None = None
    for obj in objects:
        if bool(obj.get("codex_semantic_overlay")):
            if semantic_material is None:
                semantic_material = bpy.data.materials.new("codex_semantic_overlay")
                semantic_material.diffuse_color = (1.0, 0.75, 0.18, 0.0)
                semantic_material.use_nodes = True
                principled = semantic_material.node_tree.nodes.get("Principled BSDF")
                if principled is not None:
                    principled.inputs["Base Color"].default_value = (1.0, 0.75, 0.18, 1.0)
                    principled.inputs["Alpha"].default_value = 0.0
                try:
                    semantic_material.surface_render_method = "DITHERED"
                except (AttributeError, TypeError, ValueError):
                    pass
            obj.data.materials.clear()
            obj.data.materials.append(semantic_material)
            continue
        if obj.data.materials:
            continue
        role = str(obj.get("bird_role") or "default")
        if role not in materials:
            material = bpy.data.materials.new(f"preview_{role}")
            material.diffuse_color = colors.get(role, colors["default"])
            material.metallic = 0.0
            material.roughness = 0.65
            materials[role] = material
        obj.data.materials.append(materials[role])


def _export_glb(output: Path, objects: list[bpy.types.Object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]
    kwargs = {
        "filepath": str(output),
        "export_format": "GLB",
        "use_selection": True,
        "export_apply": True,
        "export_yup": True,
        "export_extras": True,
    }
    bpy.ops.export_scene.gltf(**kwargs)


def main() -> None:
    args = _arguments()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    params = request.get("params", {})
    adapter = request.get("adapter", "generic")
    if not isinstance(params, dict):
        raise TypeError("params must be an object")

    namespace, result, parts = _execute_source(
        args.source.resolve(), params, adapter
    )
    if adapter == "bird":
        _apply_bird_part_visibility(params)
    else:
        _apply_generic_part_scales(namespace, params)
        _apply_generic_part_visibility(namespace, params)
    _finalize_hidden_objects()
    semantic_overlays = _finalize_semantic_snapshots()
    objects = _normalize_scene(params)
    if not objects:
        raise RuntimeError("脚本执行完成，但场景中没有可导出的 Mesh")
    _ensure_materials(objects)
    _export_glb(args.output.resolve(), objects)
    report = {
        "output": str(args.output.resolve()),
        "objects": len(objects),
        "bytes": args.output.stat().st_size,
        "execution": "full_source_from_empty_scene",
        "execution_id": f"{os.getpid()}-{args.output.stat().st_mtime_ns}",
        "semantic_overlays": semantic_overlays,
    }
    if adapter == "bird":
        report["source_trace"] = namespace.get("__codex_bird_source_trace__", {})
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
