"""Parse, validate, and render model-extracted structure blueprints."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any


SCHEMA_VERSION = "treestruct3d.structure-blueprint/v2"
LEGACY_SCHEMA_VERSIONS = frozenset({"stage7-structure-blueprint/v2"})
SUPPORTED_SCHEMA_VERSIONS = frozenset({SCHEMA_VERSION, *LEGACY_SCHEMA_VERSIONS})
PART_ROLES = {"root", "structural", "attached", "detail"}
IMPORTANCE_LEVELS = {"primary", "secondary", "detail"}
CONNECTION_TYPES = {
    "shared_anchor",
    "continuous_surface",
    "embedded",
    "surface_contact",
}
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract exactly one JSON object from a model response."""

    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    decoder = json.JSONDecoder()
    failures: list[str] = []
    for index, character in enumerate(candidate):
        if character != "{":
            continue
        try:
            value, end = decoder.raw_decode(candidate[index:])
        except json.JSONDecodeError as exc:
            failures.append(str(exc))
            continue
        trailing = candidate[index + end :].strip()
        if not isinstance(value, dict):
            failures.append("top-level JSON value is not an object")
            continue
        if trailing:
            failures.append("response contains text after the JSON object")
            continue
        return value
    detail = failures[-1] if failures else "no JSON object found"
    raise ValueError(f"Could not parse structure blueprint: {detail}")


def _required_string(
    value: Any,
    path: str,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> str | None:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        errors.append(f"{path} must be a non-empty string")
        return None
    return value


def validate_blueprint(blueprint: dict[str, Any]) -> list[str]:
    """Return deterministic schema and graph errors for one blueprint."""

    errors: list[str] = []
    if blueprint.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"schema_version must equal {SCHEMA_VERSION}")
    _required_string(blueprint.get("object_name"), "object_name", errors)
    if blueprint.get("assembly_intent") != "single_connected_assembly":
        errors.append("assembly_intent must equal single_connected_assembly")

    frame = blueprint.get("coordinate_frame")
    if not isinstance(frame, dict):
        errors.append("coordinate_frame must be an object")
    else:
        for field in ("up_axis", "front_axis", "origin_rule"):
            _required_string(frame.get(field), f"coordinate_frame.{field}", errors)

    root = _required_string(blueprint.get("root_part_id"), "root_part_id", errors)
    parts = blueprint.get("parts")
    if not isinstance(parts, list) or not parts:
        errors.append("parts must be a non-empty array")
        parts = []
    part_by_id: dict[str, dict[str, Any]] = {}
    for index, part in enumerate(parts):
        path = f"parts[{index}]"
        if not isinstance(part, dict):
            errors.append(f"{path} must be an object")
            continue
        part_id = _required_string(part.get("id"), f"{path}.id", errors)
        if part_id:
            if not ID_PATTERN.fullmatch(part_id):
                errors.append(f"{path}.id must be stable snake_case")
            if part_id in part_by_id:
                errors.append(f"duplicate part id: {part_id}")
            part_by_id[part_id] = part
        _required_string(part.get("name"), f"{path}.name", errors)
        if part.get("role") not in PART_ROLES:
            errors.append(f"{path}.role must be one of {sorted(PART_ROLES)}")
        if part.get("importance") not in IMPORTANCE_LEVELS:
            errors.append(
                f"{path}.importance must be one of {sorted(IMPORTANCE_LEVELS)}"
            )
        quantity = part.get("quantity")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            errors.append(f"{path}.quantity must be an integer >= 1")
        _required_string(part.get("geometry_summary"), f"{path}.geometry_summary", errors)

    if root and root not in part_by_id:
        errors.append("root_part_id must reference an existing part")
    if root in part_by_id:
        if part_by_id[root].get("parent_id") is not None:
            errors.append("the root part parent_id must be null")
        if part_by_id[root].get("role") != "root":
            errors.append("the root part role must be root")

    for part_id, part in part_by_id.items():
        if part_id == root:
            continue
        parent = part.get("parent_id")
        if not isinstance(parent, str) or not parent:
            errors.append(f"non-root part {part_id} must have one parent_id")
        elif parent not in part_by_id:
            errors.append(f"part {part_id} references missing parent {parent}")
        elif parent == part_id:
            errors.append(f"part {part_id} cannot parent itself")
        if part.get("role") == "root":
            errors.append(f"non-root part {part_id} cannot have role root")

    attachments = blueprint.get("attachments")
    if not isinstance(attachments, list):
        errors.append("attachments must be an array")
        attachments = []
    attachment_ids: set[str] = set()
    shared_anchor_ids: set[str] = set()
    attachments_by_child: Counter[str] = Counter()
    attachment_parent_by_child: dict[str, str] = {}
    for index, attachment in enumerate(attachments):
        path = f"attachments[{index}]"
        if not isinstance(attachment, dict):
            errors.append(f"{path} must be an object")
            continue
        attachment_id = _required_string(attachment.get("id"), f"{path}.id", errors)
        if attachment_id:
            if not ID_PATTERN.fullmatch(attachment_id):
                errors.append(f"{path}.id must be stable snake_case")
            if attachment_id in attachment_ids:
                errors.append(f"duplicate attachment id: {attachment_id}")
            attachment_ids.add(attachment_id)
        parent = attachment.get("parent_part_id")
        child = attachment.get("child_part_id")
        if parent not in part_by_id:
            errors.append(f"{path}.parent_part_id must reference an existing part")
        if child not in part_by_id:
            errors.append(f"{path}.child_part_id must reference an existing part")
        if parent == child and parent is not None:
            errors.append(f"{path} cannot connect a part to itself")
        if isinstance(child, str):
            attachments_by_child[child] += 1
            if isinstance(parent, str):
                attachment_parent_by_child[child] = parent
        if attachment.get("connection_type") not in CONNECTION_TYPES:
            errors.append(
                f"{path}.connection_type must be one of {sorted(CONNECTION_TYPES)}"
            )
        for anchor_name in ("parent_anchor", "child_anchor"):
            anchor = attachment.get(anchor_name)
            if not isinstance(anchor, dict):
                errors.append(f"{path}.{anchor_name} must be an object")
                continue
            for field in ("region", "position_rule", "orientation_rule"):
                _required_string(
                    anchor.get(field),
                    f"{path}.{anchor_name}.{field}",
                    errors,
                )
        _required_string(attachment.get("placement_rule"), f"{path}.placement_rule", errors)
        if not isinstance(attachment.get("contact_required"), bool):
            errors.append(f"{path}.contact_required must be boolean")
        shared_anchor_required = attachment.get("shared_anchor_required")
        if not isinstance(shared_anchor_required, bool):
            errors.append(f"{path}.shared_anchor_required must be boolean")
        contact_required = attachment.get("contact_required")
        if contact_required is True and shared_anchor_required is not True:
            errors.append(
                f"{path} contact_required=true must also require a shared anchor"
            )
        if shared_anchor_required is True:
            shared_anchor_id = _required_string(
                attachment.get("shared_anchor_id"),
                f"{path}.shared_anchor_id",
                errors,
            )
            if shared_anchor_id:
                if not ID_PATTERN.fullmatch(shared_anchor_id):
                    errors.append(f"{path}.shared_anchor_id must be stable snake_case")
                if shared_anchor_id in shared_anchor_ids:
                    errors.append(f"duplicate shared_anchor_id: {shared_anchor_id}")
                shared_anchor_ids.add(shared_anchor_id)
            invariant = _required_string(
                attachment.get("alignment_invariant"),
                f"{path}.alignment_invariant",
                errors,
            )
            if invariant and "world(parent_anchor) == world(child_anchor)" not in invariant:
                errors.append(
                    f"{path}.alignment_invariant must require "
                    "world(parent_anchor) == world(child_anchor)"
                )
            _required_string(
                attachment.get("recompute_rule"),
                f"{path}.recompute_rule",
                errors,
            )
        confidence = attachment.get("confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= float(confidence) <= 1.0
        ):
            errors.append(f"{path}.confidence must be between 0 and 1")

    for part_id, part in part_by_id.items():
        if part_id == root:
            if attachments_by_child[part_id]:
                errors.append("root part cannot be the child of a primary attachment")
            continue
        count = attachments_by_child[part_id]
        if count != 1:
            errors.append(
                f"non-root part {part_id} must have exactly one attachment; found {count}"
            )
        expected_parent = part.get("parent_id")
        actual_parent = attachment_parent_by_child.get(part_id)
        if count == 1 and actual_parent != expected_parent:
            errors.append(
                f"part {part_id} parent_id {expected_parent!r} does not match "
                f"attachment parent {actual_parent!r}"
            )

    # Verify that every parent chain reaches the one declared root without a cycle.
    for part_id in sorted(part_by_id):
        seen: list[str] = []
        current: str | None = part_id
        while current is not None and current != root:
            if current in seen:
                cycle = " -> ".join([*seen[seen.index(current) :], current])
                errors.append(f"parent cycle detected: {cycle}")
                break
            seen.append(current)
            part = part_by_id.get(current)
            if part is None:
                break
            parent = part.get("parent_id")
            current = parent if isinstance(parent, str) else None
        if current is None and part_id != root:
            errors.append(f"part {part_id} does not reach root {root!r}")

    conversion = blueprint.get("objective_conversion")
    if (
        isinstance(conversion, dict)
        and conversion.get("source_primary_class") == "object_join_core"
    ):
        for index, attachment in enumerate(attachments):
            if not isinstance(attachment, dict):
                continue
            path = f"attachments[{index}]"
            if attachment.get("shared_anchor_required") is not True:
                continue
            evidence = attachment.get("objective_evidence")
            if not isinstance(evidence, dict):
                errors.append(f"{path}.objective_evidence must prove the shared anchor")
                continue
            if evidence.get("verified_shared_anchor") is not True:
                errors.append(f"{path} must have verified_shared_anchor=true")
            for endpoint_name in ("parent_endpoint", "child_endpoint"):
                endpoint = evidence.get(endpoint_name)
                normalized = (
                    endpoint.get("bbox_normalized_position")
                    if isinstance(endpoint, dict)
                    else None
                )
                if not (
                    isinstance(normalized, list)
                    and len(normalized) == 3
                    and all(
                        isinstance(value, (int, float)) and not isinstance(value, bool)
                        for value in normalized
                    )
                ):
                    errors.append(
                        f"{path}.{endpoint_name} must have a 3D "
                        "bbox_normalized_position"
                    )
            child_id = str(attachment.get("child_part_id") or "")
            quantity = max(1, int((part_by_id.get(child_id) or {}).get("quantity") or 1))
            if quantity <= 1:
                continue
            coverage = evidence.get("instance_coverage") or {}
            if not (
                coverage.get("complete") is True
                and coverage.get("expected_child_instances") == quantity
                and coverage.get("resolved_child_instances") == quantity
            ):
                errors.append(
                    f"{path} shared anchor must cover all {quantity} child instances"
                )
            relations = evidence.get("instance_relations") or []
            resolved_ids = {
                str(relation.get("child_instance_id"))
                for relation in relations
                if isinstance(relation, dict) and relation.get("child_instance_id")
            }
            if len(resolved_ids) != quantity:
                errors.append(
                    f"{path} must have {quantity} unique child instance anchors; "
                    f"found {len(resolved_ids)}"
                )
            if any(
                not isinstance(relation, dict)
                or not isinstance(relation.get("parent_endpoint"), dict)
                or not isinstance(relation.get("child_endpoint"), dict)
                for relation in relations
            ):
                errors.append(
                    f"{path} every instance relation must have a two-sided anchor"
                )

    for field in (
        "symmetry_and_repetition",
        "global_constraints",
        "floating_part_risks",
        "uncertainties",
    ):
        if not isinstance(blueprint.get(field), list):
            errors.append(f"{field} must be an array")
    for index, risk in enumerate(blueprint.get("floating_part_risks") or []):
        if not isinstance(risk, dict):
            errors.append(f"floating_part_risks[{index}] must be an object")
            continue
        ids = risk.get("part_ids")
        if not isinstance(ids, list) or not ids:
            errors.append(f"floating_part_risks[{index}].part_ids must be non-empty")
        else:
            missing = [part_id for part_id in ids if part_id not in part_by_id]
            if missing:
                errors.append(
                    f"floating_part_risks[{index}] references missing parts: {missing}"
                )
        _required_string(risk.get("risk"), f"floating_part_risks[{index}].risk", errors)
        _required_string(
            risk.get("required_fix"),
            f"floating_part_risks[{index}].required_fix",
            errors,
        )

    # Preserve order while removing duplicate graph errors.
    return list(dict.fromkeys(errors))


def blueprint_markdown(blueprint: dict[str, Any]) -> str:
    """Render a compact readable view for manual extraction review."""

    parts = {
        str(part.get("id")): part
        for part in blueprint.get("parts") or []
        if isinstance(part, dict)
    }
    root = blueprint.get("root_part_id")
    lines = [
        f"# {blueprint.get('object_name', 'Structure')} 结构蓝图",
        "",
        f"- Schema：`{blueprint.get('schema_version')}`",
        f"- 根节点：`{root}`",
        f"- 零件模板：{len(parts)}",
        f"- 主要连接：{len(blueprint.get('attachments') or [])}",
        "",
        "## 父子结构",
        "",
    ]
    for part_id, part in parts.items():
        if part_id == root:
            lines.append(
                f"- `{part_id}`（根，数量 {part.get('quantity', 1)}）："
                f"{part.get('geometry_summary', '')}"
            )
        else:
            lines.append(
                f"- `{part.get('parent_id')}` → `{part_id}`（数量 "
                f"{part.get('quantity', 1)}）：{part.get('geometry_summary', '')}"
            )
    lines.extend(["", "## 锚点连接", ""])
    for attachment in blueprint.get("attachments") or []:
        lines.append(
            f"- `{attachment.get('parent_part_id')}` → "
            f"`{attachment.get('child_part_id')}`："
            f"{attachment.get('parent_anchor', {}).get('region')} ↔ "
            f"{attachment.get('child_anchor', {}).get('region')}；"
            f"{attachment.get('placement_rule')}；共享 ID："
            f"`{attachment.get('shared_anchor_id')}`；约束："
            f"{attachment.get('alignment_invariant')}；重算："
            f"{attachment.get('recompute_rule')}"
        )
    lines.extend(["", "## 悬浮风险", ""])
    risks = blueprint.get("floating_part_risks") or []
    if not risks:
        lines.append("- 无特别风险")
    else:
        for risk in risks:
            ids = ", ".join(f"`{item}`" for item in risk.get("part_ids") or [])
            lines.append(
                f"- {ids}：{risk.get('risk')}；处理：{risk.get('required_fix')}"
            )
    uncertainties = blueprint.get("uncertainties") or []
    lines.extend(["", "## 未确定信息", ""])
    if not uncertainties:
        lines.append("- 无")
    else:
        lines.extend(f"- {item}" for item in uncertainties)
    return "\n".join(lines) + "\n"
