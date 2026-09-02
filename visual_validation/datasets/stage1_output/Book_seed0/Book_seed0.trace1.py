import bpy
import bmesh
import math

def clear_scene():
    """Removes all default objects from the scene."""
    if "Cube" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
    if "Camera" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Camera"], do_unlink=True)
    if "Light" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Light"], do_unlink=True)

def create_cube(name, size, location):
    """Helper to create a cube with specific dimensions and location."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj

def create_book():
    # Parameters (meters)
    W = 0.16       # Width of page block
    H = 0.24       # Height of the book
    T = 0.035      # Thickness of page block
    Cover_T = 0.004 # Hardcover plate thickness
    Overhang = 0.003 # How much cover extends beyond pages (Y axis)
    SpineW = 0.015  # Width of the spine

    total_w = W + SpineW
    total_t = T + 2 * Cover_T
    
    # Coordinates for centering logic
    # We'll build relative to a reference and then shift to center at origin
    
    # 1. Page Block
    # Centered in X (excluding spine), centered in Y, Z between covers
    pages = create_cube("PageBlock", 
                        (W, H - 2 * Overhang, T), 
                        (W/2 + SpineW, 0, Cover_T + T/2))
    
    # 2. Hardcover parts
    # Back Cover (bottom)
    back_cover = create_cube("BackCover", 
                             (total_w, H, Cover_T), 
                             (total_w / 2, 0, Cover_T / 2))
    
    # Front Cover (top)
    front_cover = create_cube("FrontCover", 
                              (total_w, H, Cover_T), 
                              (total_w / 2, 0, T + Cover_T + Cover_T / 2))
    
    # Spine
    spine = create_cube("Spine", 
                        (SpineW, H, total_t), 
                        (SpineW / 2, 0, total_t / 2))
    
    # Join cover parts into one object
    bpy.ops.object.select_all(action='DESELECT')
    back_cover.select_set(True)
    front_cover.select_set(True)
    spine.select_set(True)
    bpy.context.view_layer.objects.active = spine
    bpy.ops.object.join()
    cover_obj = bpy.context.active_object
    cover_obj.name = "HardCover"

    # Add Bevel to cover for realistic edges
    bev = cover_obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.002
    bev.segments = 3
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(30)

    # Add Spine Ribs (traditional binding bands)
    rib_count = 4
    rib_thickness = 0.004
    for i in range(rib_count):
        # Space ribs evenly along the height
        y_pos = -H/2 + (H * (i + 1) / (rib_count + 1))
        rib = create_cube(f"Rib_{i}", 
                          (SpineW * 1.05, rib_thickness, total_t), 
                          (SpineW / 2, y_pos, total_t / 2))
        
        # Join rib to cover
        bpy.ops.object.select_all(action='DESELECT')
        rib.select_set(True)
        cover_obj.select_set(True)
        bpy.context.view_layer.objects.active = cover_obj
        bpy.ops.object.join()

    # Center the whole assembly at origin (0,0,0)
    # Current center is approx (total_w/2, 0, total_t/2)
    shift_x = -total_w / 2
    shift_y = 0
    shift_z = -total_t / 2
    
    pages.location = (pages.location[0] + shift_x, pages.location[1] + shift_y, pages.location[2] + shift_z)
    cover_obj.location = (cover_obj.location[0] + shift_x, cover_obj.location[1] + shift_y, cover_obj.location[2] + shift_z)

if __name__ == "__main__":
    clear_scene()
    create_book()
