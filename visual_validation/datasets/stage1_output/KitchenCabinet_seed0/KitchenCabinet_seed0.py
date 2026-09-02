import bpy
import bmesh
import math

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_box(name, size, location, color=(0.1, 0.1, 0.1, 1.0)):
    """ Creates a box with specific dimensions and a simple material. """
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Material for "dark tones"
    mat = bpy.data.materials.new(name=f"Mat_{name}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.4
    obj.data.materials.append(mat)
    return obj

def add_bevel(obj):
    bev = obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.003
    bev.segments = 2
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

def create_handle(location, orientation='vertical'):
    """ Creates a small metallic handle. """
    color = (0.6, 0.6, 0.6, 1.0) # Silver/Grey
    if orientation == 'vertical':
        h = create_box("Handle", (0.015, 0.02, 0.1), location, color)
    else:
        h = create_box("Handle", (0.1, 0.02, 0.015), location, color)
    add_bevel(h)
    return h

def main():
    clear_scene()

    # Dimensions
    W = 3.0      # Total Width
    H = 0.9      # Total Height
    D = 0.4      # Total Depth
    T = 0.02     # Material Thickness
    
    # Materials colors
    BODY_COLOR = (0.05, 0.05, 0.07, 1.0) # Dark charcoal/blue tone
    ACCENT_COLOR = (0.12, 0.12, 0.15, 1.0)

    # --- Carcass ---
    # Top and Bottom
    top = create_box("Carcass_Top", (W, D, T), (0, 0, H/2 - T/2), BODY_COLOR)
    bottom = create_box("Carcass_Bottom", (W, D, T), (0, 0, -H/2 + T/2), BODY_COLOR)
    # Sides (Now full height)
    left = create_box("Carcass_Left", (T, D, H - 2*T), (-W/2 + T/2, 0, 0), BODY_COLOR)
    right = create_box("Carcass_Right", (T, D, H - 2*T), (W/2 - T/2, 0, 0), BODY_COLOR)
    # Back panel
    back = create_box("Carcass_Back", (W - 2*T, T, H - 2*T), (0, D/2 - T/2, 0), BODY_COLOR)

    for o in [top, bottom, left, right, back]:
        add_bevel(o)

    # --- Sections ---
    num_sections = 5
    sec_width = W / num_sections
    
    # Vertical dividers
    for i in range(1, num_sections):
        x_pos = -W/2 + (i * sec_width) - T/2 if i == 1 else -W/2 + (i * sec_width) - T/2 # simplified logic below
        # Better X calc:
        div_x = -W/2 + (i * sec_width) - (T/2 if i < num_sections else 0) 
        # Wait, let's be precise. The dividers are at boundaries between sections.
        # Section i goes from -W/2 + i*sec_width to -W/2 + (i+1)*sec_width
        div_x = -W/2 + (i * sec_width) 
        # Adjust center so divider is centered on the boundary line
        div = create_box(f"Divider_{i}", (T, D - T, H - 2*T), (div_x, -T/2, 0), BODY_COLOR)
        add_bevel(div)

    # --- Interior and Doors ---
    for i in range(num_sections):
        sec_center_x = -W/2 + (i * sec_width) + sec_width / 2
        inner_w = sec_width - T # approximate
        
        if i == 1 or i == 3: # Open sections
            # Add a couple of shelves
            num_shelves = 2 if i == 1 else 3
            for s in range(1, num_shelves):
                z_pos = -H/2 + (s * (H / (num_shelves + 1)))
                shelf = create_box(f"Shelf_{i}_{s}", (sec_width - T*1.5, D - T, T), (sec_center_x, -T/2, z_pos), ACCENT_COLOR)
                add_bevel(shelf)
        else: # Closed sections
            # Doors are placed at the front (-D/2)
            door_w = sec_width - 0.01
            door_h = H - 2*T - 0.01
            door_y = -D/2 - T/2
            
            if i == 2: # Split doors (top/bottom)
                d_h_half = (H - 2*T)/2 - 0.01
                # Top door
                d_top = create_box(f"Door_{i}_Top", (door_w, T, d_h_half), (sec_center_x, door_y, (H-2*T)/4 + T/2), ACCENT_COLOR)
                add_bevel(d_top)
                create_handle((sec_center_x + door_w/3, door_y - T/2, (H-2*T)/4), 'vertical')
                # Bottom door
                d_bot = create_box(f"Door_{i}_Bot", (door_w, T, d_h_half), (sec_center_x, door_y, -(H-2*T)/4 - T/2), ACCENT_COLOR)
                add_bevel(d_bot)
                create_handle((sec_center_x + door_w/3, door_y - T/2, -(H-2*T)/4), 'vertical')
            else: # Full doors
                door = create_box(f"Door_{i}", (door_w, T, door_h), (sec_center_x, door_y, 0), ACCENT_COLOR)
                add_bevel(door)
                # Handle position based on side
                handle_x = sec_center_x + door_w/3 if i < 2 else sec_center_x - door_w/3
                create_handle((handle_x, door_y - T/2, 0), 'vertical')

if __name__ == "__main__":
    main()
