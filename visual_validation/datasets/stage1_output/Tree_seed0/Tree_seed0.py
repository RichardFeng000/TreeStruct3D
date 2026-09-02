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

def build_branch(bm, start_pos, end_pos, radius_start, radius_end, divisions=4, segments_per_ring=8):
    """Adds a branch to the provided BMesh using bridged rings for connectivity."""
    points = []
    prev_p = start_pos
    full_vec = end_pos - start_pos
    seg_vec = full_vec / divisions
    
    for i in range(divisions):
        jitter = Vector((random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)))
        p = start_pos + seg_vec * (i + 1) + jitter if i < divisions - 1 else end_pos
        points.append(p)
    
    # Generate rings at each point including the start
    all_points = [start_pos] + points
    radii = [radius_start + (radius_end - radius_start) * (i / divisions) for i in range(divisions + 1)]
    
    rings = []
    for i, p in enumerate(all_points):
        r = radii[i]
        ring_verts = []
        # Create a consistent orientation basis
        dir_vec = Vector((0, 0, 1)) if i == 0 else (all_points[i] - all_points[i-1]).normalized()
        ortho = Vector((0, 1, 0)) if abs(dir_vec.dot(Vector((0, 0, 1)))) < 0.9 else Vector((1, 0, 0))
        right = dir_vec.cross(ortho).normalized()
        up = dir_vec.cross(right).normalized()
        
        for j in range(segments_per_ring):
            angle = (2 * math.pi / segments_per_ring) * j
            offset = (right * math.cos(angle) + up * math.sin(angle)) * r
            ring_verts.append(bm.verts.new((p + offset)))
        rings.append(ring_verts)

    # Bridge rings with faces
    for i in range(len(rings) - 1):
        r1 = rings[i]
        r2 = rings[i+1]
        for j in range(segments_per_ring):
            v1 = r1[j]
            v2 = r1[(j + 1) % segments_per_ring]
            v3 = r2[(j + 1) % segments_per_ring]
            v4 = r2[j]
            bm.faces.new((v1, v2, v3, v4))
            
    return all_points[-1], rings[-1]

def create_leaf_mesh():
    bm = bmesh.new()
    # Simple leaf shape (diamond)
    v1 = bm.verts.new((0, 0, 0))
    v2 = bm.verts.new((0, 0.3, 0))
    v3 = bm.verts.new((0.15, 0.15, 0))
    v4 = bm.verts.new((-0.15, 0.15, 0))
    bm.faces.new((v1, v3, v2, v4))
    mesh = bpy.data.meshes.new("LeafMesh")
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def create_flower_mesh():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=6, radius=0.07)
    mesh = bpy.data.meshes.new("FlowerMesh")
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def generate_tree():
    clear_scene()

    # Materials
    brown_mat = create_material("Brown", (0.12, 0.06, 0.03, 1.0))
    green_mat = create_material("Green", (0.08, 0.3, 0.05, 1.0))
    pink_mat = create_material("Pink", (0.95, 0.45, 0.6, 1.0))

    # Create skeleton in one BMesh for connectivity
    skeleton_bm = bmesh.new()
    
    # Trunk: short and thick
    trunk_start = Vector((0, 0, 0))
    trunk_end = Vector((0, 0, 1.1))
    last_p, _ = build_branch(skeleton_bm, trunk_start, trunk_end, 0.5, 0.35, divisions=3)

    # Primary Branches
    num_primary = 6
    primary_endpoints = []
    for i in range(num_primary):
        angle_z = (2 * math.pi / num_primary) * i
        spread_angle = random.uniform(0.7, 1.2) # Outward spread for top-down look
        direction = Vector((math.cos(angle_z) * math.sin(spread_angle), 
                           math.sin(angle_z) * math.sin(spread_angle), 
                           math.cos(spread_angle)))
        end = trunk_end + direction * random.uniform(1.8, 2.5)
        ep, _ = build_branch(skeleton_bm, trunk_end, end, 0.35, 0.15, divisions=4)
        primary_endpoints.append(ep)

    # Secondary Branches
    secondary_endpoints = []
    for ep in primary_endpoints:
        for j in range(random.randint(3, 5)):
            direction = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.4, 1))).normalized()
            end = ep + direction * random.uniform(0.8, 1.6)
            sep, _ = build_branch(skeleton_bm, ep, end, 0.15, 0.06, divisions=3)
            secondary_endpoints.append(sep)

    # Finalize skeleton mesh
    skeleton_mesh = bpy.data.meshes.new("TreeSkeleton")
    skeleton_bm.to_mesh(skeleton_mesh)
    skeleton_bm.free()
    skeleton_obj = bpy.data.objects.new("TreeSkeleton", skeleton_mesh)
    bpy.context.collection.objects.link(skeleton_obj)
    skeleton_obj.data.materials.append(brown_mat)

    # Foliage instancing
    leaf_mesh = create_leaf_mesh()
    flower_mesh = create_flower_mesh()

    for ep in secondary_endpoints:
        # Denser leaf clusters for a "broad" look
        num_leaves = random.randint(20, 35)
        for _ in range(num_leaves):
            offset = Vector((random.uniform(-0.6, 0.6), 
                            random.uniform(-0.6, 0.6), 
                            random.uniform(-0.6, 0.6)))
            rot = Euler((random.uniform(0, 6.28), random.uniform(0, 6.28), random.uniform(0, 6.28)))
            leaf_obj = bpy.data.objects.new("Leaf", leaf_mesh)
            bpy.context.collection.objects.link(leaf_obj)
            leaf_obj.location = ep + offset
            leaf_obj.rotation_euler = rot
            leaf_obj.data.materials.append(green_mat)

        # Flower clusters
        if random.random() < 0.6:
            cluster_center = ep + Vector((0, 0, 0.1))
            for _ in range(random.randint(4, 8)):
                offset = Vector((random.uniform(-0.2, 0.2), 
                                random.uniform(-0.2, 0.2), 
                                random.uniform(-0.2, 0.2)))
                flower_obj = bpy.data.objects.new("Flower", flower_mesh)
                bpy.context.collection.objects.link(flower_obj)
                flower_obj.location = cluster_center + offset
                flower_obj.data.materials.append(pink_mat)

if __name__ == "__main__":
    generate_tree()
