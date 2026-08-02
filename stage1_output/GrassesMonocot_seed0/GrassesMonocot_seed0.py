import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears all objects from the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_grass_stalk():
    """Constructs a procedural grass stalk with a curved stem and alternating leaves."""
    
    # --- Parameters ---
    height = 4.0
    segments = 60
    stem_radius_bottom = 0.02
    stem_radius_top = 0.008
    num_leaves = 15
    leaf_length_max = 1.8
    leaf_width_max = 0.08
    curvature_amplitude = 0.6
    
    # --- STEM GEOMETRY ---
    path_points = []
    for i in range(segments + 1):
        t = i / segments
        z = t * height
        # Organic curve: combine sine waves for a natural drift
        x = math.sin(t * math.pi * 0.8) * curvature_amplitude * (t**1.5)
        y = math.cos(t * math.pi * 0.6 + 0.4) * (curvature_amplitude * 0.7) * (t**1.5)
        path_points.append(Vector((x, y, z)))

    bm = bmesh.new()
    
    # Create stem tube with tapering
    ring_res = 8
    rings = []
    for i, p in enumerate(path_points):
        t = i / segments
        current_radius = stem_radius_bottom + (stem_radius_top - stem_radius_bottom) * t
        ring = []
        for j in range(ring_res):
            angle = (2 * math.pi * j) / ring_res
            vx = p.x + math.cos(angle) * current_radius
            vy = p.y + math.sin(angle) * current_radius
            vz = p.z
            ring.append(bm.verts.new(Vector((vx, vy, vz))))
        rings.append(ring)

    for i in range(len(rings) - 1):
        r1 = rings[i]
        r2 = rings[i+1]
        for j in range(ring_res):
            v1 = r1[j]
            v2 = r1[(j + 1) % ring_res]
            v3 = r2[(j + 1) % ring_res]
            v4 = r2[j]
            bm.faces.new((v1, v2, v3, v4))

    # --- LEAF GEOMETRY ---
    for i in range(num_leaves):
        # Distribute leaves along the stem (avoiding extreme ends)
        t = 0.1 + (i / (num_leaves - 1)) * 0.8 if num_leaves > 1 else 0.5
        idx = int(t * segments)
        p_start = path_points[idx]
        
        # Calculate tangent for orientation
        if idx < segments:
            tangent = (path_points[idx+1] - path_points[idx]).normalized()
        else:
            tangent = (path_points[idx] - path_points[idx-1]).normalized()
            
        # Create orthonormal basis
        up_ref = Vector((0, 0, 1))
        if abs(tangent.dot(up_ref)) > 0.9:
            up_ref = Vector((0, 1, 0))
            
        right = tangent.cross(up_ref).normalized()
        up_leaf_axis = right.cross(tangent).normalized()

        # Alternate side and add randomness
        side_mult = 1 if (i % 2 == 0) else -1
        angle_offset = random.uniform(-0.4, 0.4)
        
        # Rotate the leaf projection vector around the stem tangent
        s_val = math.sin(angle_offset)
        c_val = math.cos(angle_offset)
        side_dir = (right * c_val + up_leaf_axis * s_val).normalized() * side_mult
        
        # Leaf dimensions and segments
        l_len = random.uniform(0.8, leaf_length_max)
        l_wid = random.uniform(0.04, leaf_width_max)
        l_segs = 20

        prev_v_left = None
        prev_v_right = None
        
        for s in range(l_segs + 1):
            st = s / l_segs
            # Taper: narrow at base, wide in middle, very sharp at tip
            if st < 0.2:
                current_width = l_wid * (st * 5)
            elif st > 0.4:
                current_width = l_wid * (1.0 - (st - 0.4) / 0.6)
            else:
                current_width = l_wid

            # Leaf curvature: outward, then drooping down, with a slight twist
            outward_vec = side_dir * st * l_len
            droop_vec = Vector((0, 0, -1)) * (st**2 * l_len * 0.6)
            twist_vec = up_leaf_axis * math.sin(st * math.pi) * 0.15
            
            center = p_start + outward_vec + droop_vec + twist_vec
            
            # Edge vertices: offset perpendicular to the leaf's primary growth direction
            # The "width" axis is cross of tangent and side_dir
            width_axis = tangent.cross(side_dir).normalized()
            offset = width_axis * (current_width / 2.0)
            v_left = bm.verts.new(center + offset)
            v_right = bm.verts.new(center - offset)
            
            if prev_v_left is not None:
                bm.faces.new((prev_v_left, v_left, v_right, prev_v_right))
                
            prev_v_left = v_left
            prev_v_right = v_right

    # --- Finalize and Create Object ---
    mesh_data = bpy.data.meshes.new("GrassStalkMesh")
    bm.to_mesh(mesh_data)
    bm.free()
    
    stalk_obj = bpy.data.objects.new("GrassStalk", mesh_data)
    bpy.context.collection.objects.link(stalk_obj)
    
    # Add Subdivision Surface for organic smoothness
    subsurf = stalk_obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    subsurf.render_levels = 2
    
    # Set shading to smooth
    for poly in mesh_data.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    clear_scene()
    create_grass_stalk()
