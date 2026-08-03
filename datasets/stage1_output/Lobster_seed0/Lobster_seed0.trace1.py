import bpy
import bmesh
import math
from mathutils import Vector, Quaternion

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.2):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs[0].default_value = color # Base Color
        bsdf.inputs[7].default_value = roughness # Roughness (Blender 4+ mapping)
        # For Blender 5.0, we should check the specific input index or name
        for input in bsdf.inputs:
            if input.name == 'Roughness':
                input.default_value = roughness
    return mat

def create_mesh_cylinder(name, start, end, radius, material):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Create circle at start
    segments = 12
    verts_start = []
    for i in range(segments):
        angle = (2 * math.pi / segments) * i
        # Calculate a perpendicular vector for the radius
        direction = (end - start).normalized()
        up = Vector((0, 0, 1)) if abs(direction.z) < 0.9 else Vector((0, 1, 0))
        right = direction.cross(up).normalized()
        forward = direction.cross(right).normalized()
        pos = start + (right * math.cos(angle) + forward * math.sin(angle)) * radius
        verts_start.append(bm.verts.new(pos))
    
    # Create circle at end
    verts_end = []
    for i in range(segments):
        angle = (2 * math.pi / segments) * i
        direction = (end - start).normalized()
        up = Vector((0, 0, 1)) if abs(direction.z) < 0.9 else Vector((0, 1, 0))
        right = direction.cross(up).normalized()
        forward = direction.cross(right).normalized()
        pos = end + (right * math.cos(angle) + forward * math.sin(angle)) * radius
        verts_end.append(bm.verts.new(pos))
    
    # Bridge them
    for i in range(segments):
        bm.faces.new((verts_start[i], verts_start[(i+1)%segments], verts_end[(i+1)%segments], verts_end[i]))
    
    # Cap ends
    bm.faces.new(verts_start)
    bm.faces.new(verts_end)
    
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(material)
    return obj

def create_rounded_box(name, pos, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=pos)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    
    # Bevel for rounding
    mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    mod.width = 0.2
    mod.segments = 3
    
    subsurf = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf.levels = 1
    
    obj.data.materials.append(material)
    return obj

def create_pincer(side, is_crusher, material, white_mat):
    # side: 1 for Right, -1 for Left
    mult = side
    prefix = "Claw_R" if side == 1 else "Claw_L"
    
    size_factor = 1.4 if is_crusher else 1.0
    
    # Arm segments (Merus and Carpus)
    p0 = Vector((0.4 * mult, 0.6, 0))
    p1 = Vector((0.8 * mult, 1.2, 0.2))
    p2 = Vector((0.7 * mult, 1.6, -0.1))
    
    arm1 = create_mesh_cylinder(f"{prefix}_Arm1", p0, p1, 0.12 * size_factor, material)
    arm2 = create_mesh_cylinder(f"{prefix}_Arm2", p1, p2, 0.1 * size_factor, material)
    
    # The Pincer (Propodus and Dactylus)
    # Propodus (Fixed part)
    p3 = Vector((0.7 * mult, 2.1, -0.1))
    prop = create_mesh_cylinder(f"{prefix}_Propodus", p2, p3, 0.15 * size_factor, material)
    # Scale the propodus to be a bit chunkier
    prop.scale = (1.4, 1.4, 1.4)
    
    # Dactylus (Movable finger)
    p4 = Vector((0.65 * mult, 2.0, -0.3)) # Slight offset to leave gap
    dact_end = Vector((0.7 * mult, 2.1, -0.4)) if not is_crusher else Vector((0.8 * mult, 2.2, -0.4))
    # To make it look like a pincer, we'll use a slightly different approach for the finger
    dact = create_mesh_cylinder(f"{prefix}_Dactylus", p2, dact_end, 0.1 * size_factor, material)
    
    if is_crusher:
        # Add white tip to crusher
        tip_start = dact_end - (dact_end - p2).normalized() * 0.3
        tip_end = dact_end
        create_mesh_cylinder(f"{prefix}_Tip", tip_start, tip_end, 0.1 * size_factor, white_mat)

def create_leg(side, index, material):
    mult = side
    # Start point on thorax
    start = Vector((0.5 * mult, -0.2 - (index * 0.3), 0))
    mid = Vector((0.8 * mult, -0.4 - (index * 0.3), -0.6))
    end = Vector((0.7 * mult, -0.5 - (index * 0.3), -1.0))
    
    leg1 = create_mesh_cylinder(f"Leg_{side}_{index}_1", start, mid, 0.05, material)
    leg2 = create_mesh_cylinder(f"Leg_{side}_{index}_2", mid, end, 0.04, material)

def create_antenna(side, material):
    mult = side
    start = Vector((0.1 * mult, 0.8, 0.2))
    points = [
        start,
        Vector((0.3 * mult, 1.5, 1.2)),
        Vector((0.5 * mult, 2.0, 2.5)),
        Vector((0.4 * mult, 2.8, 3.0))
    ]
    
    for i in range(len(points) - 1):
        create_mesh_cylinder(f"Antenna_{side}_{i}", points[i], points[i+1], 0.02, material)

def main():
    clear_scene()
    
    # Materials
    red_brown = create_material("LobsterRed", (0.45, 0.15, 0.08, 1.0), roughness=0.2)
    white = create_material("PincerWhite", (0.9, 0.9, 0.9, 1.0), roughness=0.3)

    # --- Cephalothorax (The main head/body part) ---
    cepha = create_rounded_box("Cephalothorax", (0, 0, 0), (0.8, 1.2, 0.7), red_brown)
    
    # --- Abdomen (Segmented Tail) ---
    for i in range(6):
        y_pos = -1.0 - (i * 0.5)
        scale = (0.7 - (i*0.05), 0.4, 0.5 - (i*0.02))
        seg = create_rounded_box(f"Abdomen_{i}", (0, y_pos, 0), scale, red_brown)
        # Rotate slightly for natural curve
        seg.rotation_euler[0] = math.radians(-5 * i)

    # --- Tail Fan ---
    telson_pos = (0, -4.2, 0)
    telson = create_rounded_box("Telson", telson_pos, (0.4, 0.3, 0.1), red_brown)
    
    for side in [1, -1]:
        uropod_pos = (0.5 * side, -4.2, 0)
        uropod = create_rounded_box(f"Uropod_{side}", uropod_pos, (0.3, 0.6, 0.08), red_brown)
        uropod.rotation_euler[1] = math.radians(-15 * side)

    # --- Claws ---
    create_pincer(1, True, red_brown, white)   # Right - Crusher
    create_pincer(-1, False, red_brown, white) # Left - Cutter

    # --- Walking Legs ---
    for i in range(4):
        create_leg(1, i, red_brown)
        create_leg(-1, i, red_brown)

    # --- Antennae ---
    create_antenna(1, red_brown)
    create_antenna(-1, red_brown)

if __name__ == "__main__":
    main()
