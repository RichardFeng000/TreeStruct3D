import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Clear the default scene."""
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

def create_box(name, size, location, material):
    """Create a cube scaled to specific dimensions."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    return obj

def build_fridge():
    # Dimensions (Compact cube-like)
    W, D, H = 0.5, 0.5, 0.55  # Width, Depth, Height
    thickness = 0.02

    # Materials - Using deep dark brown and high contrast for glass/metal
    mat_body = create_material("BodyDarkBrown", (0.06, 0.03, 0.01, 1.0), metallic=0.1, roughness=0.4)
    mat_glass = create_material("GlassTop", (0.01, 0.01, 0.02, 1.0), metallic=0.3, roughness=0.1)
    mat_metal = create_material("HandleMetal", (0.8, 0.8, 0.8, 1.0), metallic=1.0, roughness=0.2)

    # --- Main Body Cabinet ---
    # Bottom at Z=0
    body = create_box("Fridge_Body", (W, D, H), (0, 0, H/2), mat_body)
    bev_body = body.modifiers.new(name="Bevel", type='BEVEL')
    bev_body.width = 0.01
    bev_body.segments = 3

    # --- Glass Top ---
    # Sits flush on top of the cabinet
    glass_h = 0.015
    glass_top = create_box("GlassTop", (W, D, glass_h), (0, 0, H + glass_h/2), mat_glass)
    bev_glass = glass_top.modifiers.new(name="Bevel", type='BEVEL')
    bev_glass.width = 0.005
    bev_glass.segments = 3

    # --- Door ---
    # Positioned at the front (Y negative). Offset slightly to avoid Z-fighting.
    door_w = W - 0.01 # Slight inset for a seam
    door_h = H - 0.02
    door_depth = thickness
    # Center of door: X=0, Y is at the front face of body (-D/2) minus half its own depth
    door_y = -D/2 - (door_depth / 2)
    door = create_box("Fridge_Door", (door_w, door_depth, door_h), (0, door_y, H/2), mat_body)
    bev_door = door.modifiers.new(name="Bevel", type='BEVEL')
    bev_door.width = 0.005
    bev_door.segments = 3

    # --- Door Handle ---
    # Vertical metallic handle on the right side of the door
    h_w, h_depth, h_height = 0.015, 0.04, 0.2
    # X position: near right edge of the door
    hx = (door_w / 2) - 0.03
    # Y position: protruding from the door face
    hy = door_y - (door_depth/2) - (h_depth/2)
    hz = H/2 # Centered vertically
    handle = create_box("DoorHandle", (h_w, h_depth, h_height), (hx, hy, hz), mat_metal)
    bev_handle = handle.modifiers.new(name="Bevel", type='BEVEL')
    bev_handle.width = 0.005
    bev_handle.segments = 3

    # --- Feet ---
    foot_r = 0.012
    foot_h = 0.02
    offset = 0.07
    foot_coords = [
        (W/2 - offset, D/2 - offset),
        (-W/2 + offset, D/2 - offset),
        (W/2 - offset, -D/2 + offset),
        (-W/2 + offset, -D/2 + offset)
    ]

    for i, (cx, cy) in enumerate(foot_coords):
        bpy.ops.mesh.primitive_cylinder_add(radius=foot_r, depth=foot_h, location=(cx, cy, foot_h/2))
        foot = bpy.context.active_object
        foot.name = f"Foot_{i}"
        foot.data.materials.append(mat_body)

    # Parenting for hierarchy
    glass_top.parent = body
    door.parent = body
    handle.parent = door

if __name__ == "__main__":
    clear_scene()
    build_fridge()
