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
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_branch_segment(bm, start, end, radius_start, radius_end):
    """Creates a tapered cylinder segment between two points using bmesh."""
    direction = (end - start).normalized()
    length = (end - start).length
    
    # Create cone along Z axis and then transform it
    res = bmesh.ops.create_cone(
        bm, 
        cap_ends=True, 
        segments=8, 
        radius1=radius_start, 
        radius2=radius_end, 
        depth=length
    )
    
    # The cone is created centered at origin along Z axis from -length/2 to length/2
    # We need it from start to end.
    midpoint = (start + end) / 2
    
    # Calculate rotation to align Z with the direction vector
    rot_quat = direction.to_track_quat('Z', 'Y')
    
    for v in res['verts']:
        v.co = (rot_quat @ v.co) + midpoint

def create_knot(bm, position, radius):
    """Creates a small sphere at a joint to simulate knobby bark."""
    # Record current vertex count to move only the new vertices
    start_vert_idx = len(bm.verts)
    bmesh.ops.create_uvsphere(
        bm, 
        u_segments=8, 
        v_segments=8, 
        radius=radius
    )
    # Shift all newly created vertices to the joint position
    for v in bm.verts[start_vert_idx:]:
        v.co += position

def create_tree_recursive(bm, start, direction, length, radius, depth):
    """Recursively generates branches and twigs."""
    if depth < 0:
        return

    # Add a slight wiggle to the growth direction
    jitter = Vector((random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15)))
    actual_dir = (direction + jitter).normalized()
    end = start + (actual_dir * length)
    
    # Taper the branch
    radius_end = radius * 0.65
    create_branch_segment(bm, start, end, radius, radius_end)
    
    # Add a knot at the junction/tip
    create_knot(bm, end, radius * (1.2 + random.uniform(0, 0.3)))

    if depth > 0:
        # Branching factor
        num_branches = random.randint(2, 3)
        for _ in range(num_branches):
            # Randomize child direction spread
            spread_angle = math.radians(random.uniform(25, 50))
            rand_axis = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()
            rot_quat = Quaternion(rand_axis, spread_angle)
            new_dir = rot_quat @ actual_dir
            
            # Recursive call with decreasing length and radius
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
    
    # Mesh and Object setup
    mesh = bpy.data.meshes.new("DeadTree")
    obj = bpy.data.objects.new("DeadTree", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Initial Root Parameters
    root_start = Vector((0, 0, 0))
    root_dir = Vector((0, 0, 1))
    base_radius = 0.6
    trunk_height = 3.5
    recursion_depth = 4
    
    # The trunk is built in segments for irregularity and widening at base
    current_pos = root_start
    current_dir = root_dir
    current_rad = base_radius
    
    segments = 4
    for i in range(segments):
        seg_len = trunk_height / segments
        # Widening effect: The first segment starts at base_radius, others taper more
        # We manually calculate radius for the start and end of this specific chunk
        rad_start = current_rad
        rad_end = current_rad * 0.82
        
        # Randomize trunk direction slightly
        jitter = Vector((random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), 0))
        actual_dir = (current_dir + jitter).normalized()
        end_pos = current_pos + (actual_dir * seg_len)
        
        create_branch_segment(bm, current_pos, end_pos, rad_start, rad_end)
        
        # Add a knot at the junction
        create_knot(bm, end_pos, rad_end * 1.2)
        
        current_pos = end_pos
        current_dir = actual_dir
        current_rad = rad_end

    # Start recursive branching from the top of the trunk
    create_tree_recursive(bm, current_pos, current_dir, 1.8, current_rad, recursion_depth)
    
    # Finalize mesh
    bm.to_mesh(mesh)
    bm.free()
    
    # Apply Subdivision Surface for organic look and to blend knots with branches
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    # Smooth shading
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    # Material Setup (Russet/Brown)
    russet_brown = (0.3, 0.18, 0.12, 1.0) # Dark russet brown
    mat = create_material("BarkMaterial", russet_brown)
    obj.data.materials.append(mat)

if __name__ == "__main__":
    generate_dead_tree()
