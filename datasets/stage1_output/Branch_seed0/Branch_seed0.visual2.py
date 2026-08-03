import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_leaf(bm, position, direction):
    """Creates a tiny, simple leaf mesh."""
    # Increased size slightly to ensure visibility in renders
    size = 0.08
    width = 0.04
    
    up = Vector((0, 1, 0)) if abs(direction.z) < 0.9 else Vector((0, 0, 1))
    right = direction.cross(up).normalized()
    actual_up = right.cross(direction).normalized()

    # Leaf as a simple diamond/oval plane
    v0 = bm.verts.new(position) # Base
    v1 = bm.verts.new(position + (direction * size)) # Tip
    v2 = bm.verts.new(position + (right * width * 0.5) + (direction * size * 0.4))
    v3 = bm.verts.new(position + (right * -width * 0.5) + (direction * size * 0.4))
    
    try:
        bm.faces.new((v0, v2, v1, v3))
    except:
        pass

def create_branch_segment(bm, start_pos, direction, length, radius, depth):
    """Recursively creates the twig structure with better organic curvature."""
    if depth < 0 or radius < 0.002:
        return start_pos

    num_segments = 8
    seg_len = length / num_segments
    curr_pos = Vector(start_pos)
    curr_dir = Vector(direction).normalized()
    
    for i in range(num_segments):
        # Stronger jitter for organic feel
        jitter = Vector((random.uniform(-0.3, 0.3), 
                         random.uniform(-0.3, 0.3), 
                         random.uniform(-0.3, 0.3)))
        curr_dir = (curr_dir + jitter * 0.2).normalized()
        next_pos = curr_pos + curr_dir * seg_len
        
        # Cylinder segment cross-section
        res = 6
        ring1 = []
        ring2 = []
        perp = Vector((0, 1, 0)) if abs(curr_dir.z) < 0.9 else Vector((1, 0, 0))
        right = curr_dir.cross(perp).normalized()
        up = right.cross(curr_dir).normalized()
        
        for j in range(res):
            angle = (2 * math.pi / res) * j
            offset = (right * math.cos(angle) + up * math.sin(angle)) * radius
            ring1.append(bm.verts.new(curr_pos + offset))
            ring2.append(bm.verts.new(next_pos + offset))
        
        for j in range(res):
            try:
                bm.faces.new((ring1[j], ring2[j], ring2[(j+1)%res], ring1[(j+1)%res]))
            except:
                pass
        
        # Sparse leaves along the stem
        if random.random() < 0.1:
            leaf_dir = (right * random.uniform(-1,1) + up * random.uniform(-1,1)).normalized()
            create_leaf(bm, curr_pos, leaf_dir)

        curr_pos = next_pos

    # Side offshoots for "several minimal slim offshoots"
    if depth > 0:
        num_offshoots = random.randint(1, 3)
        for _ in range(num_offshoots):
            # Branching angle relative to current direction
            offset_dir = Vector((random.uniform(-1, 1), 
                                 random.uniform(-1, 1), 
                                 random.uniform(-1, 1)))
            off_dir = (curr_dir + offset_dir * 0.5).normalized()
            create_branch_segment(bm, curr_pos, off_dir, length * 0.6, radius * 0.7, depth - 1)

    # Final leaf at tip
    if random.random() < 0.7:
        create_leaf(bm, curr_pos, curr_dir)

    return curr_pos

def main():
    clear_scene()

    mesh = bpy.data.meshes.new("Twig")
    obj = bpy.data.objects.new("Twig", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # Start parameters for a slender, delicate twig
    start_pos = Vector((0, 0, 0))
    main_dir = Vector((0, 0, 1)).normalized()
    length = 1.2
    radius = 0.015
    depth = 3 # Increased depth for more offshoots

    create_branch_segment(bm, start_pos, main_dir, length, radius, depth)

    bm.to_mesh(mesh)
    bm.free()

    # Smooth the organic geometry
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    
    # Center and scale for "small fraction of frame" feel
    obj.location = (0, 0, -0.6)

if __name__ == "__main__":
    main()
