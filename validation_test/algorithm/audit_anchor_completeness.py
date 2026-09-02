#!/usr/bin/env python3
"""Batch-audit strict shared-anchor completeness for one generated dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from model_playground import (
    DEFAULT_CACHE,
    RUNTIME_GRAPH_VERSION,
    RUNTIME_GRAPH_PROBE,
    PlaygroundState,
    _model_catalog,
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--retry-errors", action="store_true")
    return parser.parse_args()


def state_arguments(args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        dataset=[args.dataset],
        dataset_label=[args.dataset.name],
        benchmark=Path("/nonexistent-benchmark"),
        blender=None,
        cache_dir=args.cache_dir,
        render_timeout=args.timeout,
    )


def edge_failure_reason(edge: dict[str, Any]) -> str:
    count = edge.get("authored_anchor_count")
    valid = edge.get("authored_anchor_valid_count")
    if isinstance(count, int) and count > 0 and valid != count:
        return f"authored_anchor_incomplete:{valid or 0}/{count}"
    if edge.get("parameter_invariance_failed"):
        return "parameter_invariance_failed"
    if not edge.get("contact"):
        return "no_contact"
    if not edge.get("geometric_anchor_aligned"):
        return "anchor_misaligned"
    if not edge.get("shared_anchor_evidence"):
        return "missing_explicit_shared_evidence"
    return "shared_anchor_unverified"


def classify_view(label: str, model_id: str, view: dict[str, Any]) -> dict[str, Any]:
    edges = list(view.get("edges") or [])
    directed = [
        edge
        for edge in edges
        if edge.get("parent_child_known")
        or edge.get("relation") in {"DIRECTED", "DIRECTED_CODE"}
    ]
    shared = [edge for edge in directed if edge.get("shared_anchor")]
    authored = [
        edge
        for edge in directed
        if isinstance(edge.get("authored_anchor_count"), int)
        and edge["authored_anchor_count"] > 0
    ]
    authored_total = sum(int(edge["authored_anchor_count"]) for edge in authored)
    authored_valid = sum(
        int(edge.get("authored_anchor_valid_count") or 0) for edge in authored
    )
    missing = [edge for edge in directed if not edge.get("shared_anchor")]
    failed_parts = [
        item
        for item in (view.get("parameter_invariance") or {}).get("results") or []
        if not item.get("passed") and int(item.get("affected_edges") or 0) > 0
    ]
    node_count = len(view.get("nodes") or [])

    if not directed:
        status = "single_part_no_anchor_needed" if node_count <= 1 else "unverifiable"
    elif missing:
        status = "incomplete"
    else:
        status = "complete"

    return {
        "model": label,
        "model_id": model_id,
        "status": status,
        "nodes": node_count,
        "directed_edges": len(directed),
        "shared_edges": len(shared),
        "missing_shared_edges": len(missing),
        "authored_anchors": authored_total,
        "valid_authored_anchors": authored_valid,
        "failed_invariance_parts": [str(item.get("part_id")) for item in failed_parts],
        "missing_edges": [
            {
                "parent": str(edge.get("parent")),
                "child": str(edge.get("child")),
                "reason": edge_failure_reason(edge),
                "authored_anchor_count": edge.get("authored_anchor_count"),
                "authored_anchor_valid_count": edge.get(
                    "authored_anchor_valid_count"
                ),
                "parent_anchor_vertex_gap": edge.get("parent_anchor_vertex_gap"),
                "child_anchor_vertex_gap": edge.get("child_anchor_vertex_gap"),
                "contact": edge.get("contact"),
                "parameter_invariance_failed": bool(
                    edge.get("parameter_invariance_failed")
                ),
            }
            for edge in missing
        ],
    }


def build_payload(
    dataset: Path,
    results: dict[str, dict[str, Any]],
    started_at: float,
    total_models: int,
) -> dict[str, Any]:
    records = [results[key] for key in sorted(results)]
    counts: dict[str, int] = {}
    for record in records:
        status = str(record["status"])
        counts[status] = counts.get(status, 0) + 1
    return {
        "version": 2,
        "runtime_graph_version": RUNTIME_GRAPH_VERSION,
        "validator_files": {
            str(RUNTIME_GRAPH_PROBE): hashlib.sha256(
                RUNTIME_GRAPH_PROBE.read_bytes()
            ).hexdigest(),
            str(Path(__file__).resolve()): hashlib.sha256(
                Path(__file__).resolve().read_bytes()
            ).hexdigest(),
        },
        "dataset": str(dataset),
        "started_at": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(started_at)
        ),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(time.time() - started_at, 3),
        "total_models": total_models,
        "completed_models": len(records),
        "status_counts": counts,
        "models": records,
    }


def write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{threading.get_ident()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def reason_label(reason: str) -> str:
    if reason.startswith("authored_anchor_incomplete:"):
        return "主体 Mesh 声明锚点不完整 " + reason.split(":", 1)[1]
    return {
        "parameter_invariance_failed": "部件缩放后共享锚点失效",
        "no_contact": "父子对象没有接触",
        "anchor_misaligned": "锚点未对齐",
        "missing_explicit_shared_evidence": "缺少显式共享锚点证据",
        "shared_anchor_unverified": "共享锚点未通过严格验证",
    }.get(reason, reason)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    incomplete = [
        record for record in payload["models"] if record["status"] == "incomplete"
    ]
    lines = [
        "# GPT-5.5 共享锚点完整性审计",
        "",
        f"- 数据集：`{payload['dataset']}`",
        f"- 验证器版本：`{payload['runtime_graph_version']}`",
        f"- 完成：{payload['completed_models']}/{payload['total_models']}",
        f"- 共享锚点齐全：{payload['status_counts'].get('complete', 0)}",
        f"- 共享锚点不齐：{payload['status_counts'].get('incomplete', 0)}",
        f"- 单体模型无需锚点：{payload['status_counts'].get('single_part_no_anchor_needed', 0)}",
        f"- 无法验证：{payload['status_counts'].get('unverifiable', 0)}",
        f"- 运行错误：{payload['status_counts'].get('runtime_error', 0)}",
        "",
        "判定规则：存在父子方向时，每条父子边都必须通过严格共享锚点验证；重复实例必须逐个完整，部件单独放大 1.35 倍后仍需保持。",
        "",
        "## 不完整模型总表",
        "",
        "| 模型 | 共享边/父子边 | 有效声明锚点/声明锚点 | 缺失边 |",
        "|---|---:|---:|---:|",
    ]
    for record in incomplete:
        lines.append(
            f"| {record['model']} | {record['shared_edges']}/{record['directed_edges']} "
            f"| {record['valid_authored_anchors']}/{record['authored_anchors']} "
            f"| {record['missing_shared_edges']} |"
        )
    lines.extend(["", "## 每个模型的失败父子边", ""])
    for record in incomplete:
        lines.append(
            f"### {record['model']} — {record['shared_edges']}/{record['directed_edges']}"
        )
        lines.append("")
        for edge in record["missing_edges"]:
            declared = edge.get("authored_anchor_count")
            valid = edge.get("authored_anchor_valid_count")
            anchor_count = (
                f"；声明锚点 {valid or 0}/{declared}"
                if isinstance(declared, int) and declared > 0
                else ""
            )
            lines.append(
                f"- `{edge['parent']} → {edge['child']}`："
                f"{reason_label(edge['reason'])}{anchor_count}"
            )
        if record.get("failed_invariance_parts"):
            lines.append(
                "- 缩放不变性失败部件："
                + "、".join(f"`{part}`" for part in record["failed_invariance_parts"])
            )
        lines.append("")
    lines.extend(
        [
            "## 解释限制",
            "",
            "这是基于 prompt 提取结构的代理评测，不是真实数据集 GT。历史 `structural_score_attempt*.json` 没有固定验证器版本，因此本报告只使用当前探针重跑结果。完整机器可读证据见同名 JSON。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = arguments()
    args.dataset = args.dataset.expanduser().resolve()
    args.cache_dir = args.cache_dir.expanduser().resolve()
    output = (
        args.output.expanduser().resolve()
        if args.output
        else args.dataset / "anchor_completeness_audit_v10.json"
    )
    models = _model_catalog(args.dataset, "dataset")
    if not models:
        raise SystemExit(f"No runnable models found in {args.dataset}")
    workers = max(1, min(int(args.workers), 8))
    started_at = time.time()
    completed: dict[str, dict[str, Any]] = {}
    if output.is_file():
        try:
            previous = json.loads(output.read_text(encoding="utf-8"))
            if previous.get("runtime_graph_version") == RUNTIME_GRAPH_VERSION:
                for record in previous.get("models") or []:
                    if record.get("status") != "runtime_error" or not args.retry_errors:
                        completed[str(record["model_id"])] = record
        except (OSError, ValueError, TypeError, KeyError):
            completed = {}

    local = threading.local()

    def scan(item):
        model_id, entry = item
        if not hasattr(local, "state"):
            local.state = PlaygroundState(state_arguments(args))
        try:
            view = local.state.runtime_graph(entry)
            return model_id, classify_view(entry.label, model_id, view)
        except Exception as exc:  # Keep the batch alive and report the case.
            return model_id, {
                "model": entry.label,
                "model_id": model_id,
                "status": "runtime_error",
                "error": f"{type(exc).__name__}: {exc}",
            }

    pending = [item for item in models.items() if item[0] not in completed]
    print(
        json.dumps(
            {
                "event": "start",
                "total": len(models),
                "cached": len(completed),
                "pending": len(pending),
                "workers": workers,
                "output": str(output),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(scan, item): item[0] for item in pending}
        for future in as_completed(futures):
            model_id, record = future.result()
            completed[model_id] = record
            payload = build_payload(args.dataset, completed, started_at, len(models))
            write_checkpoint(output, payload)
            print(
                json.dumps(
                    {
                        "event": "model",
                        "completed": len(completed),
                        "total": len(models),
                        "model": record["model"],
                        "status": record["status"],
                        "shared": record.get("shared_edges"),
                        "directed": record.get("directed_edges"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    payload = build_payload(args.dataset, completed, started_at, len(models))
    write_checkpoint(output, payload)
    write_markdown(output.with_suffix(".md"), payload)
    print(json.dumps({"event": "done", **payload["status_counts"]}), flush=True)


if __name__ == "__main__":
    main()
