import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_maple_leaf():
    # 1. Define the rough outline of a maple leaf (Palmate shape)
    # Coordinates as (x, y). Maple leaves usually have 5 main lobes.
    outline_points = [
        (0.0, 0.0),             # Base
        (-0.2, 0.1),            # Gap 1
        (-1.4, 0.3),            # Tip 1 (Lower Left)
        (-0.5, 0.4),            # Gap 2
        (-1.6, 1.2),            # Tip 2 (Upper Left)
        (-0.4, 0.8),            # Gap 3
        (0.0, 2.0),             # Tip 3 (Center Top)
        (0.4, 0.8),             # Gap 4
        (1.6, 1.2),             # Tip 4 (Upper Right)
        (0.5, 0.4),             # Gap 5
        (1.4, 0.3),             # Tip 6 (Lower Right)
        (0.2, 0.1),             # Gap 7
        (0.0, 0.0),             # Close loop at base
    ]

    pts_3d = [Vector((p[0], p[1], 0.0)) for p in outline_points]

    res = 20 
    smooth_outline = []
    for i in range(len(pts_3d) - 1):
        p1 = pts_3d[i]
        p2 = pts_3d[i+1]
        for j in range(res):
            t = j / res
            smooth_outline.append(p1.lerp(p2, t))

    mesh = bpy.data.meshes.new("MapleLeaf")
    obj = bpy.data.objects.new("MapleLeaf", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    final_outline = []
    for i in range(len(smooth_outline)):
        p = smooth_outline[i]
        prev_p = smooth_outline[i-1] if i > 0 else smooth_outline[-1]
        next_p = smooth_outline[(i+1)%len(smooth_outline)]
        edge_dir = (next_p - prev_p).normalized()
        normal = Vector((-edge_dir.y, edge_dir.x, 0))
        
        if p.length > 0.3:
            # Serration amplitude varies slightly for organic look
            serration_amp = 0.04 * (1.0 + math.sin(i * 0.5) * 0.2)
            offset = normal * (math.sin(i * 2.5) * serration_amp)
            final_outline.append(p + offset)
        else:
            final_outline.append(p)

    perimeter_verts = [bm.verts.new(v) for v in final_outline]
    center_vert = bm.verts.new(Vector((0, 0, 0)))
    for i in range(len(perimeter_verts)):
        v1 = perimeter_verts[i]
        v2 = perimeter_verts[(i+1)%len(perimeter_verts)]
        try:
            bm.faces.new((center_vert, v1, v2))
        except ValueError:
            pass

    # High subdivision for displacement
    for _ in range(4): 
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1)

    bm.verts.ensure_lookup_table()
    
    lobe_tips = [
        Vector((-1.4, 0.3, 0)), 
        Vector((-1.6, 1.2, 0)), 
        Vector((0.0, 2.0, 0)), 
        Vector((1.6, 1.2, 0)), 
        Vector((1.4, 0.3, 0))
    ]

    for v in bm.verts:
        pos = v.co.copy()
        x, y, z = pos.x, pos.y, pos.z
        dist_sq = x*x + y*y
        
        # Base organic curvature
        z_base = 0.2 * math.exp(-dist_sq / 3.0)
        wave = 0.05 * math.sin(x * 4.0) * math.cos(y * 4.0)
        fold = -0.1 * (dist_sq * 0.1) # Curl edges down slightly
        
        vein_contribution = 0.0
        for tip in lobe_tips:
            line_vec = tip
            l2 = line_vec.length**2
            if l2 == 0: continue
            proj_t = (pos.dot(line_vec)) / l2
            proj_t = max(0, min(1, proj_t))
            closest_point = line_vec * proj_t
            dist_to_vein = (pos - closest_point).length
            if dist_to_vein < 0.1:
                vein_contribution += max(0, (0.1 - dist_to_vein) * 0.8)
        
        v.co.z = z_base + wave + fold + vein_contribution

    # Stem construction
    stem_segments = 20
    stem_rings = 12
    radius = 0.04
    length = 1.8
    
    stem_verts = []
    for i in range(stem_segments + 1):
        t = i / stem_segments
        z = - t * length
        x_offset = 0.2 * math.sin(t * math.pi * 0.5)
        y_offset = -0.1 * t
        
        ring = []
        for j in range(stem_rings):
            angle = (j / stem_rings) * 2 * math.pi
            vx = x_offset + radius * math.cos(angle)
            vy = y_offset + radius * math.sin(angle)
            ring.append(bm.verts.new(Vector((vx, vy, z))))
        stem_verts.append(ring)

    for i in range(stem_segments):
        for j in range(stem_rings):
            v1 = stem_verts[i][j]
            v2 = stem_verts[i][(j+1)%stem_rings]
            v3 = stem_verts[i+1][(j+1)%stem_rings]
            v4 = stem_verts[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    bottom_ring = stem_verts[-1]
    bm.faces.new(bottom_ring)

    top_ring = stem_verts[0]
    for j in range(stem_rings):
        v1 = top_ring[j]
        v2 = top_ring[(j+1)%stem_rings]
        bm.faces.new((center_vert, v1, v2))

    bm.to_mesh(mesh)
    bm.free()

    obj.rotation_euler = (math.radians(-30), 0, math.radians(45))
    obj.location = (0, 0, 0)

if __name__ == "__main__":
    clear_scene()
    create_maple_leaf()
