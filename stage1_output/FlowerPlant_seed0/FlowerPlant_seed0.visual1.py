import bpy
import bmesh
import math
import random
from mathutils import Vector

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
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    res = 8
    prev_ring = []
    for i, p in enumerate(points):
        if i == 0:
            dir = (points[1] - points[0]).normalized() if len(points) > 1 else Vector((0,0,1))
        else:
            dir = (p - points[i-1]).normalized()
        up = Vector((0, 0, 1)) if abs(dir.z) < 0.9 else Vector((0, 1, 0))
        right = dir.cross(up).normalized()
        forward = right.cross(dir).normalized()
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

def create_broad_leaf(pos, direction, scale, material):
    mesh = bpy.data.meshes.new("Leaf")
    obj = bpy.data.objects.new("Leaf", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    # Create a leaf using a scaled sphere approach for "broadness"
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=8, radius=1.0)
    for v in bm.verts:
        v.co.z *= 0.1 # Flatten
        # Taper one end to make it leaf-like (pointed tip)
        t = (v.co.x + 1) / 2
        factor = 1.0 - t * 0.7
        v.co.y *= factor
    bm.to_mesh(mesh)
    bm.free()
    obj.location = pos
    # Align leaf x-axis with direction
    rot_quat = Vector((1, 0, 0)).to_track_quat('X', direction, Vector((0,0,1)))
    obj.rotation_euler = rot_quat.to_euler()
    obj.scale = scale
    obj.data.materials.append(material)
    return obj

def create_flower(pos, material_white):
    # Small white flower bloom
    container = bpy.data.collections.new("Flower")
    bpy.context.scene.collection.children.link(container)
    
    # Center
    mesh_center = bpy.data.meshes.new("Center")
    obj_center = bpy.data.objects.new("Center", mesh_center)
    container.objects.link(obj_center)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=8, radius=0.04)
    bm.to_mesh(mesh_center)
    bm.free()
    obj_center.location = pos
    obj_center.data.materials.append(material_white)

    # Petals (small spheres flattened)
    num_petals = 5
    for i in range(num_petals):
        mesh_p = bpy.data.meshes.new("Petal")
        obj_p = bpy.data.objects.new("Petal", mesh_p)
        container.objects.link(obj_p)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=8, radius=0.1)
        for v in bm.verts:
            v.co.z *= 0.2
            v.co.y *= 0.5
        bm.to_mesh(mesh_p)
        bm.free()
        angle = (2 * math.pi / num_petals) * i
        obj_p.location = pos + Vector((math.cos(angle)*0.06, math.sin(angle)*0.06, 0))
        obj_p.rotation_euler = (0, 0, angle)
        obj_p.data.materials.append(material_white)

def build_plant():
    clear_scene()
    mat_green = create_material("Green", (0.15, 0.4, 0.1, 1.0))
    mat_white = create_material("White", (0.95, 0.95, 0.9, 1.0))
    
    # Tall main stem
    main_pts = [Vector((0,0,0)), Vector((0.05, 0, 0.8)), Vector((-0.05, 0.05, 1.6)), Vector((0,0,2.4))]
    build_tube("MainStem", main_pts, 0.04, mat_green)
    
    # Branching stalks and leaves
    num_branches = 6
    for i in range(num_branches):
        z_pos = (i + 1) * 0.35
        if z_pos > 2.2: continue
        
        # Find position on main stem via linear interpolation for simplicity
        p_start = Vector((0, 0, z_pos)) 
        angle = (i * 1.2) # spiral distribution
        dir_vec = Vector((math.cos(angle), math.sin(angle), 0.4)).normalized()
        p_end = p_start + dir_vec * 0.6
        
        # Branch stem
        build_tube(f"Branch_{i}", [p_start, p_end], 0.02, mat_green)
        
        # Leaves along the branch
        for leaf_idx in range(3):
            t = (leaf_idx + 1) / 4
            l_pos = p_start + (p_end - p_start) * t
            l_dir = dir_vec.copy() # simplify leaf direction
            # Add some random variation to leave angle
            l_dir += Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 0))
            create_broad_leaf(l_pos, l_dir.normalized(), (0.3, 0.5, 0.1), mat_green)

        # Flower at end of branch
        create_flower(p_end, mat_white)

    # Topmost bloom
    create_flower(main_pts[-1], mat_white)
    
    # Base cluster leaves
    for i in range(5):
        angle = (2 * math.pi / 5) * i
        dir_vec = Vector((math.cos(angle), math.sin(angle), 0.3)).normalized()
        create_broad_leaf(Vector((0,0,0.1)), dir_vec, (0.4, 0.7, 0.2), mat_green)

if __name__ == "__main__":
    build_plant()
