import bpy
import bmesh
import random

def clear_scene():
    """Clear the default scene of all objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_rounded_cube(name, size, location, bevel_width=0.05, segments=3):
    """Creates a cube and applies a bevel modifier to give it a padded look."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    
    # Scale the cube to desired size (width, depth, height)
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Add Bevel Modifier for rounded edges
    bev = obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = bevel_width
    bev.segments = segments
    
    # Add Subdivision Surface for smoother appearance
    subdiv = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subdiv.levels = 1
    subdiv.render_levels = 2
    
    return obj

def create_sectional_sofa():
    # --- Parameters ---
    cushion_w = 0.8  # Width of a single seat cushion
    cushion_d = 0.8  # Depth of a standard seat cushion
    cushion_h = 0.25 # Height of the cushions
    chaise_ext = 0.7 # Extra depth for chaise lounge
    base_h = 0.12    # Height of the base frame
    backrest_w = 0.2 # Thickness of backrest
    armrest_w = 0.25 # Width of armrests
    armrest_h = 0.5  # Height of armrests
    
    # Coordinate Setup:
    # Main axis along X, Chaise extends in -Y direction.
    num_seats = 3
    # Seat center X positions
    seat_x = [ (i - (num_seats-1)/2) * cushion_w for i in range(num_seats)]
    
    # Y references: Backrest at y=0, seat starts at y=0 and goes to y=-cushion_d
    y_backrest_center = -backrest_w / 2
    y_seat_start = -backrest_w
    y_seat_end = y_seat_start - cushion_d
    y_chaise_end = y_seat_end - chaise_ext

    # 1. Base Frame (L-shaped)
    # Main base block for the standard seats
    base_main_size = (num_seats * cushion_w, cushion_d + backrest_w, base_h)
    base_main_loc = (0, (y_seat_start + y_seat_end)/2, base_h/2)
    create_rounded_cube("BaseMain", base_main_size, base_main_loc, bevel_width=0.02)
    
    # Chaise extension base block
    base_chaise_size = (cushion_w, chaise_ext, base_h)
    base_chaise_loc = (seat_x[0], (y_seat_end + y_chaise_end)/2, base_h/2)
    create_rounded_cube("BaseChaise", base_chaise_size, base_chaise_loc, bevel_width=0.02)

    # 2. Seat Cushions
    for i in range(num_seats):
        if i == 0: # The Chaise Lounge seat
            depth = cushion_d + chaise_ext
            y_pos = (y_seat_start + y_chaise_end) / 2
        else: # Regular seats
            depth = cushion_d
            y_pos = (y_seat_start + y_seat_end) / 2
            
        create_rounded_cube(f"Cushion_{i}", 
                           (cushion_w, depth, cushion_h), 
                           (seat_x[i], y_pos, base_h + cushion_h/2),
                           bevel_width=0.06)

    # 3. Backrests (varying heights)
    for i in range(num_seats):
        # Chaise lounge usually has a lower backrest or only one side; here we provide varied height segments
        h = random.uniform(0.4, 0.6) if i > 0 else 0.35
        create_rounded_cube(f"Backrest_{i}", 
                           (cushion_w, backrest_w, h), 
                           (seat_x[i], y_backrest_center, base_h + cushion_h + h/2),
                           bevel_width=0.05)

    # 4. Armrests (Solid ends of the L-shape)
    # Right end armrest
    right_arm_x = seat_x[-1] + (cushion_w/2) + (armrest_w/2)
    right_arm_y = (y_seat_start + y_seat_end) / 2
    create_rounded_cube("Armrest_Right", 
                       (armrest_w, cushion_d + backrest_w, armrest_h), 
                       (right_arm_x, right_arm_y, base_h + armrest_h/2),
                       bevel_width=0.04)

    # Chaise end armrest (the far front of the L)
    left_arm_x = seat_x[0]
    left_arm_y = y_chaise_end - (armrest_w / 2) # Position at very end of chaise extension
    # Adjust size to cap the chaise width
    create_rounded_cube("Armrest_ChaiseEnd", 
                       (cushion_w, armrest_w, armrest_h), 
                       (left_arm_x, left_arm_y, base_h + armrest_h/2),
                       bevel_width=0.04)

    # Final cleanup: Join into one object
    bpy.ops.object.select_all(action='SELECT')
    if bpy.context.selected_objects:
        bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
        bpy.ops.object.join()
        bpy.context.active_object.name = "SectionalSofa"

if __name__ == "__main__":
    clear_scene()
    create_sectional_sofa()
