import bpy
import bmesh
import math
import random
from mathutils import Vector, Quaternion

def clear_scene():
    """Removes all objects from the current scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple principled BSDF material with a given color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Base Color'].default_value = color
    # Make it look a bit more like wood/bark (rougher)
    node_principled.inputs['Roughness'].default_value = 0.9
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_branch_segment(bm, start, end, radius_start, radius_end):
    """Creates a tapered cylinder segment between two points."""
    direction = (end - start).normalized()
    length = (end - start).length
    if length < 0.001: return

    res = bmesh.ops.create_cone(
        bm, 
        cap_ends=True, 
        segments=8, 
        radius1=radius_start, 
        radius2=radius_end, 
        depth=length
    )
    
    midpoint = (start + end) / 2
    rot_quat = direction.to_track_quat('Z', 'Y')
    
    for v in res['verts']:
        v.co = (rot_quat @ v.co) + midpoint

def create_knot(bm, position, radius):
    """Creates a small, irregular sphere at a joint to simulate knobby bark."""
    start_vert_idx = len(bm.verts)
    bmesh.ops.create_uvsphere(
        bm, 
        u_segments=8, 
        v_segments=8, 
        radius=radius
    )
    # Randomize the knot shape so it's not a perfect sphere
    for v in bm.verts[start_vert_idx:]:
        jitter = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2))) * radius
        v.co += position + jitter

def create_tree_recursive(bm, start, direction, length, radius, depth):
    """Recursively generates bare branches and twigs."""
    if depth < 0:
        return

    # Add organic wiggle to growth
    jitter = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2)))
    actual_dir = (direction + jitter).normalized()
    end = start + (actual_dir * length)
    
    # Taper the branch significantly for "slender" look
    radius_end = radius * random.uniform(0.6, 0.8)
    create_branch_segment(bm, start, end, radius, radius_end)
    
    # Only add knots at deeper branching points to avoid "beaded string" look
    if depth % 2 == 0:
        create_knot(bm, end, radius * random.uniform(1.1, 1.4))

    if depth > 0:
        num_branches = random.randint(2, 3)
        for _ in range(num_branches):
            # Wider spread for the sparse network effect
            spread_angle = math.radians(random.uniform(30, 60))
            rand_axis = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()
            rot_quat = Quaternion(rand_axis, spread_angle)
            new_dir = rot_quat @ actual_dir
            
            create_tree_recursive(
                bm, 
                end, 
                new_dir, 
                length * random.uniform(0.6, 0.8), 
                radius_end, 
                depth - 1
            )

def generate_dead_tree():
    clear_scene()
    
    mesh = bpy.data.meshes.new("DeadTree")
    obj = bpy.data.objects.new("DeadTree", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    root_start = Vector((0, 0, 0))
    root_dir = Vector((0, 0, 1))
    base_radius = 0.8
    trunk_height = 4.5
    recursion_depth = 5 # Increased depth for slender twigs
    
    # Build trunk in segments
    current_pos = root_start
    current_dir = root_dir
    current_rad = base_radius
    
    segments = 6
    for i in range(segments):
        seg_len = trunk_height / segments
        rad_start = current_rad
        # Stronger taper from base to top
        rad_end = current_rad * random.uniform(0.8, 0.9)
        
        jitter = Vector((random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15), 0))
        actual_dir = (current_dir + jitter).normalized()
        end_pos = current_pos + (actual_dir * seg_len)
        
        create_branch_segment(bm, current_pos, end_pos, rad_start, rad_end)
        
        # Occasional knots on the main trunk
        if random.random() > 0.6:
            create_knot(bm, end_pos, rad_end * 1.3)

        # Start some branches along the upper half of the trunk (not just at top)
        if i >= segments // 2 and random.random() > 0.4:
            branch_dir = (actual_dir + Vector((random.uniform(-1,1), random.uniform(-1,1), random.uniform(-1,1)))).normalized()
            create_tree_recursive(bm, end_pos, branch_dir, seg_len * 1.5, rad_end * 0.6, recursion_depth - 2)

        current_pos = end_pos
        current_dir = actual_dir
        current_rad = rad_end

    # Final canopy branching from the top
    create_tree_recursive(bm, current_pos, current_dir, 1.5, current_rad, recursion_depth - 2)
    
    bm.to_mesh(mesh)
    bm.free()
    
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    russet_brown = (0.25, 0.14, 0.08, 1.0)
    mat = create_material("BarkMaterial", russet_brown)
    obj.data.materials.append(mat)

if __name__ == "__main__":
    generate_dead_tree()
