#!/usr/bin/env python3
"""Print deterministic geometry summaries for generated GLB regression checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys

import bpy


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def _summary(path: Path) -> dict[str, object]:
    _clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(path))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    digest = hashlib.sha256()
    lower = [float("inf")] * 3
    upper = [float("-inf")] * 3
    vertex_count = 0
    mesh_count = 0
    for obj in sorted(bpy.context.scene.objects, key=lambda item: item.name):
        if obj.type != "MESH":
            continue
        mesh_count += 1
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            digest.update(obj.name.encode("utf-8"))
            matrix = evaluated.matrix_world
            for vertex in mesh.vertices:
                point = matrix @ vertex.co
                coordinates = tuple(round(float(point[axis]), 6) for axis in range(3))
                digest.update(struct.pack("<3d", *coordinates))
                for axis, value in enumerate(coordinates):
                    lower[axis] = min(lower[axis], value)
                    upper[axis] = max(upper[axis], value)
                vertex_count += 1
        finally:
            evaluated.to_mesh_clear()
    return {
        "file": path.name,
        "meshes": mesh_count,
        "vertices": vertex_count,
        "bounds_min": lower,
        "bounds_max": upper,
        "geometry_sha256": digest.hexdigest(),
    }


def main() -> None:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not arguments:
        raise SystemExit("Pass one or more GLB paths after --")
    reports = [_summary(Path(argument).resolve()) for argument in arguments]
    print("GLB_GEOMETRY_AUDIT=" + json.dumps(reports, ensure_ascii=False))


if __name__ == "__main__":
    main()
