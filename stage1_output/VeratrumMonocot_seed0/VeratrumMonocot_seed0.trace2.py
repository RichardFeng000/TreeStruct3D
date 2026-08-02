import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    if "Cube" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
    if "Camera" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Camera"], do_unlink=True)
    if "Light" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Light"], do_unlink=True)
    # Clear all other objects just in case
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_leaf(name, angle_deg, scale=1.0, material=None):
    """Creates a broad, plicate (ribbed) Veratrum leaf."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    
    # Leaf parameters
    res_l = 32 # length resolution
    res_w = 24 # width resolution
    leaf_len = 4.0 * scale
    leaf_max_w = 1.2 * scale
    num_ribs = 7

    verts = []
    for i in range(res_l + 1):
        t = i / res_l # 0 to 1
        
        # Width profile: narrow at base, widest in middle/upper-middle, tapered tip
        w_factor = math.sin(math.pi * t**0.7) if t > 0 else 0
        current_half_width = (leaf_max_w * 0.5) * w_factor
        
        # Leaf arching/drooping
        z_bend = -1.2 * (t**2) * scale
        y_offset = t * leaf_len
        
        row = []
        for j in range(res_w + 1):
            u = (j / res_w) - 0.5 # -0.5 to 0.5
            
            # Plicate effect: ribs along the length
            rib_offset = 0.12 * math.sin(u * math.pi * num_ribs) * scale
            x_pos = u * 2.0 * current_half_width
            v = bm.verts.new(Vector((x_pos, y_offset, z_bend + rib_offset)))
            row.append(v)
        verts.append(row)

    for i in range(res_l):
        for j in range(res_w):
            bm.faces.new((
                verts[i][j],
                verts[i+1][j],
                verts[i+1][j+1],
                verts[i][j+1]
            ))

    # Smooth shading
    for f in bm.faces:
        f.smooth = True

    bm.to_mesh(mesh)
    bm.free()

    # Transform leaf
    obj.rotation_euler[2] = math.radians(angle_deg)
    # Tilt outward and slightly up from the center
    obj.rotation_euler[0] = math.radians(-10 + random.uniform(-5, 5))
    obj.rotation_euler[1] = math.radians(15 + random.uniform(-5, 5))
    
    if material:
        obj.data.materials.append(material)
    return obj

def create_stalk_mesh(name, points, radius, material):
    """Creates a stalk mesh by lofting circles along the provided points."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    res = 8
    
    prev_ring = []
    for i, p in enumerate(points):
        t = i / len(points)
        current_r = radius * (1.0 - 0.5 * t) # taper towards top
        
        ring = []
        # Determine orientation for the ring
        if i < len(points) - 1:
            dir_vec = (points[i+1] - p).normalized()
        else:
            dir_vec = (p - points[i-1]).normalized()
        
        # Orthonormal basis
        up = Vector((0, 0, 1)) if abs(dir_vec.z) < 0.9 else Vector((0, 1, 0))
        right = dir_vec.cross(up).normalized()
        top = dir_vec.cross(right).normalized()
        
        for j in range(res):
            angle = (2 * math.pi * j) / res
            offset = (right * math.cos(angle) * current_r) + (top * math.sin(angle) * current_r)
            v = bm.verts.new(p + offset)
            ring.append(v)
        
        if prev_ring:
            for j in range(res):
                bm.faces.new((
                    prev_ring[j], 
                    prev_ring[(j+1)%res], 
                    ring[(j+1)%res], 
                    ring[j]
                ))
        prev_ring = ring

    bm.faces.new(prev_ring[::-1])
    for f in bm.faces:
        f.smooth = True

    bm.to_mesh(mesh)
    bm.free()
    
    if material:
        obj.data.materials.append(material)
    return obj

def create_floret(pos, material):
    """Creates a single small floret using BMesh."""
    mesh = bpy.data.meshes.new("Floret")
    obj = bpy.data.objects.new("Floret", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.07)
    for v in bm.verts:
        v.co += pos
        
    bm.to_mesh(mesh)
    bm.free()

    if material:
        obj.data.materials.append(material)
    return obj

def main():
    clear_scene()

    # Muted colors
    leaf_mat = create_material("LeafMat", (0.1, 0.2, 0.08, 1.0))
    stalk_mat = create_material("StalkMat", (0.15, 0.25, 0.1, 1.0))
    floret_mat = create_material("FloretMat", (0.4, 0.45, 0.2, 1.0))

    # Basal Leaves - arranged in a circle at the base
    num_leaves = 14
    for i in range(num_leaves):
        angle = (360 / num_leaves) * i
        scale = random.uniform(0.8, 1.2)
        create_leaf(f"Leaf_{i}", angle, scale, leaf_mat)

    # Flower stalk: an arching curve
    # Points define the path of the flower stalk
    stalk_ctrl = [
        Vector((0, 0, 0)),
        Vector((0.2, 0.4, 1.8)),
        Vector((0.6, 1.2, 3.5)),
        Vector((1.2, 2.5, 5.5)),
        Vector((1.8, 4.0, 7.0))
    ]
    
    # Linear interpolation for a smooth path
    smooth_points = []
    segments_per_ctrl = 6
    for i in range(len(stalk_ctrl) - 1):
        p1 = stalk_ctrl[i]
        p2 = stalk_ctrl[i+1]
        for j in range(segments_per_ctrl):
            t = j / segments_per_ctrl
            smooth_points.append(p1 + (p2 - p1) * t)
    smooth_points.append(stalk_ctrl[-1])

    create_stalk_mesh("Stalk", smooth_points, 0.1, stalk_mat)

    # Raceme: small clustered florets along the top part of the stalk
    # Start from ~40% height to the tip
    start_idx = int(len(smooth_points) * 0.4)
    for i in range(start_idx, len(smooth_points)):
        pos = smooth_points[i]
        # Randomly determine how many florets at this segment
        if random.random() > 0.3:
            num_in_cluster = random.randint(2, 5)
            for _ in range(num_in_cluster):
                offset = Vector((
                    random.uniform(-0.2, 0.2),
                    random.uniform(-0.2, 0.2),
                    random.uniform(-0.1, 0.1)
                ))
                create_floret(pos + offset, floret_mat)

if __name__ == "__main__":
    main()
