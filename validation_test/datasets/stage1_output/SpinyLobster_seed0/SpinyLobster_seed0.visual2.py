import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 0.1
    bsdf.inputs['Specular IOR Level'].default_value = 0.7
    return mat

def create_curved_tube(name, control_points, radius, material):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Higher resolution for smoother curvature
    segments_per_span = 16
    all_points = []
    for i in range(len(control_points) - 1):
        p1 = Vector(control_points[i])
        p2 = Vector(control_points[i+1])
        for j in range(segments_per_span):
            all_points.append(p1.lerp(p2, j / segments_per_span))
    all_points.append(Vector(control_points[-1]))

    circle_res = 12
    prev_ring = []
    
    for i, p in enumerate(all_points):
        if i < len(all_points) - 1:
            tangent = (all_points[i+1] - p).normalized()
        else:
            tangent = (p - all_points[i-1]).normalized()
            
        ortho = Vector((0, 0, 1)) if abs(tangent.dot(Vector((0,0,1)))) < 0.9 else Vector((0,1,0))
        right = tangent.cross(ortho).normalized()
        up = tangent.cross(right).normalized()
        
        current_ring = []
        for j in range(circle_res):
            angle = (2 * math.pi / circle_res) * j
            off = (right * math.cos(angle) + up * math.sin(angle)) * radius
            current_ring.append(bm.verts.new(p + off))
        
        if prev_ring:
            for j in range(circle_res):
                next_j = (j + 1) % circle_res
                bm.faces.new((prev_ring[j], prev_ring[next_j], current_ring[next_j], current_ring[j]))
        
        prev_ring = current_ring

    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return obj

def create_leg(name, start_pos, side, material):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    
    side_mult = 1 if side == 'right' else -1
    joints = [
        Vector(start_pos),
        Vector((start_pos[0] + 0.25 * side_mult, start_pos[1], start_pos[2] - 0.1)),
        Vector((start_pos[0] + 0.4 * side_mult, start_pos[1] - 0.1, start_pos[2] - 0.3)),
        Vector((start_pos[0] + 0.45 * side_mult, start_pos[1] - 0.2, start_pos[2] - 0.5))
    ]
    
    # Tapering radius for pointed tips
    radii = [0.04, 0.03, 0.02, 0.005]
    for i in range(len(joints) - 1):
        p1, p2 = joints[i], joints[i+1]
        dir_vec = (p2 - p1).normalized()
        ortho = Vector((0, 0, 1)) if abs(dir_vec.dot(Vector((0,0,1)))) < 0.9 else Vector((0,1,0))
        right = dir_vec.cross(ortho).normalized()
        up = dir_vec.cross(right).normalized()
        res = 8
        r1, r2 = [], []
        for j in range(res):
            angle = (2 * math.pi / res) * j
            r1.append(bm.verts.new(p1 + (right * math.cos(angle) + up * math.sin(angle)) * radii[i]))
            r2.append(bm.verts.new(p2 + (right * math.cos(angle) + up * math.sin(angle)) * radii[i+1]))
        for j in range(res):
            nj = (j+1)%res
            bm.faces.new((r1[j], r1[nj], r2[nj], r2[j]))

    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(material)
    return obj

def build_spiny_lobster():
    clear_scene()
    shell_mat = create_material("LobsterShell", (0.8, 0.2, 0.1, 1.0))
    
    # --- Cephalothorax ---
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(0, 0, 0))
    head = bpy.context.active_object
    head.scale = (1.0, 0.9, 0.7)
    head.data.materials.append(shell_mat)
    bpy.ops.object.shade_smooth()

    # --- Abdomen (Overlapping Carapace Plates) ---
    num_segments = 6
    for i in range(num_segments):
        y_pos = -0.5 - (i * 0.25)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, y_pos, 0))
        seg = bpy.context.active_object
        # Wide in X, Thin in Y (for overlap), rounded height in Z
        seg.scale = (0.9 - i*0.05, 0.2, 0.5 - i*0.03)
        seg.rotation_euler[0] = math.radians(-12 * i)
        seg.data.materials.append(shell_mat)
        bpy.ops.object.shade_smooth()

    # --- Tail Fan (Radial plates) ---
    tail_y = -0.5 - (num_segments * 0.25)
    fan_center = Vector((0, tail_y, 0))
    for i in range(5):
        angle = math.pi * (i / 4) # Spread across 180 degrees
        offset_x = math.sin(angle) * 0.2
        offset_y = -math.cos(angle) * 0.2
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(offset_x, tail_y + offset_y, 0))
        plate = bpy.context.active_object
        plate.scale = (0.4, 0.1, 0.2)
        plate.rotation_euler[1] = angle
        plate.data.materials.append(shell_mat)
        bpy.ops.object.shade_smooth()

    # --- Antennae (Stout and smooth curving) ---
    ant_l_pts = [
        (0.2, 0.4, 0.1),
        (0.5, 1.2, 1.0),
        (1.2, 2.0, 2.0),
        (1.8, 3.0, 3.5)
    ]
    create_curved_tube("Antenna_L", ant_l_pts, 0.08, shell_mat)
    
    ant_r_pts = [
        (-0.2, 0.4, 0.1),
        (-0.5, 1.2, 1.0),
        (-1.2, 2.0, 2.0),
        (-1.8, 3.0, 3.5)
    ]
    create_curved_tube("Antenna_R", ant_r_pts, 0.08, shell_mat)

    # --- Walking Legs (Pointed) ---
    for i in range(4):
        y_pos = -0.1 - (i * 0.25)
        create_leg(f"Leg_L_{i}", (0.6, y_pos, -0.1), 'right', shell_mat)
        create_leg(f"Leg_R_{i}", (-0.6, y_pos, -0.1), 'left', shell_mat)

if __name__ == "__main__":
    build_spiny_lobster()
