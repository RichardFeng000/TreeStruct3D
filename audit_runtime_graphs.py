#!/usr/bin/env python3
"""Run and summarize the Blender runtime anchor graph for every model seed."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import model_playground


APP_DIR = Path(__file__).resolve().parent


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="benchmark")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--only",
        default="",
        help="comma-separated seed labels to audit",
    )
    parser.add_argument(
        "--report-name",
        default="",
        help="output basename; defaults to runtime_anchor_<source>",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=APP_DIR / "audit_reports",
    )
    return parser.parse_args()


def playground_state(timeout: int) -> model_playground.PlaygroundState:
    args = argparse.Namespace(
        benchmark=model_playground.DEFAULT_BENCHMARK,
        blender=model_playground.DEFAULT_BLENDER,
        cache_dir=model_playground.DEFAULT_CACHE,
        render_timeout=timeout,
    )
    return model_playground.PlaygroundState(args)


def error_kind(exc: BaseException) -> str:
    message = str(exc).lower()
    if isinstance(exc, subprocess.TimeoutExpired):
        return "timeout"
    if "no observable geometry" in message or "没有可观察" in message:
        return "no_observable_geometry"
    if "syntaxerror" in message or "syntax error" in message:
        return "syntax_error"
    if "traceback" in message or "blender" in message:
        return "runtime_error"
    return "analysis_error"


def result_for_view(label: str, model_id: str, view: dict[str, Any], seconds: float) -> dict[str, Any]:
    summary = view.get("summary") or {}
    edges = list(view.get("edges") or [])
    relation_counts: dict[str, int] = {}
    broken_attachments = 0
    misaligned = 0
    unverified = 0
    for edge in edges:
        relation = str(edge.get("relation") or "UNKNOWN")
        relation_counts[relation] = relation_counts.get(relation, 0) + 1
        if relation == "BROKEN_ATTACHMENT":
            broken_attachments += 1
        if edge.get("geometric_anchor_aligned") is False:
            misaligned += 1
        if relation in {"GEOMETRIC_ANCHOR_CANDIDATE", "UNVERIFIED_ANCHOR"}:
            unverified += 1
    nodes = len(view.get("nodes") or [])
    edge_count = len(edges)
    return {
        "label": label,
        "model_id": model_id,
        "status": "ok",
        "seconds": round(seconds, 3),
        "nodes": nodes,
        "edges": edge_count,
        "directed_edges": int(summary.get("directed_edges") or 0),
        "runtime_directed_edges": int(summary.get("runtime_directed_edges") or 0),
        "shared_anchor_edges": int(summary.get("shared_anchor_edges") or 0),
        "estimated_anchor_edges": int(summary.get("estimated_anchor_edges") or 0),
        "unverified_anchor_edges": unverified,
        "broken_attachment_edges": broken_attachments,
        "misaligned_anchor_edges": max(
            misaligned,
            int(summary.get("misaligned_anchor_edges") or 0),
        ),
        "relations": relation_counts,
        "problem": "single_final_mesh_no_runtime_relations" if nodes == 1 and edge_count == 0 else None,
    }


def write_reports(
    output_dir: Path,
    source: str,
    report_name: str,
    records: list[dict[str, Any]],
    total: int,
    started_at: float,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    basename = report_name or f"runtime_anchor_{source}"
    json_path = output_dir / f"{basename}.json"
    markdown_path = output_dir / f"{basename}.md"

    completed = len(records)
    ok = sum(record["status"] == "ok" for record in records)
    errors = completed - ok
    zero_relations = sum(
        record.get("problem") == "single_final_mesh_no_runtime_relations"
        for record in records
    )
    with_shared = sum(int(record.get("shared_anchor_edges") or 0) > 0 for record in records)
    broken = sum(int(record.get("broken_attachment_edges") or 0) > 0 for record in records)
    misaligned = sum(int(record.get("misaligned_anchor_edges") or 0) > 0 for record in records)
    payload = {
        "source": source,
        "blender": str(model_playground.DEFAULT_BLENDER),
        "blender_version": model_playground.PINNED_BLENDER_VERSION,
        "probe": str(model_playground.RUNTIME_GRAPH_PROBE),
        "total": total,
        "completed": completed,
        "elapsed_seconds": round(time.time() - started_at, 3),
        "summary": {
            "ok": ok,
            "errors": errors,
            "single_final_mesh_no_runtime_relations": zero_relations,
            "models_with_shared_anchors": with_shared,
            "models_with_broken_attachments": broken,
            "models_with_misaligned_anchor_candidates": misaligned,
        },
        "records": records,
    }
    temporary = json_path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(json_path)

    lines = [
        f"# Runtime Anchor Audit — {source}",
        "",
        f"- Blender: {model_playground.PINNED_BLENDER_VERSION}",
        f"- Progress: {completed}/{total}",
        f"- Success: {ok}",
        f"- Errors: {errors}",
        f"- Single final Mesh with no runtime relations: {zero_relations}",
        f"- Models with confirmed shared anchors: {with_shared}",
        f"- Models with broken attachments: {broken}",
        f"- Models with misaligned anchor candidates: {misaligned}",
        "",
        "| Seed | Status | Nodes | Edges | Directed | Shared | Broken attachment | Misaligned | Seconds | Problem |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for record in records:
        problem = record.get("problem") or record.get("error_kind") or ""
        lines.append(
            "| {label} | {status} | {nodes} | {edges} | {directed} | {shared} | {broken} | {misaligned} | {seconds:.3f} | {problem} |".format(
                label=str(record["label"]).replace("|", "\\|"),
                status=record["status"],
                nodes=record.get("nodes", "-"),
                edges=record.get("edges", "-"),
                directed=record.get("directed_edges", "-"),
                shared=record.get("shared_anchor_edges", "-"),
                broken=record.get("broken_attachment_edges", "-"),
                misaligned=record.get("misaligned_anchor_edges", "-"),
                seconds=float(record.get("seconds") or 0),
                problem=str(problem).replace("|", "\\|"),
            )
        )
        if record["status"] != "ok":
            error = " ".join(str(record.get("error") or "").split())
            lines.append(f"  - `{record['label']}`: {error}")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path


def main() -> None:
    args = arguments()
    state = playground_state(args.timeout)
    models = state.models_by_source.get(args.source)
    if not models:
        raise SystemExit(f"Unknown or empty source: {args.source}")

    entries = sorted(models.values(), key=lambda entry: entry.label.lower())
    requested = {label.strip() for label in args.only.split(",") if label.strip()}
    if requested:
        entries = [entry for entry in entries if entry.label in requested]
        found = {entry.label for entry in entries}
        missing = sorted(requested - found)
        if missing:
            raise SystemExit("Unknown seed labels: " + ", ".join(missing))
    records: list[dict[str, Any]] = []
    started_at = time.time()
    total = len(entries)
    for index, entry in enumerate(entries, 1):
        item_started = time.time()
        try:
            view = state.runtime_graph(entry)
            record = result_for_view(
                entry.label,
                entry.model_id,
                view,
                time.time() - item_started,
            )
            short = (
                f"ok nodes={record['nodes']} edges={record['edges']} "
                f"shared={record['shared_anchor_edges']} "
                f"broken={record['broken_attachment_edges']} "
                f"misaligned={record['misaligned_anchor_edges']}"
            )
        except Exception as exc:  # Continue auditing the remaining seeds.
            record = {
                "label": entry.label,
                "model_id": entry.model_id,
                "status": "error",
                "seconds": round(time.time() - item_started, 3),
                "error_kind": error_kind(exc),
                "error": str(exc),
            }
            short = f"ERROR {record['error_kind']}"
        records.append(record)
        write_reports(
            args.output_dir,
            args.source,
            args.report_name,
            records,
            total,
            started_at,
        )
        print(f"[{index:03d}/{total:03d}] {entry.label}: {short}", flush=True)

    json_path, markdown_path = write_reports(
        args.output_dir,
        args.source,
        args.report_name,
        records,
        total,
        started_at,
    )
    print(f"JSON: {json_path}", flush=True)
    print(f"Markdown: {markdown_path}", flush=True)


if __name__ == "__main__":
    main()
