import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_rotten_segment(bm, start, end, radius_start, radius_end, segments=12, resolution=8):
    """Creates a gnarled segment of wood between two points."""
    prev_verts = []
    direction = (end - start).normalized()
    dist = (end - start).length
    
    for i in range(resolution + 1):
        t = i / resolution
        curr_center = start + direction * (dist * t)
        
        # Add organic noise to the center point for gnarled effect
        jitter = Vector((random.uniform(-0.05, 0.05), 
                        random.uniform(-0.05, 0.05), 
                        random.uniform(-0.05, 0.05))) * (1.0 - t)
        curr_center += jitter
        
        r = radius_start + (radius_end - radius_start) * t
        # Vary radius for organic look
        r *= random.uniform(0.8, 1.2)
        
        ring_verts = []
        for s in range(segments):
            angle = (2 * math.pi / segments) * s
            offset = random.uniform(0.9, 1.1)
            v = Vector((math.cos(angle) * r * offset, math.sin(angle) * r * offset, 0))
            
            if abs(direction.z) < 0.9:
                up = Vector((0, 0, 1))
            else:
                up = Vector((0, 1, 0))
            
            right = direction.cross(up).normalized()
            actual_up = right.cross(direction).normalized()
            
            world_v = curr_center + (right * v.x) + (actual_up * v.y)
            ring_verts.append(bm.verts.new(world_v))
        
        if prev_verts:
            for s in range(segments):
                v1 = prev_verts[s]
                v2 = ring_verts[s]
                v3 = ring_verts[(s + 1) % segments]
                v4 = prev_verts[(s + 1) % segments]
                bm.faces.new((v1, v2, v3, v4))
        
        prev_verts = ring_verts

    return prev_verts

def generate_branch(bm, start_pos, direction, length, radius, depth):
    """Recursive function to create a branching structure."""
    if depth <= 0 or radius < 0.01:
        return
    
    # Add curvature to the growth path
    curvature = Vector((random.uniform(-0.2, 0.2), 
                       random.uniform(-0.2, 0.2), 
                       random.uniform(-0.2, 0.2))) * length
    end_pos = start_pos + (direction * length) + curvature
    
    res = 6 if depth > 1 else 3
    segs = 8 if depth > 1 else 6
    last_ring = create_rotten_segment(bm, start_pos, end_pos, radius, radius * 0.7, segments=segs, resolution=res)
    
    # Determine branching points
    num_branches = random.randint(1, 2) if depth > 1 else random.randint(0, 1)
    final_center = (sum((v.co for v in last_ring), Vector((0,0,0))) / len(last_ring))
    
    for _ in range(num_branches):
        # Randomize branch direction relative to current growth
        branch_dir = (direction + Vector((random.uniform(-0.7, 0.7), 
                                          random.uniform(-0.7, 0.7), 
                                          random.uniform(-0.4, 0.4)))).normalized()
        child_len = length * random.uniform(0.5, 0.8)
        child_rad = radius * random.uniform(0.4, 0.6)
        generate_branch(bm, final_center, branch_dir, child_len, child_rad, depth - 1)

def main():
    clear_scene()
    
    bm = bmesh.new()
    
    # Trunk settings
    trunk_start = Vector((0, 0, 0))
    trunk_end = Vector((0, 0, 1.2)) # Short trunk as requested
    trunk_radius = 0.35
    
    # Create main rotting trunk
    last_ring = create_rotten_segment(bm, trunk_start, trunk_end, trunk_radius * 1.4, trunk_radius, segments=20, resolution=12)
    trunk_top = (sum((v.co for v in last_ring), Vector((0,0,0))) / len(last_ring))
    
    # Create the distinctive "pitchfork" silhouette: two main primary branches nearly vertical
    dir1 = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 1.0)).normalized()
    generate_branch(bm, trunk_top, dir1, 2.5, trunk_radius * 0.7, depth=3)
    
    dir2 = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 1.0)).normalized()
    generate_branch(bm, trunk_top, dir2, 2.5, trunk_radius * 0.7, depth=3)

    # Add side-branches on the lower trunk for more organic/decayed look
    for i in range(5):
        h = random.uniform(0.1, 1.1)
        pos = Vector((random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), h))
        dir_side = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.3, 0.7))).normalized()
        generate_branch(bm, pos, dir_side, random.uniform(0.4, 1.0), trunk_radius * 0.4, depth=2)

    # Geometrically simulate "decay" and "fissures" by perturbing vertices
    for v in bm.verts:
        if v.co.z > 0.05:
            # Create deep fissures via occasional large spikes combined with small noise
            if random.random() < 0.15:
                noise_val = random.uniform(-0.1, 0.1)
                v.co += Vector((noise_val, noise_val, noise_val))
            else:
                noise_val = random.uniform(-0.03, 0.03)
                v.co += Vector((noise_val, noise_val, noise_val))

    # Create mesh and object
    mesh = bpy.data.meshes.new("RottenTreeMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("RottenTree", mesh)
    bpy.context.collection.objects.link(obj)
    bm.free()

    # Subdiv to smooth the organic shapes while keeping the general silhouette
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    subsurf.render_levels = 1

    # Final shading settings
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    main()
