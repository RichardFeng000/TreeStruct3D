import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Base Color'].default_value = color
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def build_tube(name, points, radius, material):
    """Creates a mesh tube following a sequence of points."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    res = 8
    prev_ring = []
    for i in range(len(points)):
        p = points[i]
        if i < len(points) - 1:
            dir_vec = (points[i+1] - p).normalized()
        elif i > 0:
            dir_vec = (p - points[i-1]).normalized()
        else:
            dir_vec = Vector((0, 0, 1))
        
        up = Vector((0, 0, 1)) if abs(dir_vec.z) < 0.9 else Vector((0, 1, 0))
        right = dir_vec.cross(up).normalized()
        forward = dir_vec.cross(right).normalized()
        
        ring = []
        for j in range(res):
            angle = (2 * math.pi / res) * j
            v_pos = p + (right * math.cos(angle) + forward * math.sin(angle)) * radius
            ring.append(bm.verts.new(v_pos))
        
        if prev_ring:
            for j in range(res):
                bm.faces.new((prev_ring[j], prev_ring[(j+1)%res], ring[(j+1)%res], ring[j]))
        prev_ring = ring
    
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(material)
    return obj

def create_organic_leaf(pos, direction, scale, material):
    """Creates a more organic broad leaf shape."""
    mesh = bpy.data.meshes.new("Leaf")
    obj = bpy.data.objects.new("Leaf", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    
    # Create a grid-based leaf shape
    res_u, res_v = 6, 6
    verts = []
    for i in range(res_u):
        row = []
        u = i / (res_u - 1)
        for j in range(res_v):
            v = (j - (res_v - 1) / 2) / ((res_v - 1) / 2)
            # Leaf shape: tapered at ends, wide in middle
            width = math.sin(u * math.pi) * 0.5 * (1.0 - abs(v)*0.5)
            x = u * 2.0 - 1.0 # length from -1 to 1
            y = v * width
            z = math.cos(u * math.pi) * 0.1 # Slight curve
            row.append(bm.verts.new(Vector((x, y, z))))
        verts.append(row)
    
    for i in range(res_u - 1):
        for j in range(res_v - 1):
            bm.faces.new((verts[i][j], verts[i+1][j], verts[i+1][j+1], verts[i][j+1]))

    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = pos
    z_axis = direction.normalized()
    up = Vector((0, 0, 1)) if abs(z_axis.dot(Vector((0, 0, 1)))) < 0.9 else Vector((0, 1, 0))
    x_axis = z_axis
    y_axis = x_axis.cross(up).normalized()
    z_axis_final = y_axis.cross(x_axis).normalized()
    rot_mat = Matrix((x_axis, y_axis, z_axis_final)).transposed()
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = rot_mat.to_quaternion()
    obj.scale = scale
    obj.data.materials.append(material)
    return obj

def create_flower(pos, material_white):
    """Creates a flower bloom with center and petals."""
    # Center
    mesh_center = bpy.data.meshes.new("FlowerCenter")
    obj_center = bpy.data.objects.new("FlowerCenter", mesh_center)
    bpy.context.collection.objects.link(obj_center)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=8, radius=0.08)
    bm.to_mesh(mesh_center)
    bm.free()
    obj_center.location = pos
    obj_center.data.materials.append(material_white)

    # Petals
    num_petals = 6
    for i in range(num_petals):
        mesh_p = bpy.data.meshes.new("Petal")
        obj_p = bpy.data.objects.new("Petal", mesh_p)
        bpy.context.collection.objects.link(obj_p)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=6, radius=0.18)
        for v in bm.verts:
            v.co.z *= 0.1  # Flatten petal
            v.co.y *= 0.4  # Narrow petal
        bm.to_mesh(mesh_p)
        bm.free()
        
        angle = (2 * math.pi / num_petals) * i
        offset = Vector((math.cos(angle)*0.1, math.sin(angle)*0.1, 0))
        obj_p.location = pos + offset
        rot_mat = Matrix.Rotation(angle, 4, 'Z') @ Matrix.Rotation(math.radians(60), 4, 'X')
        obj_p.rotation_mode = 'QUATERNION'
        obj_p.rotation_quaternion = rot_mat.to_quaternion()
        obj_p.data.materials.append(material_white)

def get_point_on_stem(t, points):
    """Linearly interpolate between stem control points."""
    if t <= 0: return points[0]
    if t >= 1: return points[-1]
    idx = int(t * (len(points) - 1))
    local_t = (t * (len(points) - 1)) - idx
    return points[idx].lerp(points[idx+1], local_t)

def build_plant():
    clear_scene()
    mat_green = create_material("Green", (0.15, 0.45, 0.1, 1.0))
    mat_white = create_material("White", (0.98, 0.98, 0.98, 1.0))
    
    # Main stem path - taller and more elegant
    main_pts = [
        Vector((0, 0, 0)),
        Vector((0.1, 0.1, 1.5)),
        Vector((-0.1, 0.2, 3.0)),
        Vector((0.05, -0.1, 4.5))
    ]
    build_tube("MainStem", main_pts, 0.07, mat_green)
    
    # Branches and blooms along the stem
    num_branches = 8
    for i in range(num_branches):
        t_param = (i + 1) / (num_branches + 1)
        p_start = get_point_on_stem(t_param, main_pts)
        
        angle = i * 2.2  # Spiral offset
        dir_vec = Vector((math.cos(angle), math.sin(angle), 0.8)).normalized()
        branch_len = 0.6 + random.uniform(0, 0.3)
        p_end = p_start + dir_vec * branch_len
        
        build_tube(f"Branch_{i}", [p_start, p_end], 0.04, mat_green)
        
        # Leaves along the branch
        for l_idx in range(2):
            l_t = (l_idx + 1) / 3
            l_pos = p_start + (p_end - p_start) * l_t
            l_dir = (dir_vec + Vector((math.cos(angle), math.sin(angle), -0.2))).normalized()
            create_organic_leaf(l_pos, l_dir, (0.5, 1.0, 0.2), mat_green)

        create_flower(p_end, mat_white)

    # Top flower
    create_flower(main_pts[-1], mat_white)
    
    # Base leaf cluster
    num_base_leaves = 7
    for i in range(num_base_leaves):
        angle = (2 * math.pi / num_base_leaves) * i
        dir_vec = Vector((math.cos(angle), math.sin(angle), 0.6)).normalized()
        create_organic_leaf(Vector((0, 0, 0.1)), dir_vec, (0.7, 1.5, 0.3), mat_green)

if __name__ == "__main__":
    build_plant()
