#!/usr/bin/env python3
"""Verify that Bird edits run the original source construction and anchors."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


APP_DIR = Path(__file__).resolve().parent
SOURCE = APP_DIR / "benchmark" / "categories" / "Bird_seed0" / "Bird_seed0.py"
WORKER = APP_DIR / "blender_live_export.py"
EXPECTED_CREATORS = {
    "body": 1,
    "head": 1,
    "beak": 1,
    "eye": 2,
    "wing": 2,
    "tail": 1,
    "leg": 2,
    "foot": 2,
}


def _load_worker():
    spec = importlib.util.spec_from_file_location("bird_live_export", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {WORKER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _audit(worker, request_path: Path) -> dict[str, object]:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    params = request.get("params", {})
    namespace, _result, _parts = worker._execute_source(SOURCE, params, "bird")
    trace = namespace.get("__codex_bird_source_trace__", {})
    foot_gaps = [float(item["gap"]) for item in trace.get("foot_anchors", [])]
    attach_calls = trace.get("attach_calls", [])
    head_link = next(
        (
            item
            for item in attach_calls
            if item.get("parent") == "body" and item.get("child") == "head"
        ),
        None,
    )
    checks = {
        "original_main_completed": trace.get("main_completed") is True,
        "all_creators_executed_once": trace.get("creator_calls") == EXPECTED_CREATORS,
        "original_attach_calls": len(attach_calls) == 9,
        "body_head_source_anchor": head_link is not None,
        "foot_source_anchors": len(foot_gaps) == 2
        and max(foot_gaps, default=float("inf")) <= 1e-6,
    }
    return {
        "request": request_path.name,
        "ok": all(checks.values()),
        "checks": checks,
        "body_scale": float(params.get("part_scale_body", 1.0)),
        "body_head_source_anchor": head_link.get("source_anchor") if head_link else None,
        "foot_anchor_max_gap": max(foot_gaps, default=None),
    }


def main() -> None:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not arguments:
        raise SystemExit("Pass one or more render request JSON files after --")
    worker = _load_worker()
    reports = [_audit(worker, Path(argument).resolve()) for argument in arguments]
    baseline = next(
        (report for report in reports if abs(report["body_scale"] - 1.0) < 1e-8),
        None,
    )
    if baseline and baseline["body_head_source_anchor"]:
        base_anchor = baseline["body_head_source_anchor"]
        for report in reports:
            anchor = report["body_head_source_anchor"]
            factor = report["body_scale"]
            recomputed = bool(anchor) and max(
                abs(anchor[axis] - base_anchor[axis] * factor)
                for axis in range(3)
            ) <= 1e-5
            report["checks"]["body_anchor_recomputed"] = recomputed
            report["ok"] = bool(report["ok"] and recomputed)
    print("BIRD_SOURCE_AUDIT=" + json.dumps(reports, ensure_ascii=False))
    if not all(report["ok"] for report in reports):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
