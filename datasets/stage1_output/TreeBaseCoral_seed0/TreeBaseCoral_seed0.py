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
    """Creates a cylinder segment. Vertices will be merged later via remove_doubles."""
    res = 8
    
    # Local coordinate system for the rings
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
            pass
        
    return end_pos

def grow_coral(bm, start_pos, direction, radius, length, depth):
    """Recursive function to generate a sprawling coral structure."""
    if depth <= 0 or radius < 0.015:
        return

    # Taper the branch slightly
    radius_end = radius * random.uniform(0.65, 0.8)
    
    # Add some curvature by jittering direction slightly for each segment
    jitter = Vector((random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)))
    current_dir = (direction + jitter).normalized()
    
    end_pos = create_branch_segment(bm, start_pos, current_dir, radius, radius_end, length)
    
    # Branching factor
    num_children = random.randint(2, 3) if depth > 1 else random.randint(1, 2)
    
    for _ in range(num_children):
        # Wide angles for a sprawling effect
        angle = random.uniform(0.6, 1.3)
        axis = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()
        rot_quat = Quaternion(axis, angle)
        new_dir = (rot_quat @ current_dir).normalized()
        
        grow_coral(
            bm, 
            end_pos, 
            new_dir, 
            radius_end * random.uniform(0.75, 0.9), 
            length * random.uniform(0.7, 0.85), 
            depth - 1
        )

def main():
    clear_scene()

    # Configuration for a sprawling coral base mesh
    ROOT_RADIUS = 0.4
    ROOT_LENGTH = 0.3
    MAX_DEPTH = 5 
    NUM_MAIN_BRANCHES = 6 # More branches from root for wider footprint
    
    bm = bmesh.new()

    # 1. Create a shared central root (a short, thick base segment)
    root_start = Vector((0, 0, 0))
    root_dir = Vector((0, 0, 1))
    root_end_pos = create_branch_segment(
        bm, root_start, root_dir, ROOT_RADIUS, ROOT_RADIUS * 0.85, ROOT_LENGTH
    )
    
    # 2. Sprout main branches from the top of the shared root
    for i in range(NUM_MAIN_BRANCHES):
        phi = (2 * math.pi * i) / NUM_MAIN_BRANCHES
        theta = random.uniform(0.5, 1.2) # Push outward more for wide footprint
        
        initial_dir = Vector((
            math.sin(theta) * math.cos(phi),
            math.sin(theta) * math.sin(phi),
            math.cos(theta)
        )).normalized()
        
        grow_coral(
            bm, 
            root_end_pos, 
            initial_dir, 
            ROOT_RADIUS * 0.75, 
            ROOT_LENGTH * 1.2, 
            MAX_DEPTH - 1
        )

    # IMPORTANT: Weld all overlapping vertices to ensure a manifold skin and smooth Subdiv result
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    
    # Mesh creation
    mesh = bpy.data.meshes.new("CoralMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("TreeCoral", mesh)
    bpy.context.collection.objects.link(obj)
    bm.free()

    # Polish and Smoothing
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()

    # Subdivision for organic look
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 3
    subsurf.render_levels = 3

    obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
