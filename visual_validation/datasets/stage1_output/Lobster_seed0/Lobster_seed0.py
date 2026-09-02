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

def create_box(name, pos, scale, rotation, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=pos, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
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
    scale_f = 1.6 if is_crusher else 1.0
    
    # Arm segments - Lengthened for better proportions
    p0 = Vector((0.4 * mult, 0.8, 0))
    p1 = Vector((0.9 * mult, 1.5, 0.3))
    p2 = Vector((0.7 * mult, 2.1, 0.1))
    create_cylinder(f"{prefix}_Arm1", p0, p1, 0.12 * scale_f, material)
    create_cylinder(f"{prefix}_Arm2", p1, p2, 0.10 * scale_f, material)
    
    # Palm (Propodus) - More substantial shape
    palm_pos = Vector((0.6 * mult, 2.4, 0))
    palm = create_capsule(f"{prefix}_Palm", palm_pos, (0.25*scale_f, 0.4*scale_f, 0.18*scale_f), (0, 0, math.radians(10*mult)), material)
    
    # Fixed Finger
    p_fixed_start = Vector((0.6 * mult, 2.7, 0))
    p_fixed_end = Vector((0.5 * mult, 3.1, 0))
    create_cylinder(f"{prefix}_Fixed", p_fixed_start, p_fixed_end, 0.08 * scale_f, material)
    
    # Movable Finger (Dactylus)
    p_move_start = Vector((0.85 * mult, 2.6, 0))
    p_move_end = Vector((0.4 * mult, 3.0, 0))
    create_cylinder(f"{prefix}_Dactylus", p_move_start, p_move_end, 0.08 * scale_f, material)
    
    if is_crusher:
        # Pure white and more prominent tip on the moving finger
        tip_end = p_move_end
        tip_dir = (p_move_end - p_move_start).normalized()
        tip_start = tip_end - tip_dir * 0.4
        create_cylinder(f"{prefix}_Tip", tip_start, tip_end, 0.085 * scale_f, white_mat)

def create_leg(side, index, material):
    mult = side
    # Positioned beneath the thorax (cephalothorax area)
    start = Vector((0.3 * mult, -0.2 - (index * 0.4), 0))
    mid = Vector((0.7 * mult, -0.6 - (index * 0.4), -0.5))
    end = Vector((0.6 * mult, -1.0 - (index * 0.4), -1.2))
    create_cylinder(f"Leg_{side}_{index}_1", start, mid, 0.05, material)
    create_cylinder(f"Leg_{side}_{index}_2", mid, end, 0.04, material)

def create_antenna(side, material):
    mult = side
    points = [
        Vector((0.1 * mult, 1.0, 0.3)),
        Vector((0.4 * mult, 2.0, 1.5)),
        Vector((0.6 * mult, 3.0, 2.8)),
        Vector((0.5 * mult, 3.8, 3.5))
    ]
    for i in range(len(points) - 1):
        create_cylinder(f"Antenna_{side}_{i}", points[i], points[i+1], 0.02, material)

def main():
    clear_scene()
    # Warm reddish-brown and bright white
    red_brown = create_material("LobsterRed", (0.4, 0.1, 0.05, 1.0), roughness=0.2)
    white = create_material("PincerWhite", (1.0, 1.0, 1.0, 1.0), roughness=0.3)

    # Cephalothorax - Centered at origin
    cepha = create_capsule("Cephalothorax", (0, 0, 0), (0.65, 1.2, 0.75), (0, 0, 0), red_brown)

    # Abdomen segments - Adjusted to start closer and overlap for connectivity
    for i in range(6):
        y_pos = -1.0 - (i * 0.4)
        scale = (0.58 - (i*0.03), 0.35, 0.5 - (i*0.02))
        seg = create_capsule(f"Abdomen_{i}", (0, y_pos, 0), scale, (0, 0, 0), red_brown)
        # Slight curve to the abdomen
        seg.rotation_euler[0] = math.radians(-6 * i)

    # Tail Fan - Using flattened boxes for "fan" plates
    telson_pos = Vector((0, -3.5, -0.4))
    create_capsule("Telson", telson_pos, (0.3, 0.2, 0.1), (0, 0, 0), red_brown)
    for side in [1, -1]:
        uropod_start = Vector((0.2 * side, -3.3, -0.4))
        uropod_end = Vector((0.6 * side, -3.7, -0.4))
        create_cylinder(f"Uropod_{side}", uropod_start, uropod_end, 0.06, red_brown)
        # Flat fan blade plates
        blade_pos = Vector((0.8 * side, -3.8, -0.4))
        create_box(f"Blade_{side}", blade_pos, (0.4, 0.15, 0.05), (0, math.radians(-20*side), 0), red_brown)

    # Two unequal chelae: Right is Crusher, Left is Cutter
    create_pincer(1, True, red_brown, white)   
    create_pincer(-1, False, red_brown, white) 

    for i in range(4):
        create_leg(1, i, red_brown)
        create_leg(-1, i, red_brown)

    create_antenna(1, red_brown)
    create_antenna(-1, red_brown)

if __name__ == "__main__":
    main()
