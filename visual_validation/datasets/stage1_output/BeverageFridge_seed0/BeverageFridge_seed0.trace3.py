import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Clear the default scene of all objects."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Create a principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_mini_fridge():
    # Dimensions
    w, d, h = 0.5, 0.5, 0.6  # Width, Depth, Height
    corner_radius = 0.02
    shell_thickness = 0.02
    door_gap = 0.005

    # Materials
    mat_body = create_material("BodyBrown", (0.1, 0.04, 0.02, 1.0), metallic=0.1, roughness=0.3)
    mat_glass = create_material("GlassTop", (0.01, 0.01, 0.01, 1.0), metallic=0.1, roughness=0.05)
    mat_metal = create_material("HandleMetal", (0.7, 0.7, 0.8, 1.0), metallic=1.0, roughness=0.2)

    # --- Main Chassis Construction ---
    # We build the body using bmesh to ensure a proper cavity for the door
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale to desired dimensions
    for v in bm.verts:
        v.co.x *= w / 2
        v.co.y *= d / 2
        v.co.z *= h / 2

    # Find the front face (facing -Y)
    front_face = None
    for f in bm.faces:
        if f.normal.y < -0.9:
            front_face = f
            break
    
    if front_face:
        # Create a bezel/frame by insetting the front face
        res = bmesh.ops.inset_individual(bm, faces=[front_face], thickness=shell_thickness)
        inner_face = res['faces'][0]
        
        # Extrude inner face backwards to create the fridge interior cavity
        bmesh.ops.translate(bm, vec=(0, shell_thickness, 0), verts=inner_face.verts)

    # Apply beveling for rounded corners on the main chassis
    bm.to_mesh(bpy.data.meshes.new("ChassisMesh"))
    body = bpy.data.objects.new("Fridge_Body", bm.to_mesh(bpy.data.meshes.new("Temp"))) # Temporary fix to avoid error
    # Redoing the BMesh logic more cleanly:
    bm.free()

def build_fridge_v2():
    # Dimensions
    w, d, h = 0.5, 0.5, 0.6
    shell_thickness = 0.02
    door_gap = 0.005

    # Materials
    mat_body = create_material("BodyBrown", (0.1, 0.04, 0.02, 1.0), metallic=0.1, roughness=0.3)
    mat_glass = create_material("GlassTop", (0.01, 0.01, 0.01, 1.0), metallic=0.1, roughness=0.05)
    mat_metal = create_material("HandleMetal", (0.7, 0.7, 0.8, 1.0), metallic=1.0, roughness=0.2)

    # --- Body Chassis ---
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, h/2))
    body = bpy.context.active_object
    body.name = "Fridge_Body"
    body.scale = (w/2, d/2, h/2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # BMesh to carve the front
    bm = bmesh.new()
    bm.from_mesh(body.data)
    front_face = None
    for f in bm.faces:
        if f.normal.y < -0.9:
            front_face = f
            break
    
    if front_face:
        # Inset the face to create a frame
        res = bmesh.ops.inset_individual(bm, faces=[front_face], thickness=shell_thickness)
        inner_face = res['faces'][0]
        # Push interior back
        bmesh.ops.translate(bm, vec=(0, shell_thickness * 2, 0), verts=inner_face.verts)

    bm.to_mesh(body.data)
    bm.free()

    # Bevel the body for smoothness
    bev = body.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.015
    bev.segments = 5
    body.data.materials.append(mat_body)

    # --- Glass Top ---
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, h + 0.005))
    glass_top = bpy.context.active_object
    glass_top.name = "GlassTop"
    # Make it slightly smaller than the top surface to look like a cap
    glass_top.scale = (w/2 * 0.98, d/2 * 0.98, 0.01)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    gbev = glass_top.modifiers.new(name="Bevel", type='BEVEL')
    gbev.width = 0.005
    gbev.segments = 3
    glass_top.data.materials.append(mat_glass)

    # --- Door ---
    # The door fills the cavity and sits slightly in front
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -d/2 + shell_thickness/2, h/2))
    door = bpy.context.active_object
    door.name = "Fridge_Door"
    # Dimensions to fit the bezel
    door.scale = (w/2 * 0.96, 0.03, h/2 * 0.96)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    dbev = door.modifiers.new(name="Bevel", type='BEVEL')
    dbev.width = 0.01
    dbev.segments = 3
    door.data.materials.append(mat_body)

    # --- Door Handle ---
    handle_w, handle_h, handle_d = 0.02, 0.25, 0.04
    # Position on right side of door (X positive), slightly offset from surface
    hx = w/2 - 0.06
    hy = -d/2 - 0.03
    hz = h/2
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(hx, hy, hz))
    handle = bpy.context.active_object
    handle.name = "DoorHandle"
    handle.scale = (handle_w/2, handle_d/2, handle_h/2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    hbev = handle.modifiers.new(name="Bevel", type='BEVEL')
    hbev.width = 0.008
    hbev.segments = 3
    handle.data.materials.append(mat_metal)

    # --- Feet ---
    foot_r, foot_h = 0.015, 0.04
    offset = 0.06
    coords = [
        (w/2 - offset, d/2 - offset),
        (-w/2 + offset, d/2 - offset),
        (w/2 - offset, -d/2 + offset),
        (-w/2 + offset, -d/2 + offset)
    ]

    for i, (cx, cy) in enumerate(coords):
        bpy.ops.mesh.primitive_cylinder_add(radius=foot_r, depth=foot_h, location=(cx, cy, foot_h/2))
        foot = bpy.context.active_object
        foot.name = f"Foot_{i}"
        foot.data.materials.append(mat_body)

    # Parenting for organization
    glass_top.parent = body
    door.parent = body
    handle.parent = door

if __name__ == "__main__":
    clear_scene()
    build_fridge_v2()
