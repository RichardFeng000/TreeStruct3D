import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_gnarled_segment(bm, start, end, radius_start, radius_end, segments=12, resolution=8):
    """Creates a rugged wood segment."""
    prev_verts = []
    direction = (end - start).normalized()
    dist = (end - start).length
    
    for i in range(resolution + 1):
        t = i / resolution
        curr_center = start + direction * (dist * t)
        
        # Add organic noise to the path
        jitter = Vector((random.uniform(-0.04, 0.04), 
                        random.uniform(-0.04, 0.04), 
                        random.uniform(-0.04, 0.04))) * (1.0 - t)
        curr_center += jitter
        
        r = radius_start + (radius_end - radius_start) * t
        # Radius variation for rotting wood look
        r *= random.uniform(0.85, 1.15)
        
        ring_verts = []
        for s in range(segments):
            angle = (2 * math.pi / segments) * s
            # Create "fissures" by varying the radius significantly per segment
            offset = random.uniform(0.7, 1.3) if random.random() > 0.6 else random.uniform(0.9, 1.1)
            v_local = Vector((math.cos(angle) * r * offset, math.sin(angle) * r * offset, 0))
            
            if abs(direction.z) < 0.9:
                up = Vector((0, 0, 1))
            else:
                up = Vector((0, 1, 0))
            
            right = direction.cross(up).normalized()
            actual_up = right.cross(direction).normalized()
            world_v = curr_center + (right * v_local.x) + (actual_up * v_local.y)
            ring_verts.append(bm.verts.new(world_v))
        
        if prev_verts:
            for s in range(segments):
                bm.faces.new((prev_verts[s], ring_verts[s], ring_verts[(s + 1) % segments], prev_verts[(s + 1) % segments]))
        
        prev_verts = ring_verts

    return prev_verts

def generate_branch(bm, start_pos, direction, length, radius, depth):
    """Recursive function to create a detailed branching structure."""
    if depth <= 0 or radius < 0.015:
        return
    
    # More curved growth for weathered look
    curvature = Vector((random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1))) * length
    end_pos = start_pos + (direction * length) + curvature
    
    res = 5 if depth > 1 else 3
    segs = 8 if depth > 1 else 6
    last_ring = create_gnarled_segment(bm, start_pos, end_pos, radius, radius * 0.6, segments=segs, resolution=res)
    
    # Increase branching density for "fine twigs" in later stages
    num_branches = random.randint(2, 3) if depth == 1 else random.randint(1, 2)
    final_center = (sum((v.co for v in last_ring), Vector((0,0,0))) / len(last_ring))
    
    for _ in range(num_branches):
        # Narrow the spread as depth increases to keep structure tight
        spread = 0.8 if depth > 1 else 0.5
        branch_dir = (direction + Vector((random.uniform(-spread, spread), 
                                          random.uniform(-spread, spread), 
                                          random.uniform(-spread * 0.5, spread * 0.5)))).normalized()
        child_len = length * random.uniform(0.4, 0.7)
        child_rad = radius * random.uniform(0.4, 0.6)
        generate_branch(bm, final_center, branch_dir, child_len, child_rad, depth - 1)

def main():
    clear_scene()
    
    bm = bmesh.new()
    
    # Trunk setup
    trunk_start = Vector((0, 0, 0))
    trunk_end = Vector((0, 0, 1.2)) # Short trunk
    trunk_radius = 0.35
    
    # Main decaying trunk
    last_ring = create_gnarled_segment(bm, trunk_start, trunk_end, trunk_radius * 1.4, trunk_radius, segments=20, resolution=15)
    trunk_top = (sum((v.co for v in last_ring), Vector((0,0,0))) / len(last_ring))
    
    # Pitchfork silhouette: Two main primary branches nearly vertical
    # Use small X/Y offsets to keep them "nearly vertical"
    dir1 = Vector((random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), 1.0)).normalized()
    generate_branch(bm, trunk_top, dir1, 2.8, trunk_radius * 0.7, depth=4)
    
    dir2 = Vector((random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), 1.0)).normalized()
    generate_branch(bm, trunk_top, dir2, 2.8, trunk_radius * 0.7, depth=4)

    # Side-branches on the lower trunk for decay look
    for i in range(6):
        h = random.uniform(0.1, 1.1)
        pos = Vector((random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), h))
        dir_side = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.2, 0.6))).normalized()
        generate_branch(bm, pos, dir_side, random.uniform(0.3, 0.8), trunk_radius * 0.3, depth=2)

    # Post-process for deep fissures: perturb vertices based on a pseudo-random "bark" pattern
    for v in bm.verts:
        noise = (math.sin(v.co.x * 10) * math.cos(v.co.z * 10)) * 0.05
        v.co += Vector((noise, noise, noise))
        if random.random() < 0.05:
            v.co += Vector((random.uniform(-0.08, 0.08), random.uniform(-0.08, 0.08), 0))

    mesh = bpy.data.meshes.new("RottenTreeMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("RottenTree", mesh)
    bpy.context.collection.objects.link(obj)
    bm.free()

    # Subdiv for organic blend, but low level to keep rough edges
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    # Material for dark brown-black rotten wood
    mat = bpy.data.materials.new(name="RottenWoodMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Mottled brown-black color (dark charcoal / deep chocolate)
        bsdf.inputs['Base Color'].default_value = (0.05, 0.03, 0.02, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.9

    obj.data.materials.append(mat)

if __name__ == "__main__":
    main()
