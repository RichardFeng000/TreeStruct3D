import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.2):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        for input in bsdf.inputs:
            if input.name == 'Base Color':
                input.default_value = color
            elif input.name == 'Roughness':
                input.default_value = roughness
    return mat

def create_cylinder(name, start, end, radius, material):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    
    segments = 12
    direction = (end - start).normalized()
    up = Vector((0, 0, 1)) if abs(direction.z) < 0.9 else Vector((0, 1, 0))
    right = direction.cross(up).normalized()
    forward = direction.cross(right).normalized()

    verts_start = []
    for i in range(segments):
        angle = (2 * math.pi / segments) * i
        pos = start + (right * math.cos(angle) + forward * math.sin(angle)) * radius
        verts_start.append(bm.verts.new(pos))
    
    verts_end = []
    for i in range(segments):
        angle = (2 * math.pi / segments) * i
        pos = end + (right * math.cos(angle) + forward * math.sin(angle)) * radius
        verts_end.append(bm.verts.new(pos))
    
    for i in range(segments):
        bm.faces.new((verts_start[i], verts_start[(i+1)%segments], verts_end[(i+1)%segments], verts_end[i]))
    
    bm.faces.new(verts_start)
    bm.faces.new(verts_end)
    
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(material)
    return obj

def create_capsule(name, pos, scale, rotation, material):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=pos)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    return obj

def create_pincer(side, is_crusher, material, white_mat):
    mult = side
    prefix = "Claw_R" if side == 1 else "Claw_L"
    scale_f = 1.5 if is_crusher else 1.0
    
    # Arm segments
    p0 = Vector((0.4 * mult, 0.6, 0))
    p1 = Vector((0.8 * mult, 1.2, 0.2))
    p2 = Vector((0.7 * mult, 1.7, -0.1))
    create_cylinder(f"{prefix}_Arm1", p0, p1, 0.1 * scale_f, material)
    create_cylinder(f"{prefix}_Arm2", p1, p2, 0.08 * scale_f, material)
    
    # Palm (Propodus)
    palm_pos = Vector((0.7 * mult, 2.0, -0.1))
    palm = create_capsule(f"{prefix}_Palm", palm_pos, (0.2*scale_f, 0.3*scale_f, 0.15*scale_f), (0, 0, 0), material)
    
    # Fixed Finger
    p_fixed_start = Vector((0.7 * mult, 2.2, -0.1))
    p_fixed_end = Vector((0.7 * mult, 2.5, -0.1))
    create_cylinder(f"{prefix}_Fixed", p_fixed_start, p_fixed_end, 0.07 * scale_f, material)
    
    # Movable Finger (Dactylus)
    p_move_start = Vector((0.85 * mult, 2.1, -0.1))
    p_move_end = Vector((0.6 * mult, 2.45, -0.1))
    create_cylinder(f"{prefix}_Dactylus", p_move_start, p_move_end, 0.07 * scale_f, material)
    
    if is_crusher:
        # Pronounced white tip on dactylus end
        tip_end = p_move_end
        tip_start = tip_end - (tip_end - p_move_start).normalized() * 0.25
        create_cylinder(f"{prefix}_Tip", tip_start, tip_end, 0.07 * scale_f, white_mat)

def create_leg(side, index, material):
    mult = side
    start = Vector((0.4 * mult, -0.2 - (index * 0.3), 0))
    mid = Vector((0.8 * mult, -0.5 - (index * 0.3), -0.6))
    end = Vector((0.7 * mult, -0.6 - (index * 0.3), -1.2))
    create_cylinder(f"Leg_{side}_{index}_1", start, mid, 0.04, material)
    create_cylinder(f"Leg_{side}_{index}_2", mid, end, 0.03, material)

def create_antenna(side, material):
    mult = side
    points = [
        Vector((0.15 * mult, 0.8, 0.2)),
        Vector((0.4 * mult, 1.6, 1.2)),
        Vector((0.7 * mult, 2.3, 2.2)),
        Vector((0.6 * mult, 3.0, 3.0))
    ]
    for i in range(len(points) - 1):
        create_cylinder(f"Antenna_{side}_{i}", points[i], points[i+1], 0.02, material)

def main():
    clear_scene()
    red_brown = create_material("LobsterRed", (0.45, 0.15, 0.08, 1.0), roughness=0.2)
    white = create_material("PincerWhite", (0.9, 0.9, 0.9, 1.0), roughness=0.3)

    # Cephalothorax - Ellipsoid for more organic look
    cepha = create_capsule("Cephalothorax", (0, 0, 0), (0.6, 1.2, 0.7), (0, 0, 0), red_brown)

    # Abdomen segments
    for i in range(6):
        y_pos = -1.3 - (i * 0.4)
        scale = (0.55 - (i*0.02), 0.3, 0.45 - (i*0.02))
        seg = create_capsule(f"Abdomen_{i}", (0, y_pos, 0), scale, (0, 0, 0), red_brown)
        seg.rotation_euler[0] = math.radians(-8 * i)

    # Tail Fan - Unified structure
    telson_pos = Vector((0, -3.8, -0.2))
    create_capsule("Telson", telson_pos, (0.3, 0.2, 0.1), (0, 0, 0), red_brown)
    for side in [1, -1]:
        uropod_start = Vector((0.2 * side, -3.6, -0.2))
        uropod_end = Vector((0.7 * side, -4.1, -0.2))
        create_cylinder(f"Uropod_{side}", uropod_start, uropod_end, 0.05, red_brown)
        # Flat fan blade
        u_blade = create_capsule(f"Blade_{side}", (0.7 * side, -4.1, -0.2), (0.3, 0.1, 0.05), (0, math.radians(-20*side), 0), red_brown)

    create_pincer(1, True, red_brown, white)   # Right - Crusher
    create_pincer(-1, False, red_brown, white) # Left - Cutter

    for i in range(4):
        create_leg(1, i, red_brown)
        create_leg(-1, i, red_brown)

    create_antenna(1, red_brown)
    create_antenna(-1, red_brown)

if __name__ == "__main__":
    main()
