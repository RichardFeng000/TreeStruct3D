import bpy
import bmesh
import math
import random
from mathutils import Vector, Quaternion

def clear_scene():
    """Clear all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_branch_segment(bm, start_pos, direction, radius_start, radius_end, length):
    """Creates a tapered cylinder segment in the bmesh."""
    res = 10  # Resolution of the branch cross-section
    
    # Calculate local coordinate system for the ring
    up = Vector((0, 0, 1))
    if abs(direction.dot(up)) > 0.9:
        up = Vector((0, 1, 0))
    
    right = direction.cross(up).normalized()
    top = direction.cross(right).normalized()
    
    # Base ring
    base_verts = []
    for i in range(res):
        angle = (2 * math.pi * i) / res
        offset = (right * math.cos(angle) + top * math.sin(angle)) * radius_start
        base_verts.append(bm.verts.new(start_pos + offset))
    
    # Top ring
    end_pos = start_pos + direction * length
    top_verts = []
    for i in range(res):
        angle = (2 * math.pi * i) / res
        offset = (right * math.cos(angle) + top * math.sin(angle)) * radius_end
        top_verts.append(bm.verts.new(end_pos + offset))
    
    # Bridge rings with faces
    for i in range(res):
        v1 = base_verts[i]
        v2 = base_verts[(i + 1) % res]
        v3 = top_verts[(i + 1) % res]
        v4 = top_verts[i]
        try:
            bm.faces.new((v1, v2, v3, v4))
        except ValueError:
            # Face might already exist if geometry overlaps significantly
            pass
        
    return top_verts, end_pos

def grow_coral(bm, start_pos, direction, radius, length, depth):
    """Recursive function to generate branching coral structure."""
    if depth <= 0:
        return

    # Taper the branch slightly
    radius_end = radius * 0.75
    
    # Create the segment
    top_verts, end_pos = create_branch_segment(bm, start_pos, direction, radius, radius_end, length)
    
    # Determine number of child branches (2 to 4)
    num_branches = random.randint(2, 4)
    
    for _ in range(num_branches):
        # Create a rotation around the branch axis and then tilt it outwards
        # We create a random orthogonal vector for tilting
        up = Vector((0, 0, 1))
        if abs(direction.dot(up)) > 0.9:
            up = Vector((0, 1, 0))
        right = direction.cross(up).normalized()
        top = direction.cross(right).normalized()
        
        # Random mix of orthogonal vectors for the tilt direction
        tilt_vec = (right * random.uniform(-1, 1) + top * random.uniform(-1, 1)).normalized()
        
        # Rotate original direction towards tilt vector
        axis = direction.cross(tilt_vec).normalized()
        angle = random.uniform(0.4, 0.9) # Branching angle in radians
        rot_quat = Quaternion(axis, angle)
        new_dir = (rot_quat @ direction).normalized()
        
        # Recursively grow branches with decaying size and length
        grow_coral(
            bm, 
            end_pos, 
            new_dir, 
            radius_end * random.uniform(0.6, 0.8), 
            length * random.uniform(0.6, 0.8), 
            depth - 1
        )

def main():
    clear_scene()

    # Configuration
    ROOT_RADIUS = 0.4
    ROOT_LENGTH = 1.5
    MAX_DEPTH = 5 # Recursive depth of branching
    
    bm = bmesh.new()

    # Start from origin, growing upwards as the primary trunk
    start_pos = Vector((0, 0, 0))
    initial_dir = Vector((0, 0, 1))
    
    # The root doesn't branch immediately at (0,0,0) to give it a base
    # We create one main trunk segment first
    trunk_radius_end = ROOT_RADIUS * 0.85
    top_verts, end_pos = create_branch_segment(bm, start_pos, initial_dir, ROOT_RADIUS, trunk_radius_end, ROOT_LENGTH)
    
    # Now grow the fractal branches from the top of the trunk
    grow_coral(bm, end_pos, initial_dir, trunk_radius_end, ROOT_LENGTH * 0.8, MAX_DEPTH)

    # Correct way to create a mesh and object in Blender 5.0
    mesh = bpy.data.meshes.new("CoralMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("TreeCoral", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Cleanup BMesh
    bm.free()

    # Polish the geometry
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Smooth shading for organic look
    bpy.ops.object.shade_smooth()

    # Apply a Subdivision Surface modifier to make it "smooth" and "fleshy"
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2

    # Ensure the root is at the origin
    obj.location = (0, 0, 0)
    
    # Slight irregularity in overall scale for organic feel
    obj.scale = (1.05, 0.98, 1.0)

if __name__ == "__main__":
    main()
