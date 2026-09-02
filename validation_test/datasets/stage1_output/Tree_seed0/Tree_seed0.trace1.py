import bpy
import bmesh
import random
import math
from mathutils import Vector, Euler

def clear_scene():
    """Clear default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Create a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_branch_segment(name, start_pos, end_pos, radius_start, radius_end, segments=8, material=None):
    """Creates a single cylindrical segment of a branch."""
    bm = bmesh.new()
    
    dir_vec = (end_pos - start_pos).normalized()
    # Calculate orientation for the ring
    ortho_vec = Vector((0, 1, 0)) if abs(dir_vec.dot(Vector((0, 0, 1)))) < 0.9 else Vector((1, 0, 0))
    right = dir_vec.cross(ortho_vec).normalized()
    up = dir_vec.cross(right).normalized()

    verts_start = []
    verts_end = []

    for i in range(segments):
        angle = (2 * math.pi / segments) * i
        offset = (right * math.cos(angle) + up * math.sin(angle)) * radius_start
        verts_start.append(bm.verts.new((start_pos + offset)))

    for i in range(segments):
        angle = (2 * math.pi / segments) * i
        offset = (right * math.cos(angle) + up * math.sin(angle)) * radius_end
        verts_end.append(bm.verts.new((end_pos + offset)))

    for i in range(segments):
        v1 = verts_start[i]
        v2 = verts_start[(i + 1) % segments]
        v3 = verts_end[(i + 1) % segments]
        v4 = verts_end[i]
        bm.faces.new((v1, v2, v3, v4))

    # Caps
    bm.faces.new(verts_start)
    bm.faces.new(verts_end)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if material:
        obj.data.materials.append(material)
    return obj

def create_gnarled_path(name, start_pos, end_pos, radius_start, radius_end, divisions=4, segments_per_ring=8, material=None):
    """Creates a path of branch segments with random jitter for a gnarled look."""
    current_pos = Vector(start_pos)
    full_vec = end_pos - start_pos
    seg_vec = full_vec / divisions
    
    last_obj = None
    for i in range(divisions):
        # Add random jitter to the target point of this segment
        jitter = Vector((random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15)))
        target_pos = start_pos + seg_vec * (i + 1) + jitter
        if i == divisions - 1:
            target_pos = end_pos # Ensure it ends exactly at the target

        r_start = radius_start - (radius_start - radius_end) * (i / divisions)
        r_end = radius_start - (radius_start - radius_end) * ((i + 1) / divisions)
        
        seg_obj = create_branch_segment(f"{name}_{i}", current_pos, target_pos, r_start, r_end, segments_per_ring, material)
        current_pos = target_pos
        last_obj = seg_obj
    return current_pos

def create_leaf_mesh(material):
    """Creates a single leaf mesh to be instanced."""
    bm = bmesh.new()
    v1 = bm.verts.new((0, 0, 0))
    v2 = bm.verts.new((0, 0.3, 0))
    v3 = bm.verts.new((0.15, 0.15, 0))
    v4 = bm.verts.new((-0.15, 0.15, 0))
    bm.faces.new((v1, v3, v2, v4))
    
    mesh = bpy.data.meshes.new("LeafMesh")
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def create_flower_mesh(material):
    """Creates a single flower sphere to be instanced."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=8, radius=0.06)
    
    mesh = bpy.data.meshes.new("FlowerMesh")
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def generate_tree():
    clear_scene()

    # Materials
    brown_mat = create_material("Brown", (0.15, 0.08, 0.04, 1.0))
    green_mat = create_material("Green", (0.1, 0.35, 0.1, 1.0))
    pink_mat = create_material("Pink", (0.9, 0.4, 0.6, 1.0))

    # Trunk: short and thick
    trunk_start = Vector((0, 0, 0))
    trunk_end = Vector((0, 0, 1.2))
    create_gnarled_path("Trunk", trunk_start, trunk_end, 0.6, 0.4, divisions=3, material=brown_mat)

    # Primary Branches - spreading outwards for the top-down view
    num_primary = 7
    primary_endpoints = []
    for i in range(num_primary):
        start = trunk_end
        angle_z = (2 * math.pi / num_primary) * i
        # Strong spread to X/Y plane for top-down visibility
        spread_angle = random.uniform(0.6, 1.3) 
        dir = Vector((math.cos(angle_z) * math.sin(spread_angle), 
                     math.sin(angle_z) * math.sin(spread_angle), 
                     math.cos(spread_angle)))
        
        end = start + dir * random.uniform(1.8, 2.6)
        ep = create_gnarled_path(f"Primary_{i}", start, end, 0.4, 0.2, divisions=3, material=brown_mat)
        primary_endpoints.append(ep)

    # Secondary Branches - filling the canopy volume
    secondary_endpoints = []
    for ep in primary_endpoints:
        for j in range(random.randint(2, 4)):
            start = ep
            dir = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.5, 1))).normalized()
            end = start + dir * random.uniform(0.7, 1.4)
            sep = create_gnarled_path(f"Secondary_{j}", start, end, 0.2, 0.08, divisions=2, material=brown_mat)
            secondary_endpoints.append(sep)

    # Create base meshes for instancing (performance optimization)
    leaf_mesh = create_leaf_mesh(green_mat)
    flower_mesh = create_flower_mesh(pink_mat)

    # Canopy: Leaves and Flowers distributed around endpoints
    for ep in secondary_endpoints:
        # Leaves cloud
        num_leaves = random.randint(12, 25)
        for _ in range(num_leaves):
            offset = Vector((random.uniform(-0.7, 0.7), 
                            random.uniform(-0.7, 0.7), 
                            random.uniform(-0.7, 0.7)))
            rot = Euler((random.uniform(0, 6.28), random.uniform(0, 6.28), random.uniform(0, 6.28)))
            
            leaf_obj = bpy.data.objects.new("Leaf", leaf_mesh)
            bpy.context.collection.objects.link(leaf_obj)
            leaf_obj.location = ep + offset
            leaf_obj.rotation_euler = rot
            leaf_obj.data.materials.append(green_mat)

        # Flower clusters (small groups of spheres)
        if random.random() < 0.5:
            cluster_center = ep + Vector((0,0,0.1))
            for _ in range(random.randint(3, 6)):
                offset = Vector((random.uniform(-0.15, 0.15), 
                                random.uniform(-0.15, 0.15), 
                                random.uniform(-0.15, 0.15)))
                flower_obj = bpy.data.objects.new("Flower", flower_mesh)
                bpy.context.collection.objects.link(flower_obj)
                flower_obj.location = cluster_center + offset
                flower_obj.data.materials.append(pink_mat)

if __name__ == "__main__":
    generate_tree()
