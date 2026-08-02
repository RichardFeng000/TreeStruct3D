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
    # Parameters for a natural, wild look
    stem_height = 10.0
    segments = 60
    stem_radius_base = 0.04
    stem_radius_top = 0.015
    num_leaves = 12
    leaf_length_min = 4.0
    leaf_length_max = 7.0
    leaf_width_base = 0.12
    curvature_amplitude = 1.8 # Increased for visible organic curve

    mesh = bpy.data.meshes.new("GrassStalk")
    obj = bpy.data.objects.new("GrassStalk", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # 1. Generate the stem path with organic curvature
    path_points = []
    for i in range(segments + 1):
        t = i / segments
        z = t * stem_height
        # Create a more pronounced, fluid curve using a combination of sines
        x = math.sin(t * math.pi * 0.8) * curvature_amplitude * t
        y = math.cos(t * math.pi * 1.2 + 0.5) * (curvature_amplitude * 0.7) * t
        path_points.append(Vector((x, y, z)))

    # Create the stem geometry as a tube
    stem_verts = []
    rings = 8 
    for i, p in enumerate(path_points):
        ring = []
        t = i / segments
        current_radius = stem_radius_base + (stem_radius_top - stem_radius_base) * t
        for j in range(rings):
            angle = (j / rings) * 2 * math.pi
            offset = Vector((math.cos(angle), math.sin(angle), 0)) * current_radius
            # Orient offset based on stem direction to keep tube consistent
            v = bm.verts.new(p + offset)
            ring.append(v)
        stem_verts.append(ring)

    for i in range(len(stem_verts) - 1):
        r1, r2 = stem_verts[i], stem_verts[i+1]
        for j in range(rings):
            bm.faces.new((r1[j], r1[(j + 1) % rings], r2[(j + 1) % rings], r2[j]))

    # 2. Generate the elongated leaves (blades)
    # Spread them along the length, avoiding extreme ends
    for i in range(num_leaves):
        t_pos = 0.15 + (i / (num_leaves - 1)) * 0.7
        idx = int(t_pos * segments)
        start_pos = path_points[idx]
        
        # Orientation vectors
        prev_p = path_points[max(0, idx - 1)]
        next_p = path_points[min(segments, idx + 1)]
        tangent = (next_p - prev_p).normalized()
        
        # Create an alternating perpendicular direction for the leaves
        base_perp = Vector((0, 1, 0)).cross(tangent).normalized()
        side_dir = base_perp if i % 2 == 0 else -base_perp

        length = random.uniform(leaf_length_min, leaf_length_max)
        
        # Leaf geometry (blade ribbon)
        leaf_segments = 20
        v_lefts, v_rights = [], []
        
        for s in range(leaf_segments + 1):
            t = s / leaf_segments
            
            # Organic leaf shape: outward, then arches up slightly and droops down
            outward = side_dir * (length * t)
            upward = tangent * (math.sin(t * math.pi * 0.5) * 1.2)
            droop = Vector((0, 0, -1)) * (length * 0.6 * (t**2))
            
            spine_pos = start_pos + outward + upward + droop
            
            # Taper width from base to tip
            current_width = leaf_width_base * (1.0 - t * 0.95)
            
            # Width direction perpendicular to the local spine and tangent
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

    # Final polish: Subdivision for smoothness
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    
    for poly in mesh.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    clear_scene()
    create_grass_stalk()
