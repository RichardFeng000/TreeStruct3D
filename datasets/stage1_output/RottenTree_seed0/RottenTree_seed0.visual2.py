import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_gnarled_segment(bm, start, end, radius_start, radius_end, segments=12, resolution=8):
    """Creates a rugged wood segment with high geometric variance for fissures."""
    prev_verts = []
    direction = (end - start).normalized()
    dist = (end - start).length
    
    for i in range(resolution + 1):
        t = i / resolution
        # Add organic noise to the centerline path
        jitter = Vector((random.uniform(-0.05, 0.05), 
                        random.uniform(-0.05, 0.05), 
                        random.uniform(-0.05, 0.05))) * (1.0 - t)
        curr_center = start + direction * (dist * t) + jitter
        
        r = radius_start + (radius_end - radius_start) * t
        # Simulate rotting decay by varying the base ring radius
        r *= random.uniform(0.8, 1.2)
        
        ring_verts = []
        for s in range(segments):
            angle = (2 * math.pi / segments) * s
            # Deeply fissured look: High variance in vertex distance from center
            fissure_factor = random.uniform(0.6, 1.4) if random.random() > 0.4 else random.uniform(0.9, 1.1)
            v_local = Vector((math.cos(angle) * r * fissure_factor, math.sin(angle) * r * fissure_factor, 0))
            
            # Calculate orientation based on segment direction
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
                try:
                    bm.faces.new((prev_verts[s], ring_verts[s], ring_verts[(s + 1) % segments], prev_verts[(s + 1) % segments]))
                except ValueError:
                    pass # Avoid duplicate faces from degenerate geometry
        
        prev_verts = ring_verts

    return prev_verts

def generate_branch(bm, start_pos, direction, length, radius, depth):
    """Recursive function to create a dense network of twigs."""
    if depth <= 0 or radius < 0.01:
        return
    
    # Weathered curvature
    curv = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2))) * length
    end_pos = start_pos + (direction * length) + curv
    
    # Adjust resolution by depth to keep file size manageable but detail high at ends
    res = 6 if depth > 1 else 3
    segs = 8 if depth > 2 else 6
    last_ring = create_gnarled_segment(bm, start_pos, end_pos, radius, radius * 0.65, segments=segs, resolution=res)
    
    if not last_ring: return

    # Branching density increases as we move to twigs
    num_branches = random.randint(2, 3) if depth > 1 else random.randint(1, 2)
    final_center = (sum((v.co for v in last_ring), Vector((0,0,0))) / len(last_ring))
    
    for _ in range(num_branches):
        spread = 0.7 if depth > 1 else 0.4
        branch_dir = (direction + Vector((random.uniform(-spread, spread), 
                                          random.uniform(-spread, spread), 
                                          random.uniform(-spread * 0.5, spread * 0.5)))).normalized()
        child_len = length * random.uniform(0.5, 0.8)
        child_rad = radius * random.uniform(0.4, 0.6)
        generate_branch(bm, final_center, branch_dir, child_len, child_rad, depth - 1)

def main():
    clear_scene()
    
    bm = bmesh.new()
    
    # Trunk setup: short and thick
    trunk_start = Vector((0, 0, 0))
    trunk_end = Vector((0, 0, 1.1)) 
    trunk_radius = 0.35
    
    # Create main trunk with heavy decay noise
    last_ring = create_gnarled_segment(bm, trunk_start, trunk_end, trunk_radius * 1.5, trunk_radius, segments=24, resolution=16)
    trunk_top = (sum((v.co for v in last_ring), Vector((0,0,0))) / len(last_ring))
    
    # PITCHFORK SILHOUETTE: Two distinct primary branches shooting nearly vertically but diverging
    # Branch 1 - Slightly left/forward
    dir1 = Vector((-0.15, 0.1, 1.0)).normalized()
    generate_branch(bm, trunk_top, dir1, 2.5, trunk_radius * 0.7, depth=4)
    
    # Branch 2 - Slightly right/backward
    dir2 = Vector((0.15, -0.1, 1.0)).normalized()
    generate_branch(bm, trunk_top, dir2, 2.5, trunk_radius * 0.7, depth=4)

    # Additional decay branches on the main trunk (stumps/broken bits)
    for i in range(8):
        h = random.uniform(0.1, 1.0)
        pos = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), h))
        dir_side = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.3, 0.5))).normalized()
        generate_branch(bm, pos, dir_side, random.uniform(0.2, 0.6), trunk_radius * 0.3, depth=2)

    # Post-process: Aggressive vertex displacement for deep fissures/bark roughness
    for v in bm.verts:
        # Multi-scale noise for organic feel
        noise = (math.sin(v.co.x * 8) * math.cos(v.co.z * 8)) * 0.06
        noise += (math.sin(v.co.y * 20) * math.cos(v.co.x * 20)) * 0.03
        v.co += Vector((noise, noise, noise))
        if random.random() < 0.1: # Random spikes/chips in the wood
            v.co += Vector((random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)))

    mesh = bpy.data.meshes.new("RottenTreeMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("RottenTree", mesh)
    bpy.context.collection.objects.link(obj)
    bm.free()

    # Use a very low level subsurf or none to keep the jagged "rotted" edges
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    
    bpy.context.view_layer.objects.active = obj
    # Shade smooth but high geometry ensures it doesn't look like a blob
    bpy.ops.object.shade_smooth()

    # Material: Dark brown-black mottled wood
    mat = bpy.data.materials.new(name="RottenWoodMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Deep charcoal / dark rotten wood brown
        bsdf.inputs['Base Color'].default_value = (0.03, 0.02, 0.015, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.95
        bsdf.inputs['Specular IOR Level'].default_value = 0.1

    obj.data.materials.append(mat)

if __name__ == "__main__":
    main()
