import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Clears all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_coral_branch(bm, start_pos, direction, length, width_start, thickness_start):
    """Creates a flattened, palmate branch segment starting from start_pos."""
    segments = 12
    seg_len = length / segments
    res = 12
    
    # Determine coordinate system for the cross-section
    up_global = Vector((0, 0, 1))
    if abs(direction.dot(up_global)) > 0.9:
        up_global = Vector((0, 1, 0))
    
    right_axis = direction.cross(up_global).normalized()
    actual_up_axis = right_axis.cross(direction).normalized()
    
    # Create initial ring of vertices (flattened ellipse)
    verts = []
    for i in range(res):
        angle = (2 * math.pi * i) / res
        off = (right_axis * math.cos(angle) * width_start + 
               actual_up_axis * math.sin(angle) * thickness_start) * 0.5
        v = bm.verts.new(start_pos + off)
        verts.append(v)
    
    # Create the initial face (the base of the branch)
    try:
        face = bm.faces.new(verts)
    except ValueError:
        # In case of duplicate vertices or degenerate faces
        return None

    current_dir = direction.copy()
    last_face = face
    
    for s in range(segments):
        # Palmate growth logic: widen as we go
        growth_factor = 1.0 + (s / segments) * 3.0
        
        # Add organic curvature
        random_offset = Vector((random.uniform(-0.2, 0.2), 
                                random.uniform(-0.2, 0.2), 
                                random.uniform(-0.2, 0.2)))
        current_dir = (current_dir + random_offset).normalized()
        
        # Extrude the last face
        extrude_res = bmesh.ops.extrude_face_region(bm, geom=[last_face])
        
        # Update lookup table to avoid IndexError
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        # Find the new face and vertices from the extrusion result
        new_verts = [v for v in extrude_res['geom'] if isinstance(v, bmesh.types.BMVert)]
        new_faces = [f for f in extrude_res['geom'] if isinstance(f, bmesh.types.BMFace)]
        
        if not new_faces:
            break
        last_face = new_faces[0]
        
        # Calculate center of the newly extruded ring
        center = Vector((0, 0, 0))
        for v in new_verts:
            center += v.co
        center /= len(new_verts)
        
        # Move and scale vertices to create the blade shape
        # The distance from center is scaled based on axis (width vs thickness)
        for v in new_verts:
            local_vec = v.co - center
            
            # Project local vector onto our axes to apply non-uniform scaling
            proj_right = local_vec.dot(right_axis) * right_axis
            proj_up = local_vec.dot(actual_up_axis) * actual_up_axis
            
            # Apply growth: width grows more than thickness
            scaled_vec = (proj_right * growth_factor) + (proj_up * (1.0 + s * 0.05))
            
            # Position the vertex along the extrusion path
            v.co = center + (current_dir * seg_len) + scaled_vec

    return last_face

def build_elkhorn():
    clear_scene()
    
    mesh = bpy.data.meshes.new("ElkhornCoral")
    obj = bpy.data.objects.new("ElkhornCoral", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # 1. Base Mound: A small, organic-looking lump at the origin
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.4)
    for v in bm.verts:
        if v.co.z < 0:
            v.co.z = -0.05 # Slightly flatten the base
        # Randomize the mound slightly
        v.co += Vector((random.uniform(-0.05, 0.05), 
                        random.uniform(-0.05, 0.05), 
                        random.uniform(-0.05, 0.05)))

    # 2. Generate Main Branches
    num_branches = 6
    for i in range(num_branches):
        angle = (2 * math.pi * i / num_branches)
        pos = Vector((math.cos(angle)*0.2, math.sin(angle)*0.2, 0.1))
        
        # Direction: Fan outwards and upwards
        dir_vec = Vector((math.cos(angle), math.sin(angle), 0.8)).normalized()
        
        # Main Blade branch
        create_coral_branch(bm, pos, dir_vec, length=2.5, width_start=0.3, thickness_start=0.1)
        
        # Occasional smaller side branches for complexity
        if random.random() > 0.4:
            side_pos = pos + dir_vec * (random.uniform(0.8, 1.5))
            side_dir = Vector((random.uniform(-1,1), random.uniform(-1,1), 1)).normalized()
            create_coral_branch(bm, side_pos, side_dir, length=1.2, width_start=0.2, thickness_start=0.08)

    # Finalize BMesh
    bm.to_mesh(mesh)
    bm.free()
    
    # 3. Detailing via Modifiers
    # Subdivision Surface for organic smoothness
    subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 2
    
    # Displace modifier for the granular, rough coral texture
    displace = obj.modifiers.new(name="GranularTexture", type='DISPLACE')
    tex = bpy.data.textures.new("CoralNoise", type='CLOUDS')
    tex.noise_scale = 0.1
    displace.texture = tex
    displace.strength = 0.05
    
    # Smoothing and final setup
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    build_elkhorn()
