import bpy
import bmesh
import math

def clear_scene():
    """Removes all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.8):
    """Creates a simple wood-toned material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Using a rich dark brown for "dark wood-toned"
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Roughness'].default_value = roughness
    
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_box(name, w, d, h, location=(0, 0, 0), material=None):
    """Creates a box mesh with specific dimensions."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale the cube to desired dimensions
    for v in bm.verts:
        v.co.x *= w
        v.co.y *= d
        v.co.z *= h
        
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    
    # Bevel for realism
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.003
    bevel.segments = 3
    
    if material:
        obj.data.materials.append(material)
        
    return obj

def build_detailed_door(cab_w, cab_h, wall_thick, kick_h, material):
    """Creates a door with a frame and recessed center panel."""
    # The door fits within the outer carcass dimensions but leaves slight gaps for clearance
    door_w = cab_w - 0.01
    door_h = cab_h - kick_h - wall_thick - 0.01
    door_thick = 0.02
    frame_width = 0.04
    panel_inset = 0.005
    
    parts = []
    
    # Door Frame - Top/Bottom rails
    rail_h = frame_width
    top_rail = create_box("DoorTopRail", door_w, door_thick, rail_h, material=material)
    bottom_rail = create_box("DoorBotRail", door_w, door_thick, rail_h, material=material)
    top_rail.location.z = (door_h / 2) - (rail_h / 2)
    bottom_rail.location.z = -(door_h / 2) + (rail_h / 2)
    parts.append(top_rail)
    parts.append(bottom_rail)
    
    # Door Frame - Left/Right stiles
    stile_w = frame_width
    stile_h = door_h - (2 * rail_h)
    left_stile = create_box("DoorLeftStile", stile_w, door_thick, stile_h, material=material)
    right_stile = create_box("DoorRightStile", stile_w, door_thick, stile_h, material=material)
    left_stile.location.x = -(door_w / 2) + (stile_w / 2)
    right_stile.location.x = (door_w / 2) - (stile_w / 2)
    parts.append(left_stile)
    parts.append(right_stile)
    
    # Center Panel (Recessed)
    panel_w = door_w - (2 * frame_width)
    panel_h = door_h - (2 * frame_width)
    panel_thick = door_thick - panel_inset
    center_panel = create_box("DoorPanel", panel_w, panel_thick, panel_h, material=material)
    center_panel.location.y = - (panel_inset / 2)
    parts.append(center_panel)
    
    return parts, door_w, door_h

def build_cabinet():
    clear_scene()
    
    # Constants
    cab_w = 0.6
    cab_d = 0.4
    cab_h = 2.1
    wall_thick = 0.02
    kick_h = 0.1
    
    # Material: Rich Dark Wood Tone (Dark Brown/Walnut)
    dark_wood_mat = create_material("DarkWood", (0.08, 0.04, 0.02, 1.0), roughness=0.7)
    handle_mat = create_material("HandleMat", (0.1, 0.1, 0.1, 1.0), roughness=0.3)
    
    # 1. Carcass Assembly
    # The carcass is centered on Y. Front face at +cab_d/2, back face at -cab_d/2.
    side_l = create_box("SideL", wall_thick, cab_d, cab_h, location=(-cab_w/2 + wall_thick/2, 0, cab_h/2), material=dark_wood_mat)
    side_r = create_box("SideR", wall_thick, cab_d, cab_h, location=(cab_w/2 - wall_thick/2, 0, cab_h/2), material=dark_wood_mat)
    
    top = create_box("Top", cab_w, cab_d, wall_thick, location=(0, 0, cab_h - wall_thick/2), material=dark_wood_mat)
    bottom = create_box("Bottom", cab_w, cab_d, wall_thick, location=(0, 0, wall_thick/2), material=dark_wood_mat)
    
    # Back Panel - flush with back face (-cab_d/2)
    back = create_box("Back", cab_w - (wall_thick * 2), wall_thick, cab_h - (wall_thick * 2), location=(0, -cab_d/2 + wall_thick/2, cab_h/2), material=dark_wood_mat)
    
    # Kickplate - at the bottom front
    kick = create_box("Kickplate", cab_w - (wall_thick * 2), 0.05, kick_h, location=(0, cab_d/2 - 0.025, kick_h/2 + wall_thick), material=dark_wood_mat)

    # 2. Door Assembly
    door_parts, door_w, door_h = build_detailed_door(cab_w, cab_h, wall_thick, kick_h, dark_wood_mat)
    
    # Position the door flush with the front of the cabinet (Y = +cab_d/2)
    door_y = cab_d / 2 - 0.01 # Slight offset so it's not z-fighting perfectly
    actual_door_z = (cab_h - wall_thick * 2 - kick_h) / 2 + kick_h + wall_thick
    
    for part in door_parts:
        part.location.y += door_y
        part.location.z += actual_door_z

    # 3. Handle
    handle_w = 0.015
    handle_d = 0.04
    handle_h = 0.12
    handle = create_box("Handle", handle_w, handle_d, handle_h, material=handle_mat)
    # Position: Right side of door, mid-height, slightly protruding from the face
    handle.location = (door_w/2 - 0.05, door_y + 0.01, actual_door_z)
    handle.modifiers["Bevel"].width = 0.002

    # Join everything into one object
    bpy.ops.object.select_all(action='DESELECT')
    all_objects = [side_l, side_r, top, bottom, back, kick, handle] + door_parts
    for obj in all_objects:
        obj.select_set(True)
        
    bpy.context.view_layer.objects.active = top 
    bpy.ops.object.join()
    
    final_cabinet = bpy.context.active_object
    final_cabinet.name = "TallCabinet"

if __name__ == "__main__":
    build_cabinet()
