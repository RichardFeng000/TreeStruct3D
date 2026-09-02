import bpy
import bmesh
import math

def clear_scene():
    """Clear all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, rgba, roughness=0.3):
    """Create a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    node_principled.inputs['Base Color'].default_value = rgba
    node_principled.inputs['Roughness'].default_value = roughness
    
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_microwave():
    # Dimensions for a "wide, low-profile" look
    width = 2.4
    height = 1.0
    depth = 1.6
    corner_radius = 0.15
    
    # Materials - Using very dark values to ensure they render as requested
    mat_brown = create_material("DarkBrown", (0.07, 0.04, 0.02, 1.0), roughness=0.4)
    mat_navy = create_material("DarkNavyBlue", (0.01, 0.02, 0.08, 1.0), roughness=0.2)
    mat_dark_gap = create_material("DarkGap", (0.01, 0.01, 0.01, 1.0), roughness=0.8)
    mat_glass = create_material("Glass", (0.02, 0.02, 0.03, 1.0), roughness=0.1)
    
    # --- Main Body ---
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    body = bpy.context.active_object
    body.name = "Microwave_Body"
    body.scale = (width, depth, height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Bevel for rounded corners
    bevel = body.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = corner_radius
    bevel.segments = 12
    
    body.data.materials.append(mat_brown)

    # --- Top Surface (Navy Blue) ---
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    top = bpy.context.active_object
    top.name = "Microwave_Top"
    # Slightly inset to fit within rounded body corners
    top_w = width - (corner_radius * 2)
    top_d = depth - (corner_radius * 2)
    top.scale = (top_w, top_d, 0.05)
    top.location.z = height / 2 + 0.02
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    bev_top = top.modifiers.new(name="Bevel", type='BEVEL')
    bev_top.width = 0.02
    bev_top.segments = 3
    
    top.data.materials.append(mat_navy)

    # --- Door and Front Panel ---
    # Door is shifted to the left, Control panel on right
    door_w = width * 0.65
    door_h = height * 0.8
    door_d = 0.08
    
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    door = bpy.context.active_object
    door.name = "Microwave_Door"
    door.scale = (door_w, door_d, door_h)
    # Center the door assembly relative to the body offset
    door.location = (- (width - door_w)/4, -depth/2 - 0.05, 0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    bev_door = door.modifiers.new(name="Bevel", type='BEVEL')
    bev_door.width = 0.02
    bev_door.segments = 5
    door.data.materials.append(mat_brown)

    # --- Window on Door ---
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    window = bpy.context.active_object
    window.name = "Microwave_Window"
    win_w = door_w * 0.75
    win_h = door_h * 0.6
    window.scale = (win_w, 0.04, win_h)
    window.location = (door.location.x, -depth/2 - 0.06, 0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    window.data.materials.append(mat_glass)

    # --- Door Latch / Handle Detail (Right side of door) ---
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    latch = bpy.context.active_object
    latch.name = "Door_Latch"
    latch.scale = (0.05, 0.12, door_h * 0.4)
    # Position at the right edge of the door slab
    latch.location = (door.location.x + door_w/2 - 0.03, -depth/2 - 0.07, 0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    latch.data.materials.append(mat_brown)

    # --- Ventilation Slots (Front lower edge) ---
    num_slots = 15
    slot_w = 0.06
    slot_h = 0.02
    slot_depth = 0.03 # Thin so they look like slits
    
    start_x = -width/2 + 0.2
    gap = (width - 0.4) / num_slots
    
    for i in range(num_slots):
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        slot = bpy.context.active_object
        slot.scale = (slot_w, slot_depth, slot_h)
        # Place them at the very bottom front edge
        slot.location = (start_x + i * gap, -depth/2 - 0.01, -height/2 + 0.08)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        slot.data.materials.append(mat_dark_gap)

    # --- Control Panel Area (Right side of front face) ---
    panel_w = width * 0.25
    panel_h = height * 0.85
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    panel = bpy.context.active_object
    panel.name = "ControlPanel"
    panel.scale = (panel_w, 0.06, panel_h)
    panel.location = (width/2 - panel_w/2, -depth/2 - 0.03, 0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    panel.data.materials.append(mat_brown)

    # Add small button details to the panel
    for row in range(4):
        for col in range(2):
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            btn = bpy.context.active_object
            btn.scale = (0.07, 0.05, 0.07)
            btn.location = (panel.location.x + (col-0.5)*0.12, -depth/2 - 0.06, (row-1.5)*0.2)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            btn.data.materials.append(mat_dark_gap)

# Execute the process
clear_scene()
create_microwave()
