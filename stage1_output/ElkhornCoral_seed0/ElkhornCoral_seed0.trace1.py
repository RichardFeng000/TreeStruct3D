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
    segments = 8
    seg_len = length / segments
    
    # Create initial cross-section (flattened ellipse)
    res = 12
    verts = []
    up = Vector((0, 0, 1))
    if abs(direction.dot(up)) > 0.9:
        up = Vector((0, 1, 0))
    
    right = direction.cross(up).normalized()
    actual_up = right.cross(direction).normalized()
    
    # Create initial ring of vertices for the base of the branch
    for i in range(res):
        angle = (2 * math.pi * i) / res
        off = (right * math.cos(angle) * width_start + actual_up * math.sin(angle) * thickness_start) * 0.5
        v = bm.verts.new(start_pos + off)
        verts.append(v)
    
    bm.faces.new(verts)
    last_face = bm.faces[-1]
    
    current_dir = direction.copy()
    
    for s in range(segments):
        # Palmate growth: widen the branch as it extends
        growth_factor = 1.0 + (s / segments) * 2.5
        curvature = random.uniform(-0.2, 0.2)
        
        # Slightly shift direction for organic look
        random_offset = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized() * curvature
        current_dir = (current_dir + random_offset).normalized()
        
        # Extrude the face
        res_ext = bmesh.ops.extrude_face_region(bm, geom=[last_face])
        verts_new = [v for v in res_ext['geom'] if isinstance(v, bmesh.types.BMVert)]
        
        # Calculate center of new verts to scale around it
        center = Vector((0, 0, 0))
        for v in verts_new:
            center += v.co
        center /= len(verts_new)
        
        # Move and scale the vertices
        # We want width to increase but thickness to stay relatively thin
        for v in verts_new:
            v.co = center + (current_dir * seg_len) 
            local_pos = v.co - (center + current_dir * seg_len) # this is wrong, let's recalculate local
            # We need the original offset from the previous segment
            pass
        
        # Correct movement and scaling logic
        # Let's use a different approach for positioning:
        # Shift all vertices by the direction vector first
        for v in verts_new:
            v.co += current_dir * seg_len
            
        # Now scale them relative to their new center to create the 'fan'
        center = Vector((0, 0, 0))
        for v in verts_new: center += v.co
        center /= len(verts_new)
        
        for v in verts_new:
            local_vec = v.co - center
            # Projection of local vec onto the 'right' and 'up' axes to scale differently
            # Since it's a flat branch, we amplify the horizontal expansion
            v.co = center + (local_vec * growth_factor)
            # Clamp thickness slightly so it doesn't become too fat
            # Project onto actual_up and scale down relative to width
            proj_up = local_vec.dot(actual_up) * actual_up
            proj_right = local_vec - proj_up
            v.co = center + (proj_right * growth_factor) + (proj_up * (1.0 + s*0.1))

        # Update last face for next iteration
        for f in res_ext['geom']:
            if isinstance(f, bmesh.types.BMFace):
                last_face = f
                break
    
    return last_face

def build_elkhorn():
    clear_scene()
    
    # Create mesh and object
    mesh = bpy.data.meshes.new("ElkhornCoral")
    obj = bpy.data.objects.new("ElkhornCoral", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # 1. Create the Base Mound
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.5)
    for v in bm.verts:
        if v.co.z < 0:
            v.co.z = 0 # Flatten the bottom
            
    # 2. Create Main Branches
    num_branches = 5
    branch_starts = []
    # Sample some points on top of the base for branch origins
    for i in range(num_branches):
        angle = (2 * math.pi * i / num_branches)
        pos = Vector((math.cos(angle)*0.3, math.sin(angle)*0.3, 0.1))
        # Randomize pos slightly
        pos += Vector((random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)))
        
        # Direction: generally upward and outward
        dir_vec = (pos + Vector((0, 0, 1))).normalized()
        
        # Create the main "blade" branch
        last_face = create_coral_branch(bm, pos, dir_vec, length=2.0, width_start=0.2, thickness_start=0.1)
        
        # Add a few side-shoots for complexity
        num_side_shoots = random.randint(1, 3)
        for j in range(num_side_shoots):
            shoot_pos = pos + dir_vec * (random.uniform(0.5, 1.5))
            # Shoot direction: perpendicular to main branch and slightly up
            shoot_dir = Vector((random.uniform(-1,1), random.uniform(-1,1), 1)).normalized()
            create_coral_branch(bm, shoot_pos, shoot_dir, length=1.2, width_start=0.15, thickness_start=0.08)

    # Finalize BMesh to Mesh
    bm.to_mesh(mesh)
    bm.free()
    
    # 3. Geometric Detail via Modifiers
    # Smooth out the blocky extrusions
    subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 2
    
    # Add a Displace modifier to achieve the "rough, granular surface texture"
    displace = obj.modifiers.new(name="Granular", type='DISPLACE')
    tex = bpy.data.textures.new("CoralNoise", type='CLOUDS')
    tex.noise_scale = 0.15
    displace.texture = tex
    displace.strength = 0.06
    
    # Final smoothing and shading
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    build_elkhorn()
