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
    # A leaf is essentially a thin, slightly curved plane
    # Use a small diamond/oval shape
    size = 0.04
    width = 0.02
    
    # Create a local coordinate system for the leaf orientation
    # Leaf should grow roughly in direction but be flat
    up = Vector((0, 1, 0)) if abs(direction.z) < 0.9 else Vector((0, 0, 1))
    right = direction.cross(up).normalized()
    actual_up = right.cross(direction).normalized()

    # Define leaf vertices relative to position
    v0 = bm.verts.new(position) # Base
    v1 = bm.verts.new(position + (direction * size)) # Tip
    v2 = bm.verts.new(position + (right * width * 0.5) + (direction * size * 0.4))
    v3 = bm.verts.new(position + (right * -width * 0.5) + (direction * size * 0.4))
    
    try:
        bm.faces.new((v0, v2, v1, v3))
    except:
        pass

def create_branch_segment(bm, start_pos, direction, length, radius, depth):
    """Recursively creates the twig structure."""
    if depth < 0 or radius < 0.002:
        return start_pos

    # Break branch into smaller segments for curvature
    num_segments = 5
    seg_len = length / num_segments
    curr_pos = Vector(start_pos)
    curr_dir = Vector(direction).normalized()
    
    for i in range(num_segments):
        # Add organic jitter
        jitter = Vector((random.uniform(-0.15, 0.15), 
                         random.uniform(-0.15, 0.15), 
                         random.uniform(-0.15, 0.15)))
        curr_dir = (curr_dir + jitter).normalized()
        next_pos = curr_pos + curr_dir * seg_len
        
        # Create cylinder segment
        res = 6
        ring1 = []
        ring2 = []
        
        # Perpendicular vectors for the cross-section
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
        
        # Occasional leaf along the stem
        if random.random() < 0.15:
            create_leaf(bm, curr_pos, (right * random.uniform(-1,1) + up * random.uniform(-1,1)).normalized())

        curr_pos = next_pos

    # Create side offshoots at the end or middle of this branch
    if depth > 0:
        num_offshoots = random.randint(1, 2)
        for _ in range(num_offshoots):
            # Offshoot direction is a mix of current dir and random
            off_dir = (curr_dir + Vector((random.uniform(-1, 1), 
                                          random.uniform(-1, 1), 
                                          random.uniform(-1, 1)))).normalized()
            create_branch_segment(bm, curr_pos, off_dir, length * 0.6, radius * 0.7, depth - 1)

    # Final leaf at the tip
    if random.random() < 0.5:
        create_leaf(bm, curr_pos, curr_dir)

    return curr_pos

def main():
    clear_scene()

    mesh = bpy.data.meshes.new("Twig")
    obj = bpy.data.objects.new("Twig", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # Root parameters for a "small thin twig"
    start_pos = Vector((0, 0, 0))
    main_dir = Vector((0.2, 0.1, 1)).normalized()
    length = 1.5
    radius = 0.012
    depth = 2

    create_branch_segment(bm, start_pos, main_dir, length, radius, depth)

    bm.to_mesh(mesh)
    bm.free()

    # Smoothing and Organic feel
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    
    # Center the object roughly
    obj.location = (0, 0, -0.5)

if __name__ == "__main__":
    main()
