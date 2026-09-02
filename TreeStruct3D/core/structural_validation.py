"""Run validation_test's Blender probe and score structural attachments.

The probe remains the source of truth for runtime observations.  This module
only turns its detailed JSON into a deterministic Stage 7 gate and a compact
repair report; it does not infer shared anchors from visual proximity.
"""

from __future__ import annotations

import ast
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any


EXPLICIT_SHARED_EVIDENCE = {
    "authored_anchor_pair",
    "declared_world_anchor",
    "explicit_anchor_id",
}


def native_part_parameter_ids(script: Path) -> list[str]:
    """Return concrete ids from the literal Stage7 PART_PARAMS protocol."""

    try:
        tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name) and target.id == "PART_PARAMS"
            for target in targets
        ):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError, SyntaxError):
            return []
        if not isinstance(value, dict):
            return []
        return sorted(
            str(part_id)
            for part_id, params in value.items()
            if isinstance(params, dict)
            and isinstance(params.get("scale"), (int, float))
            and not isinstance(params.get("scale"), bool)
        )
    return []


def _geometry_change_evidence(
    before: dict[str, Any],
    after: dict[str, Any],
) -> tuple[bool, bool, bool]:
    """Detect rebuilt geometry without confusing a group AABB with its shape.

    Repeated primitives can grow around fixed instance centers while the union
    keeps the same outer bounds.  The probe already records deterministic mesh
    samples, so compare those samples relative to each object's center as well
    as its dimensions.  Centering prevents a pure attachment translation from
    being mistaken for use of the part's construction scale.
    """

    before_dims = [float(value) for value in before.get("dimensions") or []]
    after_dims = [float(value) for value in after.get("dimensions") or []]
    dimensions_changed = bool(
        len(before_dims) == len(after_dims) == 3
        and any(
            abs(current - original) > max(abs(original) * 0.05, 1e-5)
            for original, current in zip(before_dims, after_dims)
        )
    )

    before_samples = before.get("samples") or []
    after_samples = after.get("samples") or []
    before_center = [float(value) for value in before.get("center") or []]
    after_center = [float(value) for value in after.get("center") or []]
    samples_changed = False
    if (
        len(before_center) == len(after_center) == 3
        and before_samples
        and after_samples
    ):
        if len(before_samples) != len(after_samples):
            samples_changed = True
        else:
            reference_extent = max([abs(value) for value in before_dims] or [1.0])
            tolerance = max(reference_extent * 0.0025, 1e-5)
            for original, current in zip(before_samples, after_samples):
                if not (
                    isinstance(original, list)
                    and isinstance(current, list)
                    and len(original) == len(current) == 3
                ):
                    continue
                original_local = [
                    float(original[axis]) - before_center[axis] for axis in range(3)
                ]
                current_local = [
                    float(current[axis]) - after_center[axis] for axis in range(3)
                ]
                if any(
                    abs(current_local[axis] - original_local[axis]) > tolerance
                    for axis in range(3)
                ):
                    samples_changed = True
                    break

    vertex_count_changed = before.get("vertex_count") != after.get("vertex_count")
    return (
        bool(dimensions_changed or samples_changed or vertex_count_changed),
        dimensions_changed,
        samples_changed,
    )


def apply_parameter_invariance_gate(
    score: dict[str, Any],
    default_report: dict[str, Any],
    perturbation_reports: dict[str, dict[str, Any]],
    *,
    expected_part_ids: list[str] | None = None,
    expected_attachment_pairs: list[tuple[str, str]] | None = None,
    expected_attachment_requirements: dict[
        tuple[str, str], dict[str, bool]
    ]
    | None = None,
    expected_part_count: int | None = None,
    expected_attachment_count: int | None = None,
) -> dict[str, Any]:
    """Require every native part to survive its own scale-and-rebuild probe."""

    default_nodes = {
        str(node.get("id")): node
        for node in default_report.get("nodes") or []
        if isinstance(node, dict) and node.get("id") is not None
    }
    results = []
    extra_issues = []
    for part_id, report in sorted(perturbation_reports.items()):
        variant_score = score_structure_report(
            report,
            minimum_score=float(score.get("minimum_score", 85.0)),
            expected_part_ids=expected_part_ids,
            expected_attachment_pairs=expected_attachment_pairs,
            expected_attachment_requirements=expected_attachment_requirements,
            expected_part_count=expected_part_count,
            expected_attachment_count=expected_attachment_count,
        )
        variant_nodes = {
            str(node.get("id")): node
            for node in report.get("nodes") or []
            if isinstance(node, dict) and node.get("id") is not None
        }
        before = default_nodes.get(part_id)
        after = variant_nodes.get(part_id)
        geometry_changed = False
        dimensions_changed = False
        samples_changed = False
        if before is not None and after is not None:
            geometry_changed, dimensions_changed, samples_changed = (
                _geometry_change_evidence(before, after)
            )
        passed = bool(variant_score.get("passed") and geometry_changed)
        results.append({
            "part_id": part_id,
            "passed": passed,
            "structure_passed": bool(variant_score.get("passed")),
            "geometry_changed": geometry_changed,
            "dimensions_changed": dimensions_changed,
            "shape_samples_changed": samples_changed,
            "score": variant_score.get("score"),
            "issues": variant_score.get("issues") or [],
        })
        if before is None or after is None:
            extra_issues.append(
                _issue(
                    "NATIVE_PART_NODE_MISSING",
                    f"原生参数 {part_id} 没有对应同名运行时 Mesh 节点。",
                    part_id=part_id,
                )
            )
        elif not geometry_changed:
            extra_issues.append(
                _issue(
                    "NATIVE_PART_SCALE_UNUSED",
                    f"修改 {part_id}.scale 后该 Mesh 几何没有变化。",
                    part_id=part_id,
                )
            )
        elif not variant_score.get("passed"):
            extra_issues.append(
                _issue(
                    "PARAMETER_ANCHOR_INVARIANCE_FAILED",
                    f"单独修改 {part_id}.scale 后父子关系或共享锚点失效。",
                    part_id=part_id,
                    variant_issues=[
                        item.get("code") for item in variant_score.get("issues") or []
                    ],
                )
            )

    score = json.loads(json.dumps(score))
    score["parameter_invariance"] = {
        "mode": "native_rebuild",
        "tested_parts": len(results),
        "passed_parts": sum(bool(item["passed"]) for item in results),
        "results": results,
    }
    if extra_issues:
        score.setdefault("issues", []).extend(extra_issues)
        score["passed"] = False
    return score


def _edge_directions(edge: dict[str, Any], node_ids: set[str]) -> set[tuple[str, str]]:
    """Return every explicit or verified parent -> child direction on an edge."""

    directions: set[tuple[str, str]] = set()
    parent = edge.get("parent")
    child = edge.get("child")
    if (
        edge.get("relation") in {"DIRECTED", "DIRECTED_CODE"}
        and parent in node_ids
        and child in node_ids
        and parent != child
    ):
        directions.add((str(parent), str(child)))
    for declaration in edge.get("declared_directions") or []:
        parent = declaration.get("parent")
        child = declaration.get("child")
        if parent in node_ids and child in node_ids and parent != child:
            directions.add((str(parent), str(child)))
    return directions


def _cycles(pairs: set[tuple[str, str]]) -> list[list[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for parent, child in pairs:
        adjacency[parent].add(child)

    state: dict[str, int] = {}
    stack: list[str] = []
    found: list[list[str]] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for child in sorted(adjacency.get(node, ())):
            if state.get(child, 0) == 0:
                visit(child)
            elif state.get(child) == 1 and child in stack:
                start = stack.index(child)
                cycle = [*stack[start:], child]
                if cycle not in found:
                    found.append(cycle)
        stack.pop()
        state[node] = 2

    for node in sorted({item for pair in pairs for item in pair}):
        if state.get(node, 0) == 0:
            visit(node)
    return found


def _issue(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"severity": "error", "code": code, "message": message, **details}


def score_structure_report(
    report: dict[str, Any],
    *,
    minimum_score: float = 85.0,
    expected_part_ids: list[str] | None = None,
    expected_attachment_pairs: list[tuple[str, str]] | None = None,
    expected_attachment_requirements: dict[
        tuple[str, str], dict[str, bool]
    ]
    | None = None,
    expected_part_count: int | None = None,
    expected_attachment_count: int | None = None,
) -> dict[str, Any]:
    """Score one raw validation_test probe report on a 0--100 scale.

    A high numeric score alone is not sufficient.  Any missing authored shared
    anchor, broken declared attachment, multiple parent, multiple root, or
    cycle remains a hard failure so averages cannot hide a bad leaf part.
    """

    if report.get("status") != "ok":
        message = str(report.get("error") or "validation_test probe failed")
        return {
            "schema_version": "stage7-structural-score/v1",
            "passed": False,
            "score": 0.0,
            "minimum_score": float(minimum_score),
            "components": {"hierarchy": 0.0, "shared_anchors": 0.0},
            "summary": {
                "nodes": 0,
                "directed_relations": 0,
                "confirmed_shared_anchors": 0,
            },
            "issues": [_issue("PROBE_FAILED", message)],
        }

    all_nodes = list(report.get("nodes") or [])
    expected_id_set = (
        {str(part_id) for part_id in expected_part_ids}
        if expected_part_ids is not None
        else None
    )
    nodes = [
        node
        for node in all_nodes
        if expected_id_set is None
        or (isinstance(node, dict) and str(node.get("id")) in expected_id_set)
    ]
    node_ids = {
        str(node.get("id"))
        for node in nodes
        if isinstance(node, dict) and node.get("id") is not None
    }
    raw_edges = [
        edge
        for edge in report.get("edges") or []
        if isinstance(edge, dict)
        and (
            expected_id_set is None
            or (
                str(edge.get("node_a")) in node_ids
                and str(edge.get("node_b")) in node_ids
            )
        )
    ]
    expected_pair_set = (
        {(str(parent), str(child)) for parent, child in expected_attachment_pairs}
        if expected_attachment_pairs is not None
        else None
    )
    requirements_by_pair = {
        (str(parent), str(child)): {
            "contact_required": bool(requirements.get("contact_required")),
            "shared_anchor_required": bool(
                requirements.get("shared_anchor_required")
            ),
        }
        for (parent, child), requirements in (
            expected_attachment_requirements or {}
        ).items()
    }
    directed_pairs: set[tuple[str, str]] = set()
    unexpected_declared_pairs: set[tuple[str, str]] = set()
    shared_pairs: set[tuple[str, str]] = set()
    contact_pairs: set[tuple[str, str]] = set()
    aligned_pairs: set[tuple[str, str]] = set()
    pair_evidence: dict[tuple[str, str], dict[str, Any]] = {}
    broken_edges: list[dict[str, Any]] = []
    proximity_only = 0

    for edge in raw_edges:
        directions = _edge_directions(edge, node_ids)
        if expected_pair_set is None:
            structural_directions = directions
        else:
            structural_directions = directions & expected_pair_set
            for declaration in edge.get("declared_directions") or []:
                declared_pair = (
                    str(declaration.get("parent")),
                    str(declaration.get("child")),
                )
                if (
                    declared_pair[0] in node_ids
                    and declared_pair[1] in node_ids
                    and declared_pair not in expected_pair_set
                ):
                    unexpected_declared_pairs.add(declared_pair)
        directed_pairs.update(structural_directions)
        evidence = str(edge.get("shared_anchor_evidence") or "")
        explicit_shared = bool(
            edge.get("shared_anchor") and evidence in EXPLICIT_SHARED_EVIDENCE
        )
        for pair in structural_directions:
            pair_evidence[pair] = {
                "relation": edge.get("relation"),
                "contact": bool(edge.get("contact")),
                "geometric_anchor_aligned": bool(
                    edge.get("geometric_anchor_aligned")
                ),
                "shared_anchor_evidence": evidence or None,
                "anchor_gap": edge.get("anchor_gap"),
                "anchor_tolerance": edge.get("anchor_tolerance"),
            }
            if edge.get("contact"):
                contact_pairs.add(pair)
            if edge.get("geometric_anchor_aligned"):
                aligned_pairs.add(pair)
            if explicit_shared and edge.get("contact") and edge.get(
                "geometric_anchor_aligned"
            ):
                shared_pairs.add(pair)
        broken_contact_directions = {
            pair
            for pair in structural_directions
            if requirements_by_pair.get(pair, {"contact_required": True})[
                "contact_required"
            ]
        }
        if edge.get("relation") == "BROKEN_ATTACHMENT" and broken_contact_directions:
            broken_edges.append(edge)
        if edge.get("geometric_anchor_aligned") and not directions:
            proximity_only += 1

    parents_by_child: dict[str, set[str]] = defaultdict(set)
    for parent, child in directed_pairs:
        parents_by_child[child].add(parent)
    roots = sorted(node_ids - set(parents_by_child))
    multiple_parents = {
        child: sorted(parents)
        for child, parents in parents_by_child.items()
        if len(parents) > 1
    }
    cycles = _cycles(directed_pairs)

    single_part_blueprint = bool(
        expected_part_count == 1 and expected_attachment_count == 0
    )
    valid_single_part_observation = bool(
        single_part_blueprint and len(node_ids) == 1 and not directed_pairs
    )
    expected_children = max(len(node_ids) - 1, 0)
    covered_children = len(parents_by_child)
    hierarchy_coverage = (
        min(covered_children / expected_children, 1.0)
        if expected_children
        else (1.0 if valid_single_part_observation else 0.0)
    )
    direction_count = len(directed_pairs)
    no_attachment_coverage = 1.0 if valid_single_part_observation else 0.0
    if requirements_by_pair:
        shared_required_pairs = {
            pair
            for pair, requirements in requirements_by_pair.items()
            if requirements["shared_anchor_required"]
        }
        contact_required_pairs = {
            pair
            for pair, requirements in requirements_by_pair.items()
            if requirements["contact_required"]
        }
    else:
        shared_required_pairs = set(expected_pair_set or directed_pairs)
        contact_required_pairs = set(expected_pair_set or directed_pairs)
    alignment_required_pairs = set(shared_required_pairs)
    shared_coverage = (
        len(shared_pairs & shared_required_pairs) / len(shared_required_pairs)
        if shared_required_pairs
        else 1.0
    )
    contact_coverage = (
        len(contact_pairs & contact_required_pairs) / len(contact_required_pairs)
        if contact_required_pairs
        else 1.0
    )
    alignment_coverage = (
        len(aligned_pairs & alignment_required_pairs) / len(alignment_required_pairs)
        if alignment_required_pairs
        else 1.0
    )

    hierarchy_score = (
        25.0 * hierarchy_coverage
        + (5.0 if len(roots) == 1 else 0.0)
        + (5.0 if not multiple_parents else 0.0)
        + (5.0 if not cycles else 0.0)
    )
    anchor_score = (
        45.0 * shared_coverage
        + 7.5 * contact_coverage
        + 7.5 * alignment_coverage
    )
    total = round(hierarchy_score + anchor_score, 2)

    issues: list[dict[str, Any]] = []
    missing_expected_parts = sorted((expected_id_set or set()) - node_ids)
    if missing_expected_parts:
        issues.append(
            _issue(
                "EXPECTED_PARTS_MISSING",
                (
                    "结构蓝图中的语义零件没有生成同名运行时 Mesh："
                    + ", ".join(missing_expected_parts)
                ),
                missing=missing_expected_parts,
            )
        )
    missing_expected_attachments = sorted((expected_pair_set or set()) - directed_pairs)
    for parent, child in missing_expected_attachments:
        issues.append(
            _issue(
                "MISSING_EXPECTED_ATTACHMENT",
                f"结构蓝图要求 {parent} -> {child}，运行时没有确认该直接关系。",
                parent=parent,
                child=child,
            )
        )
    for parent, child in sorted(unexpected_declared_pairs):
        issues.append(
            _issue(
                "UNEXPECTED_DECLARED_ATTACHMENT",
                f"代码声明了蓝图之外的直接关系 {parent} -> {child}。",
                parent=parent,
                child=child,
            )
        )
    if len(node_ids) < 2 and not valid_single_part_observation:
        issues.append(
            _issue(
                "INSUFFICIENT_PARTS",
                "只观察到一个或零个语义零件，无法验证父子共享锚点。",
                nodes=len(node_ids),
            )
        )
    if len(node_ids) > 1 and not directed_pairs:
        issues.append(
            _issue(
                "NO_DIRECTED_RELATIONS",
                "存在多个零件，但没有确认任何父 → 子方向。",
            )
        )
    if len(node_ids) > 1 and len(roots) != 1:
        issues.append(
            _issue(
                "MULTIPLE_ROOTS",
                f"父子图应有一个根节点，当前检测到 {len(roots)} 个。",
                roots=roots,
            )
        )
    for child, parents in sorted(multiple_parents.items()):
        issues.append(
            _issue(
                "MULTIPLE_PRIMARY_PARENTS",
                f"子节点 {child} 同时具有多个主要父节点。",
                child=child,
                parents=parents,
            )
        )
    for cycle in cycles:
        issues.append(
            _issue(
                "PARENT_CHILD_CYCLE",
                "父子关系形成循环：" + " -> ".join(cycle),
                cycle=cycle,
            )
        )
    for edge in broken_edges:
        issues.append(
            _issue(
                "BROKEN_ATTACHMENT",
                "代码声明了连接，但运行后零件没有接触或锚点没有对齐。",
                node_a=edge.get("node_a"),
                node_b=edge.get("node_b"),
                anchor_gap=edge.get("anchor_gap"),
                anchor_tolerance=edge.get("anchor_tolerance"),
            )
        )
    for parent, child in sorted(
        (directed_pairs & shared_required_pairs) - shared_pairs
    ):
        evidence = pair_evidence.get((parent, child), {})
        issues.append(
            _issue(
                "UNVERIFIED_SHARED_ANCHOR",
                f"{parent} -> {child} 有父子方向，但没有通过显式共享锚点验证。",
                parent=parent,
                child=child,
                **evidence,
            )
        )
    for parent, child in sorted(
        (directed_pairs & contact_required_pairs) - contact_pairs
    ):
        if (parent, child) in shared_required_pairs:
            continue
        evidence = pair_evidence.get((parent, child), {})
        issues.append(
            _issue(
                "REQUIRED_CONTACT_MISSING",
                f"{parent} -> {child} 要求物理接触，但运行时没有确认接触。",
                parent=parent,
                child=child,
                **evidence,
            )
        )

    passed = bool(total >= minimum_score and not issues)
    return {
        "schema_version": "stage7-structural-score/v1",
        "passed": passed,
        "score": total,
        "minimum_score": float(minimum_score),
        "components": {
            "hierarchy": round(hierarchy_score, 2),
            "shared_anchors": round(anchor_score, 2),
        },
        "summary": {
            "nodes": len(node_ids),
            "expected_nodes": expected_part_count,
            "expected_attachments": expected_attachment_count,
            "expected_part_ids": sorted(expected_id_set or []),
            "expected_attachment_pairs": [
                {"parent": parent, "child": child}
                for parent, child in sorted(expected_pair_set or [])
            ],
            "shared_anchor_required_pairs": [
                {"parent": parent, "child": child}
                for parent, child in sorted(shared_required_pairs)
            ],
            "contact_required_pairs": [
                {"parent": parent, "child": child}
                for parent, child in sorted(contact_required_pairs)
            ],
            "roots": roots,
            "directed_relations": direction_count,
            "confirmed_shared_anchors": len(shared_pairs),
            "hierarchy_coverage": round(hierarchy_coverage, 4),
            "shared_anchor_coverage": round(shared_coverage, 4),
            "contact_coverage": round(contact_coverage, 4),
            "anchor_alignment_coverage": round(alignment_coverage, 4),
            "proximity_only_candidates": proximity_only,
            "broken_attachments": len(broken_edges),
        },
        "confirmed_relations": [
            {
                "parent": parent,
                "child": child,
                "shared_anchor": (parent, child) in shared_pairs,
                **pair_evidence.get((parent, child), {}),
            }
            for parent, child in sorted(directed_pairs)
        ],
        "issues": issues,
    }


def run_validation_probe(
    *,
    blender: Path,
    probe: Path,
    script: Path,
    output: Path,
    timeout: int,
    contact_ratio: float = 0.025,
    anchor_ratio: float = 0.025,
    samples: int = 96,
    part_param_scales: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Execute validation_test's strict runtime probe in Blender 5.0."""

    if not probe.is_file():
        return {
            "status": "error",
            "error": f"validation_test probe does not exist: {probe}",
        }
    if not blender.is_file():
        return {"status": "error", "error": f"Blender does not exist: {blender}"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    command = [
        str(blender),
        "--background",
        "--factory-startup",
        "--python",
        str(probe),
        "--",
        "--script",
        str(script),
        "--source-root",
        str(script.parent),
        "--output",
        str(output),
        "--contact-ratio",
        str(contact_ratio),
        "--anchor-ratio",
        str(anchor_ratio),
        "--max-nodes",
        "128",
        "--max-edges",
        "512",
        "--samples",
        str(samples),
    ]
    for part_id, factor in sorted((part_param_scales or {}).items()):
        command.extend(["--part-param-scale", f"{part_id}={factor}"])
    try:
        completed = subprocess.run(
            command,
            cwd=script.parent,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": f"validation_test probe exceeded {timeout}s",
        }
    if not output.is_file():
        tail = "\n".join(
            (completed.stdout + "\n" + completed.stderr).splitlines()[-30:]
        )
        return {
            "status": "error",
            "error": (
                "validation_test probe did not write a report "
                f"(Blender exit {completed.returncode})\n{tail}"
            ),
        }
    try:
        return json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "error",
            "error": f"invalid validation_test report: {type(exc).__name__}: {exc}",
        }


def score_markdown(score: dict[str, Any]) -> str:
    """Create a short human-readable companion to the machine JSON report."""

    summary = score.get("summary") or {}
    components = score.get("components") or {}
    parameter_invariance = score.get("parameter_invariance") or {}
    lines = [
        "# Stage 7 父子关系与共享锚点验证",
        "",
        f"- 结果：{'通过' if score.get('passed') else '失败'}",
        f"- 总分：{score.get('score', 0)} / 100",
        f"- 通过线：{score.get('minimum_score', 0)}",
        f"- 父子树：{components.get('hierarchy', 0)} / 40",
        f"- 共享锚点：{components.get('shared_anchors', 0)} / 60",
        f"- 语义零件：{summary.get('nodes', 0)}",
        f"- 父子边：{summary.get('directed_relations', 0)}",
        f"- 确认共享锚点：{summary.get('confirmed_shared_anchors', 0)}",
        (
            "- 参数扰动："
            f"{parameter_invariance.get('passed_parts', 0)} / "
            f"{parameter_invariance.get('tested_parts', 0)} 个部件通过"
        ),
        "",
        "## 发现的问题",
        "",
    ]
    issues = score.get("issues") or []
    if not issues:
        lines.append("- 无")
    else:
        for issue in issues:
            lines.append(f"- `{issue.get('code')}`：{issue.get('message')}")
    lines.extend(["", "## 已确认关系", ""])
    relations = score.get("confirmed_relations") or []
    if not relations:
        lines.append("- 无")
    else:
        for relation in relations:
            state = "共享锚点已确认" if relation.get("shared_anchor") else "共享锚点未确认"
            lines.append(
                f"- `{relation.get('parent')} -> {relation.get('child')}`：{state}"
            )
    return "\n".join(lines) + "\n"
