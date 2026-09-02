#!/usr/bin/env python3
"""Render Python/Blender source structure as definition, call, and part trees.

The static attachment analysis follows the same core ideas used by the bundled
Blender runtime probe:

* parse source with :mod:`ast`;
* recognize attachment helpers from child/parent-like parameter names;
* prove simple parent-data -> child-mutation paths;
* recover manual transform dependencies such as ``leg -> foot``;
* preserve source-line evidence on every structural edge.

No Blender installation is required because this tool does not execute the
input.  It writes TXT, JSON, Mermaid Markdown, and Graphviz DOT outputs.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence


CHILD_TOKENS = (
    "child",
    "dependent",
    "attached",
    "part",
    "piece",
    "limb",
)
PARENT_TOKENS = (
    "parent",
    "target",
    "host",
    "support",
    "base",
    "body",
    "root",
    "anchor",
    "surface",
    "frame",
    "container",
)


@dataclass
class Definition:
    id: str
    name: str
    qualname: str
    kind: str
    line: int
    end_line: int
    parent: str | None
    parameters: list[str] = field(default_factory=list)
    docstring: str | None = None
    internal_calls: list[str] = field(default_factory=list)
    external_calls: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GraphEdge:
    parent: str
    child: str
    relation: str
    line: int
    evidence: str


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Parse a Python/Blender script and render its module tree, "
            "internal call tree, and Blender part-attachment tree."
        )
    )
    parser.add_argument("source", type=Path, help="Python source file to parse")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="output directory (default: <source_dir>/structure_tree)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=10,
        help="maximum recursive depth in the textual call tree",
    )
    return parser.parse_args()


def _attribute_name(value: ast.AST) -> str | None:
    parts: list[str] = []
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if isinstance(value, ast.Name):
        parts.append(value.id)
        return ".".join(reversed(parts))
    return None


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return _attribute_name(call.func)
    return None


def _root_name(value: ast.AST) -> str | None:
    while isinstance(value, (ast.Attribute, ast.Subscript)):
        value = value.value
    return value.id if isinstance(value, ast.Name) else None


def _assigned_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        return {
            name
            for item in target.elts
            for name in _assigned_names(item)
        }
    return set()


def _names_in(value: ast.AST) -> set[str]:
    return {
        node.id
        for node in ast.walk(value)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }


def _expression_sources(value: ast.AST, taints: dict[str, set[str]]) -> set[str]:
    sources: set[str] = set()
    for node in ast.walk(value):
        if isinstance(node, ast.Attribute):
            root = _root_name(node)
            if root is not None:
                sources.add(root)
        elif isinstance(node, ast.Name):
            sources.update(taints.get(node.id, ()))
    return sources


def _one_way_dataflow(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    source_name: str,
    sink_name: str,
) -> bool:
    """Prove a small source-parameter -> sink-object mutation path."""
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
        values = [*call.args, *(keyword.value for keyword in call.keywords)]
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


def _attachment_specs(tree: ast.AST) -> dict[str, dict[str, object]]:
    specs: dict[str, dict[str, object]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        names = [argument.arg for argument in node.args.args]
        child = next(
            (
                name
                for name in names
                if any(token in name.lower() for token in CHILD_TOKENS)
            ),
            None,
        )
        parent = next(
            (
                name
                for name in names
                if any(token in name.lower() for token in PARENT_TOKENS)
            ),
            None,
        )
        if child is None or parent is None or child == parent:
            continue
        forward = _one_way_dataflow(node, parent, child)
        reverse = _one_way_dataflow(node, child, parent)
        specs[node.name] = {
            "names": names,
            "child": child,
            "parent": parent,
            "code_directed": bool(forward and not reverse),
        }
    return specs


def _method_dataflow_links(tree: ast.AST) -> dict[tuple[int, int], set[tuple[str, str]]]:
    """Find ``source.attr -> temporary -> sink.method(temporary)`` paths."""
    scopes: list[ast.AST] = [
        tree,
        *(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ),
    ]
    result: dict[tuple[int, int], set[tuple[str, str]]] = {}
    for scope in scopes:
        taints: dict[str, set[str]] = {}
        body = getattr(scope, "body", [])
        nodes = sorted(
            (
                node
                for statement in body
                for node in ast.walk(statement)
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
            if sink is None:
                continue
            values = [*node.args, *(keyword.value for keyword in node.keywords)]
            sources = {
                source
                for value in values
                for source in _expression_sources(value, taints)
                if source != sink
            }
            if sources:
                result.setdefault(
                    (int(node.lineno), int(node.col_offset)), set()
                ).update((sink, source) for source in sources)
    return result


def _call_argument(
    call: ast.Call,
    names: Sequence[str],
    wanted: str,
) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == wanted:
            return keyword.value
    try:
        index = names.index(wanted)
    except ValueError:
        return None
    return call.args[index] if index < len(call.args) else None


def _summary_expr(value: ast.AST, limit: int = 110) -> str:
    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        return f"{type(value).__name__.lower()}[{len(value.elts)}]"
    if isinstance(value, ast.Dict):
        return f"dict[{len(value.keys)}]"
    text = ast.unparse(value)
    text = re.sub(r"\s+", " ", text).strip()
    if "np.array" in text and ".reshape" in text:
        match = re.search(r"\.reshape\(([^)]*)\)\s*$", text)
        if match:
            return f"np.array(...).reshape({match.group(1)})"
    return text if len(text) <= limit else text[: limit - 3] + "..."


class _LocalCallCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)
        if name:
            self.calls.append((name, int(node.lineno)))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return


def _looks_like_component_creator(definition: Definition) -> bool:
    """Identify high-level part builders while excluding render utilities."""
    name = definition.name.lower().lstrip("_")
    prefixes = (
        "create_",
        "build_",
        "make_",
        "generate_",
        "gen_",
        "assemble_",
        "spawn_",
        "fabricate_",
        "construct_",
        "grow_",
        "invoke_",
    )
    exact = {
        "create",
        "build",
        "make",
        "entry",
        "revolve",
        "create_asset",
        "build_asset",
        "make_asset",
        "assemble",
    }
    if not (name.startswith(prefixes) or name in exact):
        return False
    utility_tokens = (
        "nodegroup",
        "node_group",
        "geometry_node",
        "geo_",
        "group",
        "material",
        "shader",
        "texture",
        "modifier",
        "attribute",
        "socket",
        "selection",
        "transform",
        "noise",
        "clone",
        "duplicate",
        "copy_",
        "join_",
    )
    return not any(token in name for token in utility_tokens)


class SourceStructure:
    def __init__(self, source_path: Path, source: str, tree: ast.Module) -> None:
        self.source_path = source_path
        self.source = source
        self.tree = tree
        self.imports: list[dict[str, object]] = []
        self.constants: list[dict[str, object]] = []
        self.definitions: dict[str, Definition] = {}
        self.definition_nodes: dict[str, ast.AST] = {}
        self.raw_calls: dict[str, list[tuple[str, int]]] = {}
        self.module_calls: list[tuple[str, int]] = []
        self.call_edges: list[GraphEdge] = []
        self.entrypoints: list[str] = []
        self.attachment_helpers = _attachment_specs(tree)
        self.method_links = _method_dataflow_links(tree)
        self.part_edges: list[GraphEdge] = []
        self.part_nodes: set[str] = set()
        self.part_metadata: dict[str, dict[str, object]] = {}

    def analyze(self) -> None:
        self._collect_module_items()
        self._collect_definitions(self.tree.body, None, None)
        self._collect_module_calls()
        self._resolve_calls()
        self._find_entrypoints()
        self._collect_part_edges()

    def _collect_module_items(self) -> None:
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                self.imports.extend(
                    {
                        "kind": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": int(node.lineno),
                    }
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                module = "." * node.level + (node.module or "")
                self.imports.extend(
                    {
                        "kind": "from",
                        "module": module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": int(node.lineno),
                    }
                    for alias in node.names
                )
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                value = getattr(node, "value", None)
                if value is None:
                    continue
                for target in targets:
                    for name in sorted(_assigned_names(target)):
                        if name.isupper():
                            self.constants.append(
                                {
                                    "name": name,
                                    "line": int(node.lineno),
                                    "value": _summary_expr(value),
                                }
                            )

    def _collect_definitions(
        self,
        body: Sequence[ast.stmt],
        parent: str | None,
        class_owner: str | None,
    ) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                qualname = f"{parent}.{node.name}" if parent else node.name
                definition = Definition(
                    id=qualname,
                    name=node.name,
                    qualname=qualname,
                    kind="class",
                    line=int(node.lineno),
                    end_line=int(getattr(node, "end_lineno", node.lineno)),
                    parent=parent,
                    docstring=ast.get_docstring(node),
                )
                self.definitions[qualname] = definition
                self.definition_nodes[qualname] = node
                self._collect_definitions(node.body, qualname, qualname)
                continue
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            qualname = f"{parent}.{node.name}" if parent else node.name
            if class_owner and parent == class_owner:
                kind = "method"
            elif parent:
                kind = "nested_function"
            else:
                kind = "function"
            parameters = [
                argument.arg
                for argument in [
                    *node.args.posonlyargs,
                    *node.args.args,
                    *node.args.kwonlyargs,
                ]
            ]
            if node.args.vararg:
                parameters.append("*" + node.args.vararg.arg)
            if node.args.kwarg:
                parameters.append("**" + node.args.kwarg.arg)
            definition = Definition(
                id=qualname,
                name=node.name,
                qualname=qualname,
                kind=kind,
                line=int(node.lineno),
                end_line=int(getattr(node, "end_lineno", node.lineno)),
                parent=parent,
                parameters=parameters,
                docstring=ast.get_docstring(node),
            )
            self.definitions[qualname] = definition
            self.definition_nodes[qualname] = node
            collector = _LocalCallCollector()
            for statement in node.body:
                collector.visit(statement)
            self.raw_calls[qualname] = collector.calls
            self._collect_definitions(node.body, qualname, class_owner)

    def _resolve_call(self, caller: str, raw_name: str) -> str | None:
        simple = raw_name.rsplit(".", 1)[-1]
        caller_definition = self.definitions[caller]

        if raw_name.startswith(("self.", "cls.")):
            owner = caller_definition.parent
            while owner and self.definitions.get(owner, Definition("", "", "", "", 0, 0, None)).kind != "class":
                owner = self.definitions[owner].parent
            candidate = f"{owner}.{simple}" if owner else None
            if candidate in self.definitions:
                return candidate

        nested = f"{caller}.{simple}"
        if nested in self.definitions:
            return nested
        if simple in self.definitions and self.definitions[simple].kind == "function":
            return simple

        matches = [
            definition.id
            for definition in self.definitions.values()
            if definition.name == simple and definition.kind != "class"
        ]
        return sorted(matches, key=lambda value: (value.count("."), value))[0] if len(matches) == 1 else None

    def _resolve_calls(self) -> None:
        edges: dict[tuple[str, str], GraphEdge] = {}
        for caller, calls in self.raw_calls.items():
            internal: list[str] = []
            external: list[str] = []
            for raw_name, line in calls:
                target = self._resolve_call(caller, raw_name)
                if target is None:
                    external.append(raw_name)
                    continue
                internal.append(target)
                edges.setdefault(
                    (caller, target),
                    GraphEdge(caller, target, "CALL", line, f"AST call at L{line}"),
                )
            self.definitions[caller].internal_calls = sorted(set(internal))
            self.definitions[caller].external_calls = sorted(set(external))
        self.call_edges = sorted(
            edges.values(), key=lambda edge: (edge.parent, edge.line, edge.child)
        )

    def _collect_module_calls(self) -> None:
        collector = _LocalCallCollector()
        for statement in self.tree.body:
            collector.visit(statement)
        self.module_calls = collector.calls

    def _module_call_names(self) -> list[str]:
        return [name for name, _line in self.module_calls]

    def _find_entrypoints(self) -> None:
        roots: list[str] = []
        for raw_name in self._module_call_names():
            simple = raw_name.rsplit(".", 1)[-1]
            if simple in self.definitions and self.definitions[simple].kind == "function":
                roots.append(simple)
                continue
            matches = [
                definition.id
                for definition in self.definitions.values()
                if definition.name == simple and definition.kind != "class"
            ]
            if len(matches) == 1:
                roots.append(matches[0])
        if not roots and "main" in self.definitions:
            roots.append("main")
        if not roots:
            children = {edge.child for edge in self.call_edges}
            roots.extend(
                definition.id
                for definition in self.definitions.values()
                if definition.kind == "function" and definition.id not in children
            )
        self.entrypoints = list(dict.fromkeys(roots))

    def _collect_part_edges(self) -> None:
        edges: dict[tuple[str, str], GraphEdge] = {}
        # Assembly is frequently written directly at module scope (for
        # example, ``mattress.parent = frame``).  Analyze that scope as well as
        # function bodies; the collector intentionally does not descend into
        # nested definitions, so evidence is not duplicated here.
        module_aliases = _part_aliases(self.tree)
        module_collector = _PartEdgeCollector(
            aliases=module_aliases,
            specs=self.attachment_helpers,
            method_links=self.method_links,
        )
        module_collector.visit_statements(self.tree.body)
        for edge in module_collector.edges:
            edges[(edge.parent, edge.child)] = edge

        for definition_id, node in self.definition_nodes.items():
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            aliases = _part_aliases(node)
            collector = _PartEdgeCollector(
                aliases=aliases,
                specs=self.attachment_helpers,
                method_links=self.method_links,
            )
            collector.visit_statements(node.body)
            for edge in collector.edges:
                key = (edge.parent, edge.child)
                previous = edges.get(key)
                if previous is None or _edge_priority(edge) > _edge_priority(previous):
                    edges[key] = edge
        self.part_edges = sorted(
            edges.values(), key=lambda edge: (edge.parent, edge.child, edge.line)
        )
        self.part_nodes = {
            *(edge.parent for edge in self.part_edges),
            *(edge.child for edge in self.part_edges),
        }
        if self.part_edges:
            self._collect_explicit_part_metadata()
        else:
            self._collect_component_fallback()

    def _resolve_creator_name(self, caller: str | None, raw_name: str) -> str | None:
        if caller is not None:
            resolved = self._resolve_call(caller, raw_name)
            if resolved is not None:
                return resolved
        simple = raw_name.rsplit(".", 1)[-1]
        matches = [
            definition.id
            for definition in self.definitions.values()
            if definition.name == simple and definition.kind != "class"
        ]
        return matches[0] if len(matches) == 1 else None

    def _collect_explicit_part_metadata(self) -> None:
        """Attach creator-function and runtime-variable evidence to part nodes."""
        scopes: list[tuple[str | None, ast.AST]] = [(None, self.tree)]
        scopes.extend(
            (definition_id, node)
            for definition_id, node in self.definition_nodes.items()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        for caller, scope in scopes:
            aliases = _part_aliases(scope)
            creator_by_variable: dict[str, str] = {}
            assignments = sorted(
                (
                    node
                    for node in _scope_nodes(scope)
                    if isinstance(node, (ast.Assign, ast.AnnAssign))
                ),
                key=lambda node: (int(getattr(node, "lineno", 0)), int(getattr(node, "col_offset", 0))),
            )
            for assignment in assignments:
                value = getattr(assignment, "value", None)
                if not isinstance(value, ast.Call):
                    continue
                targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
                target_names = {
                    name
                    for target in targets
                    for name in _assigned_names(target)
                }
                raw_name = _call_name(value) or ""
                short_name = raw_name.rsplit(".", 1)[-1].lower()
                if any(token in short_name for token in ("clone", "copy", "duplicate")):
                    source_name = _root_name(value.args[0]) if value.args else None
                    inherited = creator_by_variable.get(source_name or "")
                    if inherited:
                        for target_name in target_names:
                            creator_by_variable[target_name] = inherited
                    continue
                resolved = self._resolve_creator_name(caller, raw_name) if raw_name else None
                if resolved is None:
                    continue
                definition = self.definitions.get(resolved)
                if definition is None or not _looks_like_component_creator(definition):
                    continue
                for target_name in target_names:
                    creator_by_variable[target_name] = resolved

            variables = {**{name: name for name in creator_by_variable}, **aliases}
            for variable, label in variables.items():
                if label not in self.part_nodes:
                    continue
                metadata = self.part_metadata.setdefault(label, {})
                metadata.setdefault("label", label)
                metadata.setdefault("kind", "blender_part")
                metadata.setdefault("line", 0)
                metadata.setdefault("group", "Blender parts")
                metadata.setdefault("runtime_variable", variable)
                creator = creator_by_variable.get(variable)
                if creator:
                    metadata["creator_function"] = creator

    def _collect_component_fallback(self) -> None:
        """Build a useful construction tree when Blender parenting is absent.

        Most benchmark scripts join meshes instead of assigning ``obj.parent``.
        In that case, the real high-level structure is expressed by creator
        functions calling other creator functions.  Preserve that hierarchy
        and anchor it beneath a synthetic model root.  Flat, function-free
        scripts fall back to their module-scope Blender object variables.
        """
        model_id = f"model:{self.source_path.stem}"
        self.part_nodes.add(model_id)
        self.part_metadata[model_id] = {
            "label": self.source_path.stem,
            "kind": "model_root",
            "line": 1,
            "creator_function": None,
            "group": "Model",
        }

        candidates = {
            definition.id: definition
            for definition in self.definitions.values()
            if _looks_like_component_creator(definition)
        }
        node_for = {
            definition_id: f"component:{definition_id}"
            for definition_id in candidates
        }
        for definition_id, definition in candidates.items():
            node_id = node_for[definition_id]
            self.part_nodes.add(node_id)
            self.part_metadata[node_id] = {
                "label": f"{definition.name}()",
                "kind": "component_creator",
                "line": definition.line,
                "creator_function": definition.qualname,
                "group": "Component creators",
            }

        component_edges: dict[tuple[str, str], GraphEdge] = {}
        for edge in self.call_edges:
            if edge.parent not in candidates or edge.child not in candidates:
                continue
            parent = node_for[edge.parent]
            child = node_for[edge.child]
            if parent == child:
                continue
            component_edges[(parent, child)] = GraphEdge(
                parent,
                child,
                "BUILDS_COMPONENT",
                edge.line,
                f"{candidates[edge.parent].name} calls {candidates[edge.child].name}",
            )

        if candidates:
            incoming = {edge.child for edge in component_edges.values()}
            roots = [
                definition_id
                for definition_id, definition in sorted(
                    candidates.items(), key=lambda item: item[1].line
                )
                if node_for[definition_id] not in incoming
            ]
            if not roots:
                roots = [min(candidates, key=lambda item: candidates[item].line)]
            for definition_id in roots:
                definition = candidates[definition_id]
                child = node_for[definition_id]
                component_edges[(model_id, child)] = GraphEdge(
                    model_id,
                    child,
                    "MODEL_COMPONENT",
                    definition.line,
                    "top-level component creator",
                )
            self.part_edges = sorted(
                component_edges.values(),
                key=lambda edge: (edge.parent, edge.line, edge.child),
            )
            return

        module_aliases = _part_aliases(self.tree)
        for index, (variable, label) in enumerate(sorted(module_aliases.items())):
            node_id = f"object:{variable}"
            self.part_nodes.add(node_id)
            self.part_metadata[node_id] = {
                "label": label if label != variable else variable,
                "kind": "blender_object",
                "line": 0,
                "creator_function": None,
                "runtime_variable": variable,
                "group": "Module objects",
            }
            self.part_edges.append(
                GraphEdge(
                    model_id,
                    node_id,
                    "MODULE_OBJECT",
                    index + 1,
                    f"module-scope Blender object variable: {variable}",
                )
            )


def _is_main_guard(test: ast.AST) -> bool:
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and any(
            isinstance(comparator, ast.Constant)
            and comparator.value == "__main__"
            for comparator in test.comparators
        )
    )


def _static_text(value: ast.AST, env: dict[str, object] | None = None) -> str | None:
    env = env or {}
    if isinstance(value, ast.Constant) and isinstance(value.value, (str, int, float)):
        return str(value.value)
    if isinstance(value, ast.Name):
        return str(env.get(value.id, "{" + value.id + "}"))
    if isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.USub):
        inner = _static_text(value.operand, env)
        return "-" + inner if inner is not None else None
    if isinstance(value, ast.JoinedStr):
        parts: list[str] = []
        for item in value.values:
            if isinstance(item, ast.Constant):
                parts.append(str(item.value))
            elif isinstance(item, ast.FormattedValue):
                rendered = _static_text(item.value, env)
                parts.append(rendered if rendered is not None else "{?}")
        return "".join(parts)
    return None


def _scope_nodes(scope: ast.AST) -> Iterable[ast.AST]:
    """Walk one lexical scope without entering nested definitions."""
    stack = list(reversed(getattr(scope, "body", [])))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        yield node
        children = list(ast.iter_child_nodes(node))
        for child in reversed(children):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            stack.append(child)


def _part_aliases(function: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in _scope_nodes(function):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = getattr(node, "value", None)
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]

        if isinstance(value, ast.Call):
            full_call_name = _call_name(value) or ""
            call_name = full_call_name.rsplit(".", 1)[-1]
            label_node = next(
                (keyword.value for keyword in value.keywords if keyword.arg == "label"),
                None,
            )
            label = _static_text(label_node) if label_node is not None else None
            if full_call_name == "bpy.data.objects.new" and value.args:
                label = _static_text(value.args[0]) or label
            creation_like = (
                label is not None
                or full_call_name == "bpy.data.objects.new"
                or call_name.endswith("State")
                or call_name.startswith(
                    ("create_", "new_", "build_", "make_", "generate_", "spawn_")
                )
                or call_name in {"create_asset", "build_asset", "make_asset"}
            )
            if creation_like:
                for target in targets:
                    for name in _assigned_names(target):
                        aliases[name] = label or name

        if isinstance(value, ast.Attribute):
            full_value_name = _attribute_name(value)
            if full_value_name in {"bpy.context.active_object", "bpy.context.object"}:
                for target in targets:
                    for name in _assigned_names(target):
                        aliases.setdefault(name, name)

        for target in targets:
            if isinstance(target, ast.Attribute) and target.attr in {"name", "label"}:
                root = _root_name(target.value)
                label = _static_text(value) if value is not None else None
                if root and label:
                    aliases[root] = label
    return aliases


def _literal_iter_values(value: ast.AST) -> list[object] | None:
    if isinstance(value, (ast.Tuple, ast.List, ast.Set)):
        result: list[object] = []
        for item in value.elts:
            text = _static_text(item, {})
            if text is None:
                return None
            try:
                result.append(int(text))
            except ValueError:
                result.append(text)
        return result
    if (
        isinstance(value, ast.Call)
        and _call_name(value) == "range"
        and all(isinstance(item, ast.Constant) and isinstance(item.value, int) for item in value.args)
    ):
        values = [int(item.value) for item in value.args]
        return list(range(*values))
    return None


def _format_alias(template: str, env: dict[str, object]) -> str:
    try:
        return template.format_map({key: value for key, value in env.items()})
    except (KeyError, ValueError):
        return template


class _PartEdgeCollector:
    def __init__(
        self,
        aliases: dict[str, str],
        specs: dict[str, dict[str, object]],
        method_links: dict[tuple[int, int], set[tuple[str, str]]],
    ) -> None:
        self.aliases = aliases
        self.specs = specs
        self.method_links = method_links
        self.env: dict[str, object] = {}
        self.edges: list[GraphEdge] = []

    def _entity(self, value: ast.AST | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, ast.Name):
            template = self.aliases.get(value.id, value.id)
            return _format_alias(template, self.env)
        root = _root_name(value)
        if root:
            template = self.aliases.get(root, root)
            return _format_alias(template, self.env)
        return _static_text(value, self.env)

    def _add(self, parent: str | None, child: str | None, relation: str, line: int, evidence: str) -> None:
        if not parent or not child or parent == child:
            return
        if parent in {"Matrix", "Vector", "np", "numpy", "bpy", "math"}:
            return
        self.edges.append(GraphEdge(parent, child, relation, line, evidence))

    def visit_statements(self, statements: Sequence[ast.stmt]) -> None:
        for statement in statements:
            self.visit(statement)

    def visit(self, node: ast.AST) -> None:
        method = getattr(self, "visit_" + type(node).__name__, self.generic_visit)
        method(node)

    def generic_visit(self, node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            self.visit(child)

    def visit_For(self, node: ast.For) -> None:
        values = _literal_iter_values(node.iter)
        if isinstance(node.target, ast.Name) and values:
            old = self.env.get(node.target.id, None)
            had_old = node.target.id in self.env
            for value in values:
                self.env[node.target.id] = value
                self.visit_statements(node.body)
            if had_old:
                self.env[node.target.id] = old
            else:
                self.env.pop(node.target.id, None)
        else:
            self.visit_statements(node.body)
        self.visit_statements(node.orelse)

    def visit_Call(self, node: ast.Call) -> None:
        short_name = (_call_name(node) or "").rsplit(".", 1)[-1]
        spec = self.specs.get(short_name)
        if spec:
            names = spec["names"]
            child_value = _call_argument(node, names, str(spec["child"]))
            parent_value = _call_argument(node, names, str(spec["parent"]))
            relation = "DIRECTED_CODE" if spec["code_directed"] else "ATTACHMENT_CALL"
            self._add(
                self._entity(parent_value),
                self._entity(child_value),
                relation,
                int(node.lineno),
                f"{short_name} call",
            )

        for sink, source in sorted(
            self.method_links.get(
                (int(node.lineno), int(node.col_offset)), set()
            )
        ):
            if sink not in self.aliases or source not in self.aliases:
                continue
            self._add(
                _format_alias(self.aliases[source], self.env),
                _format_alias(self.aliases[sink], self.env),
                "METHOD_DATAFLOW",
                int(node.lineno),
                f"{source} data reaches {sink}.{short_name}",
            )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if not isinstance(target, ast.Attribute) or target.attr != "parent":
                continue
            if isinstance(node.value, ast.Constant) and node.value.value is None:
                continue
            child_root = _root_name(target.value)
            if child_root not in self.aliases:
                # A loop placeholder such as ``for part in parts`` cannot be
                # resolved to a concrete static object.  Runtime SR-F1 can
                # expand it, but emitting ``root -> part`` here would invent a
                # fake semantic node, so leave it out of the static tree.
                continue
            self._add(
                self._entity(node.value),
                self._entity(target.value),
                "PARENT_ASSIGNMENT",
                int(node.lineno),
                "object.parent assignment",
            )
        self.generic_visit(node)


def _edge_priority(edge: GraphEdge) -> int:
    return {
        "DIRECTED_CODE": 4,
        "PARENT_ASSIGNMENT": 3,
        "METHOD_DATAFLOW": 2,
        "ATTACHMENT_CALL": 1,
    }.get(edge.relation, 0)


def _tree_lines(
    roots: Sequence[str],
    edges: Sequence[GraphEdge],
    label_for,
    max_depth: int,
) -> list[str]:
    adjacency: dict[str, list[GraphEdge]] = {}
    for edge in edges:
        adjacency.setdefault(edge.parent, []).append(edge)
    for children in adjacency.values():
        children.sort(key=lambda edge: (edge.line, edge.child))

    lines: list[str] = []

    def walk(node: str, prefix: str, path: set[str], depth: int) -> None:
        children = adjacency.get(node, [])
        if depth >= max_depth and children:
            lines.append(prefix + "└── … [max depth]")
            return
        for index, edge in enumerate(children):
            last = index == len(children) - 1
            connector = "└── " if last else "├── "
            suffix = f" [{edge.relation}, L{edge.line}]"
            cycle = edge.child in path
            lines.append(prefix + connector + label_for(edge.child) + suffix + (" ↩ cycle" if cycle else ""))
            if not cycle:
                walk(
                    edge.child,
                    prefix + ("    " if last else "│   "),
                    path | {edge.child},
                    depth + 1,
                )

    for root_index, root in enumerate(roots):
        if root_index:
            lines.append("")
        lines.append(label_for(root))
        walk(root, "", {root}, 0)
    return lines


def _definition_tree_lines(structure: SourceStructure) -> list[str]:
    lines = [f"MODULE {structure.source_path.name}"]
    groups = [
        ("Imports", [f"{item.get('module')}" + (f".{item['name']}" if item.get("name") else "") for item in structure.imports]),
        ("Constants", [f"{item['name']} = {item['value']} [L{item['line']}]" for item in structure.constants]),
    ]
    top_classes = [item for item in structure.definitions.values() if item.kind == "class" and item.parent is None]
    top_functions = [item for item in structure.definitions.values() if item.kind == "function" and item.parent is None]
    groups.append(("Classes", [item.id for item in sorted(top_classes, key=lambda value: value.line)]))
    groups.append(("Functions", [item.id for item in sorted(top_functions, key=lambda value: value.line)]))

    nonempty = [(name, values) for name, values in groups if values]
    for group_index, (group_name, values) in enumerate(nonempty):
        group_last = group_index == len(nonempty) - 1
        group_connector = "└── " if group_last else "├── "
        lines.append(group_connector + group_name)
        group_prefix = "    " if group_last else "│   "
        for index, value in enumerate(values):
            last = index == len(values) - 1
            connector = "└── " if last else "├── "
            if group_name in {"Classes", "Functions"}:
                definition = structure.definitions[value]
                lines.append(group_prefix + connector + f"{definition.name} [L{definition.line}-{definition.end_line}]")
                child_defs = sorted(
                    (
                        item
                        for item in structure.definitions.values()
                        if item.parent == definition.id
                    ),
                    key=lambda item: item.line,
                )
                child_prefix = group_prefix + ("    " if last else "│   ")
                for child_index, child in enumerate(child_defs):
                    child_last = child_index == len(child_defs) - 1
                    child_connector = "└── " if child_last else "├── "
                    lines.append(
                        child_prefix
                        + child_connector
                        + f"{child.kind}: {child.name}({', '.join(child.parameters)}) [L{child.line}-{child.end_line}]"
                    )
            else:
                lines.append(group_prefix + connector + value)
    return lines


def _call_roots(structure: SourceStructure) -> list[str]:
    return structure.entrypoints


def _part_roots(
    edges: Sequence[GraphEdge],
    nodes: Iterable[str] = (),
) -> list[str]:
    parents = {edge.parent for edge in edges}
    children = {edge.child for edge in edges}
    all_nodes = {*(parents | children), *nodes}
    roots = sorted((parents - children) | (all_nodes - parents - children))
    return roots or sorted(all_nodes)[:1]


def _text_report(structure: SourceStructure, max_depth: int) -> str:
    lines = ["CODE DEFINITION TREE", "=" * 80]
    lines.extend(_definition_tree_lines(structure))
    lines.extend(["", "EXECUTION CALL TREE", "=" * 80])

    definition_labels = {
        definition.id: f"{definition.qualname} [L{definition.line}]"
        for definition in structure.definitions.values()
    }
    if structure.call_edges and _call_roots(structure):
        lines.extend(
            _tree_lines(
                _call_roots(structure),
                structure.call_edges,
                lambda node: definition_labels.get(node, node),
                max_depth,
            )
        )
    else:
        lines.append("(no internal call tree found)")

    lines.extend(["", "BLENDER PART / ATTACHMENT TREE", "=" * 80])
    if structure.part_nodes:
        lines.extend(
            _tree_lines(
                _part_roots(structure.part_edges, structure.part_nodes),
                structure.part_edges,
                lambda node: str(
                    structure.part_metadata.get(node, {}).get("label", node)
                ),
                max_depth,
            )
        )
    else:
        lines.append("(no attachment evidence found)")

    lines.extend(["", "ATTACHMENT EVIDENCE", "=" * 80])
    if structure.part_edges:
        for edge in structure.part_edges:
            lines.append(
                f"L{edge.line}: {edge.parent} -> {edge.child} "
                f"[{edge.relation}] {edge.evidence}"
            )
    else:
        lines.append("(none)")
    return "\n".join(lines) + "\n"


def _safe_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def _mermaid_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', "&quot;")


def _mermaid_graph(
    title: str,
    edges: Sequence[GraphEdge],
    roots: Sequence[str],
    prefix: str,
    labels: dict[str, str] | None = None,
) -> list[str]:
    labels = labels or {}
    nodes = sorted({*roots, *(edge.parent for edge in edges), *(edge.child for edge in edges)})
    lines = [f"## {title}", "", "```mermaid", "flowchart TD"]
    for node in nodes:
        node_id = _safe_id(prefix, node)
        label = _mermaid_label(labels.get(node, node))
        lines.append(f'    {node_id}["{label}"]')
    for edge in edges:
        parent_id = _safe_id(prefix, edge.parent)
        child_id = _safe_id(prefix, edge.child)
        edge_label = _mermaid_label(f"{edge.relation} · L{edge.line}")
        lines.append(f'    {parent_id} -->|"{edge_label}"| {child_id}')
    lines.extend(["```", ""])
    return lines


def _markdown_report(structure: SourceStructure, text_report: str) -> str:
    labels = {
        definition.id: f"{definition.qualname}<br/>L{definition.line}"
        for definition in structure.definitions.values()
    }
    lines = [
        f"# {structure.source_path.name} — Code Structure Tree",
        "",
        f"Source: `{structure.source_path}`",
        "",
        "## Text tree",
        "",
        "```text",
        text_report.rstrip(),
        "```",
        "",
    ]
    lines.extend(
        _mermaid_graph(
            "Execution call graph",
            structure.call_edges,
            _call_roots(structure),
            "call",
            labels,
        )
    )
    lines.extend(
        _mermaid_graph(
            "Blender part attachment tree",
            structure.part_edges,
            _part_roots(structure.part_edges, structure.part_nodes),
            "part",
            {
                node: str(structure.part_metadata.get(node, {}).get("label", node))
                for node in structure.part_nodes
            },
        )
    )
    return "\n".join(lines)


def _dot_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _dot_report(structure: SourceStructure) -> str:
    lines = [
        "digraph CodeStructureTree {",
        '  rankdir="TB";',
        '  graph [fontname="Helvetica"];',
        '  node [shape="box", fontname="Helvetica"];',
        '  edge [fontname="Helvetica"];',
        "  subgraph cluster_calls {",
        '    label="Execution call graph";',
        '    color="#d0d7de";',
    ]
    call_nodes = sorted(
        {
            *(edge.parent for edge in structure.call_edges),
            *(edge.child for edge in structure.call_edges),
            *structure.entrypoints,
        }
    )
    for node in call_nodes:
        definition = structure.definitions.get(node)
        label = f"{node}\\nL{definition.line}" if definition else node
        lines.append(f"    {_dot_quote('call:' + node)} [label={_dot_quote(label)}];")
    for edge in structure.call_edges:
        lines.append(
            f"    {_dot_quote('call:' + edge.parent)} -> {_dot_quote('call:' + edge.child)} "
            f"[label={_dot_quote('L' + str(edge.line))}, color=\"#57606a\"];"
        )
    lines.extend(["  }", "  subgraph cluster_parts {", '    label="Blender part attachment tree";', '    color="#54aeff";'])
    part_nodes = sorted(
        {
            *structure.part_nodes,
            *(edge.parent for edge in structure.part_edges),
            *(edge.child for edge in structure.part_edges),
        }
    )
    for node in part_nodes:
        label = str(structure.part_metadata.get(node, {}).get("label", node))
        lines.append(f"    {_dot_quote('part:' + node)} [label={_dot_quote(label)}];")
    for edge in structure.part_edges:
        label = f"{edge.relation}\\nL{edge.line}"
        lines.append(
            f"    {_dot_quote('part:' + edge.parent)} -> {_dot_quote('part:' + edge.child)} "
            f"[label={_dot_quote(label)}, color=\"#0969da\"];"
        )
    lines.extend(["  }", "}"])
    return "\n".join(lines) + "\n"


def _json_report(structure: SourceStructure) -> dict[str, object]:
    part_nodes = sorted(
        {
            *structure.part_nodes,
            *(edge.parent for edge in structure.part_edges),
            *(edge.child for edge in structure.part_edges),
        }
    )
    return {
        "schema_version": "1.0",
        "source": str(structure.source_path),
        "summary": {
            "imports": len(structure.imports),
            "constants": len(structure.constants),
            "definitions": len(structure.definitions),
            "internal_call_edges": len(structure.call_edges),
            "attachment_helpers": len(structure.attachment_helpers),
            "part_nodes": len(part_nodes),
            "part_edges": len(structure.part_edges),
        },
        "imports": structure.imports,
        "constants": structure.constants,
        "definitions": [
            asdict(definition)
            for definition in sorted(
                structure.definitions.values(), key=lambda item: item.line
            )
        ],
        "entrypoints": structure.entrypoints,
        "call_edges": [asdict(edge) for edge in structure.call_edges],
        "attachment_helpers": [
            {
                "function": name,
                "child_parameter": spec["child"],
                "parent_parameter": spec["parent"],
                "code_directed": spec["code_directed"],
            }
            for name, spec in sorted(structure.attachment_helpers.items())
        ],
        "part_tree": {
            "roots": _part_roots(structure.part_edges, structure.part_nodes),
            "nodes": part_nodes,
            "metadata": structure.part_metadata,
            "edges": [asdict(edge) for edge in structure.part_edges],
        },
    }


def _source_section_markers(source: str) -> list[tuple[int, str]]:
    """Recover human-authored code sections from banner comments."""
    lines = source.splitlines()
    banner = re.compile(r"^\s*#\s*[=\-]{8,}\s*$")
    markers: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#") or banner.match(line):
            continue
        title = stripped.removeprefix("#").strip()
        if not title:
            continue
        previous_is_banner = index > 0 and banner.match(lines[index - 1])
        next_is_banner = index + 1 < len(lines) and banner.match(lines[index + 1])
        if previous_is_banner or next_is_banner:
            markers.append((index + 1, title))
    return markers


def _source_section_for_line(
    markers: Sequence[tuple[int, str]],
    line: int,
) -> tuple[int, str]:
    selected = (1, "Module setup")
    for marker in markers:
        if marker[0] > line:
            break
        selected = marker
    return selected


def _interactive_data(structure: SourceStructure) -> dict[str, object]:
    module_id = f"module:{structure.source_path.name}"
    section_markers = _source_section_markers(structure.source)
    definition_sections = {
        definition.id: _source_section_for_line(section_markers, definition.line)
        for definition in structure.definitions.values()
    }
    top_level_sections = {
        definition_sections[definition.id]
        for definition in structure.definitions.values()
        if definition.parent is None
    }
    section_ids = {
        section: _safe_id("section", f"{section[0]}:{section[1]}")
        for section in sorted(top_level_sections)
    }
    definition_nodes: list[dict[str, object]] = [
        {
            "id": module_id,
            "label": structure.source_path.name,
            "kind": "module",
            "line": 1,
            "end_line": len(structure.source.splitlines()),
            "parameters": [],
            "docstring": None,
            "group": "Module",
        }
    ]
    definition_edges: list[dict[str, object]] = []
    for section in sorted(top_level_sections):
        line, title = section
        section_id = section_ids[section]
        definition_nodes.append(
            {
                "id": section_id,
                "label": title,
                "kind": "section",
                "line": line,
                "end_line": line,
                "parameters": [],
                "docstring": None,
                "group": title,
            }
        )
        definition_edges.append(
            {
                "parent": module_id,
                "child": section_id,
                "relation": "SECTION",
                "line": line,
                "evidence": "source banner comment",
            }
        )
    for definition in sorted(structure.definitions.values(), key=lambda item: item.line):
        section = definition_sections[definition.id]
        section_title = section[1]
        definition_nodes.append(
            {
                "id": definition.id,
                "label": definition.name,
                "kind": definition.kind,
                "line": definition.line,
                "end_line": definition.end_line,
                "parameters": definition.parameters,
                "docstring": definition.docstring,
                "group": section_title,
            }
        )
        definition_edges.append(
            {
                "parent": definition.parent or section_ids[section],
                "child": definition.id,
                "relation": "CONTAINS" if definition.parent else "SECTION_MEMBER",
                "line": definition.line,
                "evidence": (
                    "AST lexical scope"
                    if definition.parent
                    else f"source section: {section_title}"
                ),
            }
        )

    call_node_ids = sorted(
        {
            *structure.entrypoints,
            *(edge.parent for edge in structure.call_edges),
            *(edge.child for edge in structure.call_edges),
        }
    )
    call_nodes = [
        {
            "id": module_id,
            "label": structure.source_path.name,
            "kind": "module",
            "line": 1,
            "end_line": len(structure.source.splitlines()),
            "parameters": [],
            "docstring": None,
            "group": "Module",
        }
    ]
    for node_id in call_node_ids:
        definition = structure.definitions.get(node_id)
        call_nodes.append(
            {
                "id": node_id,
                "label": definition.name if definition else node_id,
                "kind": definition.kind if definition else "callable",
                "line": definition.line if definition else 0,
                "end_line": definition.end_line if definition else 0,
                "parameters": definition.parameters if definition else [],
                "docstring": definition.docstring if definition else None,
                "group": (
                    definition_sections.get(node_id, (1, "Module setup"))[1]
                    if definition
                    else "Other"
                ),
            }
        )

    call_edges = [asdict(edge) for edge in structure.call_edges]
    entry_line_by_id: dict[str, int] = {}
    for raw_name, line in structure.module_calls:
        simple = raw_name.rsplit(".", 1)[-1]
        for entrypoint in structure.entrypoints:
            definition = structure.definitions.get(entrypoint)
            if definition and definition.name == simple:
                entry_line_by_id.setdefault(entrypoint, line)
    for entrypoint in structure.entrypoints:
        call_edges.append(
            {
                "parent": module_id,
                "child": entrypoint,
                "relation": "ENTRYPOINT",
                "line": entry_line_by_id.get(
                    entrypoint,
                    structure.definitions.get(entrypoint, Definition("", "", "", "", 1, 1, None)).line,
                ),
                "evidence": "module-level invocation or inferred call root",
            }
        )

    # Function-free Blender scripts still have a meaningful execution graph.
    # Show their distinct top-level API calls instead of leaving this tab blank.
    if not call_node_ids:
        external_calls: dict[str, int] = {}
        for raw_name, line in structure.module_calls:
            external_calls.setdefault(raw_name, line)
        for raw_name, line in sorted(
            external_calls.items(), key=lambda item: (item[1], item[0])
        )[:48]:
            external_id = f"external:{raw_name}"
            call_nodes.append(
                {
                    "id": external_id,
                    "label": f"{raw_name}()",
                    "kind": "external_call",
                    "line": line,
                    "end_line": line,
                    "parameters": [],
                    "docstring": None,
                    "group": "Module API calls",
                }
            )
            call_edges.append(
                {
                    "parent": module_id,
                    "child": external_id,
                    "relation": "CALL",
                    "line": line,
                    "evidence": "top-level AST call",
                }
            )

    part_node_ids = sorted(
        {
            *structure.part_nodes,
            *(edge.parent for edge in structure.part_edges),
            *(edge.child for edge in structure.part_edges),
        }
    )
    evidence_by_node: dict[str, list[str]] = {node_id: [] for node_id in part_node_ids}
    for edge in structure.part_edges:
        description = (
            f"L{edge.line}: {edge.parent} -> {edge.child} "
            f"[{edge.relation}] {edge.evidence}"
        )
        evidence_by_node.setdefault(edge.parent, []).append(description)
        evidence_by_node.setdefault(edge.child, []).append(description)
    part_nodes = [
        {
            "id": node_id,
            "label": structure.part_metadata.get(node_id, {}).get("label", node_id),
            "kind": structure.part_metadata.get(node_id, {}).get("kind", "blender_part"),
            "line": structure.part_metadata.get(node_id, {}).get("line", 0),
            "end_line": 0,
            "parameters": [],
            "docstring": None,
            "evidence": evidence_by_node.get(node_id, []),
            "creator_function": structure.part_metadata.get(node_id, {}).get(
                "creator_function"
            ),
            "runtime_variable": structure.part_metadata.get(node_id, {}).get(
                "runtime_variable"
            ),
            "group": structure.part_metadata.get(node_id, {}).get(
                "group", "Blender parts"
            ),
        }
        for node_id in part_node_ids
    ]

    part_roots = _part_roots(structure.part_edges)
    connected_part_nodes = {
        *(edge.parent for edge in structure.part_edges),
        *(edge.child for edge in structure.part_edges),
    }
    part_roots.extend(
        node_id
        for node_id in part_node_ids
        if node_id not in connected_part_nodes and node_id not in part_roots
    )

    return {
        "source": str(structure.source_path),
        "views": {
            "definitions": {
                "label": "Definition tree",
                "roots": [module_id],
                "nodes": definition_nodes,
                "edges": definition_edges,
            },
            "calls": {
                "label": "Execution call tree",
                "roots": [module_id],
                "nodes": call_nodes,
                "edges": call_edges,
            },
            "parts": {
                "label": "Blender part tree",
                "roots": part_roots,
                "nodes": part_nodes,
                "edges": [asdict(edge) for edge in structure.part_edges],
            },
        },
    }


def _interactive_html(structure: SourceStructure) -> str:
    template_path = (
        Path(__file__).resolve().parent.parent
        / "frontend"
        / "interactive_tree_template.html"
    )
    if not template_path.is_file():
        raise SystemExit(f"Interactive HTML template is missing: {template_path}")
    template = template_path.read_text(encoding="utf-8")
    payload = json.dumps(_interactive_data(structure), ensure_ascii=False)
    return template.replace("__TREE_DATA_JSON__", payload)


def main() -> int:
    args = _arguments()
    source_path = args.source.expanduser().resolve()
    if not source_path.is_file():
        raise SystemExit(f"Source file does not exist: {source_path}")
    if source_path.suffix.lower() != ".py":
        raise SystemExit(f"Expected a .py file: {source_path}")

    source = source_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(source_path))
    except SyntaxError as error:
        raise SystemExit(f"Cannot parse {source_path}: {error}") from error

    structure = SourceStructure(source_path, source, tree)
    structure.analyze()

    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else source_path.parent / "structure_tree"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = source_path.stem + "_structure_tree"
    text_report = _text_report(structure, max(args.max_depth, 1))

    outputs = {
        "txt": output_dir / f"{stem}.txt",
        "json": output_dir / f"{stem}.json",
        "md": output_dir / f"{stem}.md",
        "dot": output_dir / f"{stem}.dot",
        "html": output_dir / f"{stem}.html",
    }
    outputs["txt"].write_text(text_report, encoding="utf-8")
    outputs["json"].write_text(
        json.dumps(_json_report(structure), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    outputs["md"].write_text(
        _markdown_report(structure, text_report), encoding="utf-8"
    )
    outputs["dot"].write_text(_dot_report(structure), encoding="utf-8")
    outputs["html"].write_text(_interactive_html(structure), encoding="utf-8")

    print(json.dumps({key: str(path) for key, path in outputs.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
