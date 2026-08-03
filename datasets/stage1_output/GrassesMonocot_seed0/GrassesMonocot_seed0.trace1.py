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
    
    # Parameters
    height = 4.0
    segments = 48
    stem_radius = 0.012
    num_leaves = 12
    leaf_length_max = 1.5
    leaf_width_max = 0.07
    curvature_amplitude = 0.5
    
    # --- STEM GEOMETRY ---
    path_points = []
    for i in range(segments + 1):
        t = i / segments
        z = t * height
        # Natural organic curve
        x = math.sin(t * math.pi * 0.7) * curvature_amplitude * (t**1.2)
        y = math.cos(t * math.pi * 0.5 + 0.5) * (curvature_amplitude * 0.6) * (t**1.2)
        path_points.append(Vector((x, y, z)))

    # Use a single BMesh for the entire stalk assembly
    bm = bmesh.new()
    
    # Create stem tube
    ring_res = 8
    rings = []
    for p in path_points:
        ring = []
        for j in range(ring_res):
            angle = (2 * math.pi * j) / ring_res
            vx = p.x + math.cos(angle) * stem_radius
            vy = p.y + math.sin(angle) * stem_radius
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
        # Distribute leaves along the stem (avoiding ends)
        t = 0.15 + (i / (num_leaves - 1)) * 0.7 if num_leaves > 1 else 0.5
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
        up_leaf = right.cross(tangent).normalized()

        # Alternate side and add some randomness to angle
        side_mult = 1 if (i % 2 == 0) else -1
        angle_offset = random.uniform(-0.3, 0.3)
        
        # Rotate the "right" vector slightly for natural look
        rot_axis = tangent
        rot_vec = right.copy()
        # Simple rotation formula: v_rot = v*cos(a) + (axis x v)*sin(a)
        rot_vec = rot_vec * math.cos(angle_offset) + rot_axis.cross(rot_vec) * math.sin(angle_offset)
        side_dir = rot_vec.normalized() * side_mult
        
        # Leaf dimensions
        l_len = random.uniform(0.7, leaf_length_max)
        l_wid = random.uniform(0.03, leaf_width_max)
        l_segs = 16

        prev_v_left = None
        prev_v_right = None
        
        for s in range(l_segs + 1):
            st = s / l_segs
            # Taper and curve
            current_width = l_wid * math.sin(st * math.pi) # Bulge in middle, taper at ends
            if st > 0.8: current_width *= (1.0 - (st-0.8)*5.0) # Sharper tip
            
            # Droop and outward curve
            curve_out = side_dir * st * l_len
            curve_down = Vector((0, 0, -1)) * (st**2 * 0.8)
            curve_twist = up_leaf * math.sin(st * math.pi * 0.5) * 0.2
            
            center = p_start + curve_out + curve_down + curve_twist
            
            # Edge vertices
            offset = side_dir.cross(tangent).normalized() * (current_width / 2.0)
            v_left = bm.verts.new(center + offset)
            v_right = bm.verts.new(center - offset)
            
            if prev_v_left is not None:
                bm.faces.new((prev_v_left, v_left, v_right, prev_v_right))
                
            prev_v_left = v_left
            prev_v_right = v_right

    # Finalize mesh data
    bm.to_mesh() # This ensures the bmesh is updated internally
    
    # Correct way to create an object from BMesh in Blender 5.0:
    # 1. Create a Mesh data block
    mesh_data = bpy.data.meshes.new("GrassStalkMesh")
    # 2. Transfer BMesh to the mesh data block
    bm.to_mesh(mesh_data)
    # 3. Create object with that data
    stalk_obj = bpy.data.objects.new("GrassStalk", mesh_data)
    # 4. Link to collection
    bpy.context.collection.objects.link(stalk_obj)
    
    # Cleanup BMesh
    bm.free()

    # Add a subdivision surface modifier for smoothness
    subsurf = stalk_obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    subsurf.render_levels = 2

if __name__ == "__main__":
    clear_scene()
    create_grass_stalk()
