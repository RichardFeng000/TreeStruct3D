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

def create_cube(name, size, location, material):
    """Helper to create a cube with specific total dimensions."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    # Scale the unit cube (1x1x1) to actual desired sizes
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    return obj

def build_fridge():
    # Dimensions
    W, D, H = 0.5, 0.5, 0.6  # Width, Depth, Height
    thickness = 0.02
    gap = 0.005

    # Materials
    mat_body = create_material("BodyDarkBrown", (0.12, 0.05, 0.03, 1.0), metallic=0.1, roughness=0.4)
    mat_glass = create_material("GlassTop", (0.02, 0.02, 0.02, 1.0), metallic=0.2, roughness=0.05)
    mat_metal = create_material("HandleMetal", (0.7, 0.7, 0.7, 1.0), metallic=1.0, roughness=0.2)

    # --- Main Body ---
    # Center the body so its bottom is at z=0
    body = create_cube("Fridge_Body", (W, D, H), (0, 0, H/2), mat_body)
    
    # Add a slight bevel to the body for realism
    bev = body.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.01
    bev.segments = 5

    # --- Glass Top ---
    # Positioned exactly on top of the body
    glass_h = 0.01
    glass_top = create_cube("GlassTop", (W, D, glass_h), (0, 0, H + glass_h/2), mat_glass)
    gbev = glass_top.modifiers.new(name="Bevel", type='BEVEL')
    gbev.width = 0.005
    gbev.segments = 3

    # --- Door ---
    # The door sits at the front (y = -D/2)
    door_w = W - gap * 2
    door_h = H - (gap * 4) # Leave room for top glass and feet
    door_depth = thickness
    
    # Position: y is slightly offset so it doesn't Z-fight with the body face
    door = create_cube("Fridge_Door", (door_w, door_depth, door_h), (0, -D/2 + door_depth/2, H/2), mat_body)
    dbev = door.modifiers.new(name="Bevel", type='BEVEL')
    dbev.width = 0.005
    dbev.segments = 3

    # --- Door Handle ---
    # Vertical metallic handle on the right side of the door
    h_w, h_depth, h_height = 0.02, 0.03, 0.2
    hx = (door_w / 2) - 0.04  # Offset from the right edge
    hy = -D/2 - 0.01          # Slightly protruding from door
    hz = H/2                  # Centered vertically on door
    handle = create_cube("DoorHandle", (h_w, h_depth, h_height), (hx, hy, hz), mat_metal)
    hbev = handle.modifiers.new(name="Bevel", type='BEVEL')
    hbev.width = 0.005
    hbev.segments = 3

    # --- Feet ---
    foot_r = 0.015
    foot_h = 0.03
    offset = 0.08
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

    # Parenting for coherence
    glass_top.parent = body
    door.parent = body
    handle.parent = door

if __name__ == "__main__":
    clear_scene()
    build_fridge()
