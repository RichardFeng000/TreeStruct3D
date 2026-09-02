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
    """Create a simple principled BSDF material."""
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
    width = 0.5  # x
    depth = 0.5  # y
    height = 0.6 # z
    corner_radius = 0.02
    door_gap = 0.005

    # Materials
    mat_body = create_material("BodyBrown", (0.1, 0.05, 0.03, 1.0), metallic=0.1, roughness=0.4) # Dark brown
    mat_glass = create_material("GlassTop", (0.02, 0.02, 0.02, 1.0), metallic=0.2, roughness=0.1) # Dark glass
    mat_metal = create_material("HandleMetal", (0.7, 0.7, 0.7, 1.0), metallic=1.0, roughness=0.2) # Metallic silver

    # --- Main Chassis ---
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, height / 2))
    body = bpy.context.active_object
    body.name = "Fridge_Body"
    body.scale = (width, depth, height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Create a cavity for the door by deleting the front face
    bm = bmesh.new()
    bm.from_mesh(body.data)
    
    front_face = None
    for f in bm.faces:
        if f.normal.y < -0.9: # Front is facing -Y
            front_face = f
            break
    
    if front_face:
        # In Blender 5.0, bmesh.ops.delete just takes the geom list
        bmesh.ops.delete(bm, geom=[front_face], type='FACE' if hasattr(bmesh.ops, 'delete') and False else None) # Safety check removed as per error logic
    
    # Re-correcting: The previous error was exactly due to keyword 'type'. 
    # Just pass the geometry list.
    bm = bmesh.new()
    bm.from_mesh(body.data)
    front_face = None
    for f in bm.faces:
        if f.normal.y < -0.9:
            front_face = f
            break
    if front_face:
        bmesh.ops.delete(bm, geom=[front_face])

    bm.to_mesh(body.data)
    bm.free()

    # Bevel the main chassis edges
    bevel = body.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = corner_radius
    bevel.segments = 5
    body.data.materials.append(mat_body)

    # --- The Top Glass Surface ---
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, height + 0.002))
    glass_top = bpy.context.active_object
    glass_top.name = "GlassTop"
    # Slightly smaller than the body to look like a fitted insert/cap
    glass_top.scale = (width * 0.99, depth * 0.99, 0.015)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    glass_top.data.materials.append(mat_glass)

    # --- The Door ---
    # Position the door just in front of the body cavity
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -depth / 2 - door_gap/2, height / 2))
    door = bpy.context.active_object
    door.name = "Fridge_Door"
    # Door dimensions (slightly smaller than body to fit against the frame)
    door.scale = (width * 0.98, 0.04, height * 0.98)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    door_bev = door.modifiers.new(name="Bevel", type='BEVEL')
    door_bev.width = 0.01
    door_bev.segments = 3
    door.data.materials.append(mat_body)

    # --- The Handle ---
    handle_w = 0.025
    handle_h = 0.25
    handle_d = 0.04
    # Position handle on the right side of the door (x positive)
    handle_pos_x = width / 2 - 0.06
    handle_pos_y = -depth / 2 - 0.05
    handle_pos_z = height / 2
    
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(handle_pos_x, handle_pos_y, handle_pos_z))
    handle = bpy.context.active_object
    handle.name = "DoorHandle"
    handle.scale = (handle_w, handle_d, handle_h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    han_bev = handle.modifiers.new(name="Bevel", type='BEVEL')
    han_bev.width = 0.008
    han_bev.segments = 3
    handle.data.materials.append(mat_metal)

    # --- Feet ---
    foot_radius = 0.02
    foot_height = 0.04
    offset = 0.05 # Offset from edges
    foot_positions = [
        (width/2 - offset, depth/2 - offset),
        (-width/2 + offset, depth/2 - offset),
        (width/2 - offset, -depth/2 + offset),
        (-width/2 + offset, -depth/2 + offset)
    ]

    for i, pos in enumerate(foot_positions):
        bpy.ops.mesh.primitive_cylinder_add(radius=foot_radius, depth=foot_height, location=(pos[0], pos[1], foot_height / 2))
        foot = bpy.context.active_object
        foot.name = f"Foot_{i}"
        foot.data.materials.append(mat_body)

    # Organization: Parent parts to the body
    door.parent = body
    handle.parent = door
    glass_top.parent = body

if __name__ == "__main__":
    clear_scene()
    create_mini_fridge()
