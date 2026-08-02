import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clear all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_grass_stalk():
    # Parameters for a more natural, wild look
    stem_height = 8.0
    segments = 40
    stem_radius = 0.025 # Slightly thicker base/middle
    num_leaves = 9
    leaf_length_min = 2.0
    leaf_length_max = 3.5
    leaf_width_base = 0.18  # Wider blades
    curvature_strength = 1.4 # More pronounced natural bend

    mesh = bpy.data.meshes.new("GrassStalk")
    obj = bpy.data.objects.new("GrassStalk", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # 1. Generate the stem path with more organic curvature
    path_points = []
    for i in range(segments + 1):
        t = i / segments
        z = t * stem_height
        # Use combined sines for a more natural "wild" curve
        x = math.sin(t * math.pi * 0.7) * curvature_strength * t
        y = math.cos(t * math.pi * 1.1 + 0.5) * (curvature_strength * 0.6) * t
        path_points.append(Vector((x, y, z)))

    # Create the stem geometry as a tube
    stem_verts = []
    rings = 8 
    for p in path_points:
        ring = []
        # Taper the stem slightly towards the top
        t = len(stem_verts) / segments
        current_radius = stem_radius * (1.0 - t * 0.5)
        for j in range(rings):
            angle = (j / rings) * 2 * math.pi
            offset = Vector((math.cos(angle), math.sin(angle), 0)) * current_radius
            v = bm.verts.new(p + offset)
            ring.append(v)
        stem_verts.append(ring)

    for i in range(len(stem_verts) - 1):
        r1, r2 = stem_verts[i], stem_verts[i+1]
        for j in range(rings):
            bm.faces.new((r1[j], r1[(j + 1) % rings], r2[(j + 1) % rings], r2[j]))

    # 2. Generate the leaves (blades)
    # Distribute them more evenly but with slight randomness
    leaf_heights = []
    for i in range(num_leaves):
        h = (i / num_leaves) * 0.8 + 0.1 # Keep away from absolute bottom/top
        idx = int(h * segments)
        leaf_heights.append(idx)

    for idx in leaf_heights:
        start_pos = path_points[idx]
        
        # Calculate tangent for orientation
        prev_p = path_points[max(0, idx - 1)]
        next_p = path_points[min(segments, idx + 1)]
        tangent = (next_p - prev_p).normalized()
        
        # Alternating sides
        side_dir = Vector((1, 0, 0)).cross(tangent).normalized()
        if idx % 2 == 0:
            side_dir = -side_dir

        length = random.uniform(leaf_length_min, leaf_length_max)
        
        # Leaf geometry (blade ribbon)
        leaf_segments = 15
        v_lefts, v_rights = [], []
        
        for s in range(leaf_segments + 1):
            t = s / leaf_segments
            
            # Spine: starts outward, arcs slightly up then droops down naturally
            outward = side_dir * length * t
            upward = tangent * (math.sin(t * math.pi * 0.5) * 0.6)
            droop = Vector((0, 0, -1)) * (length * 0.4 * (t**2))
            
            spine_pos = start_pos + outward + upward + droop
            
            # Taper width from base to tip
            current_width = leaf_width_base * (1.0 - t * 0.9)
            
            # Calculate cross-section direction for the blade width
            # Width is perpendicular to both tangent and spine direction
            spine_dir = (spine_pos - start_pos).normalized() if t > 0 else side_dir
            width_dir = spine_dir.cross(tangent).normalized()
            
            v_l = bm.verts.new(spine_pos + width_dir * (current_width / 2))
            v_r = bm.verts.new(spine_pos - width_dir * (current_width / 2))
            v_lefts.append(v_l)
            v_rights.append(v_r)

        for s in range(leaf_segments):
            bm.faces.new((v_lefts[s], v_lefts[s+1], v_rights[s+1], v_rights[s]))

    bm.to_mesh(mesh)
    bm.free()

    # Final polish
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    
    for poly in mesh.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    clear_scene()
    create_grass_stalk()
