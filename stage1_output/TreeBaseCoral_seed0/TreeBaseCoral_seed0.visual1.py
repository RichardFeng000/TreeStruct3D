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
    """Creates a slightly irregular tapered cylinder segment in the bmesh."""
    res = 8  # Lower resolution for more organic/faceted feel before subdivision
    
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
    
    # Top ring - add a slight random jitter to the end position for organic feel
    jitter = Vector((random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05)))
    end_pos = start_pos + direction * length + jitter
    
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
            pass
        
    return top_verts, end_pos

def grow_coral(bm, start_pos, direction, radius, length, depth):
    """Recursive function to generate sprawling branching coral structure."""
    if depth <= 0 or radius < 0.02:
        return

    # Taper the branch
    radius_end = radius * random.uniform(0.6, 0.8)
    
    # Create the segment
    top_verts, end_pos = create_branch_segment(bm, start_pos, direction, radius, radius_end, length)
    
    # Number of child branches increases randomness for coral look
    num_branches = random.randint(2, 4) if depth > 1 else random.randint(1, 3)
    
    for _ in range(num_branches):
        # Generate a random direction offset from the current one
        # We use a wider angle to ensure "sprawling" effect
        angle = random.uniform(0.5, 1.4) # Wider angles for coral branching
        
        # Random axis of rotation
        axis = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()
        if axis.dot(direction) > 0.9 or axis.dot(direction) < -0.9:
            # Ensure the axis is not parallel to direction
            axis = Vector((1, 0, 0)) if abs(direction.x) < 0.5 else Vector((0, 1, 0))

        rot_quat = Quaternion(axis, angle)
        new_dir = (rot_quat @ direction).normalized()
        
        grow_coral(
            bm, 
            end_pos, 
            new_dir, 
            radius_end * random.uniform(0.7, 0.9), 
            length * random.uniform(0.6, 0.85), 
            depth - 1
        )

def main():
    clear_scene()

    # Configuration for sprawling coral
    ROOT_RADIUS = 0.3
    INITIAL_LENGTH = 0.4 # Much shorter initial trunk to encourage early branching
    MAX_DEPTH = 5 
    NUM_BASE_STEMS = 4   # Multiple stems from the base for a wide footprint
    
    bm = bmesh.new()

    # Start with multiple root-level branches to create a "shared central root" that sprawls immediately
    for i in range(NUM_BASE_STEMS):
        start_pos = Vector((0, 0, 0))
        
        # Distribute initial stems outward from center
        phi = (2 * math.pi * i) / NUM_BASE_STEMS
        theta = random.uniform(0.5, 1.0) # Tilt away from vertical Z
        
        initial_dir = Vector((
            math.sin(theta) * math.cos(phi),
            math.sin(theta) * math.sin(phi),
            math.cos(theta)
        )).normalized()
        
        # Create the first segment of each base stem
        trunk_radius_end = ROOT_RADIUS * 0.8
        top_verts, end_pos = create_branch_segment(
            bm, start_pos, initial_dir, ROOT_RADIUS, trunk_radius_end, INITIAL_LENGTH
        )
        
        # Grow the fractal from each base stem
        grow_coral(
            bm, end_pos, initial_dir, trunk_radius_end, INITIAL_LENGTH * 1.2, MAX_DEPTH - 1
        )

    # Mesh creation
    mesh = bpy.data.meshes.new("CoralMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("TreeCoral", mesh)
    bpy.context.collection.objects.link(obj)
    bm.free()

    # Polish the geometry
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()

    # Heavy subdivision to create organic smooth surface from low-res BMesh segments
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 3
    subsurf.render_levels = 3

    obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
