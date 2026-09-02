import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Clear all existing objects from the scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_box(name, size, location):
    """Helper to create a box mesh with specific dimensions and location."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    # Scale the cube to desired dimensions
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
        v.co += Vector(location)
    
    bm.to_mesh(mesh)
    bm.free()
    return obj

def apply_bevel(obj, width=0.005):
    """Adds and applies a bevel modifier to the object."""
    bev = obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = width
    bev.segments = 3
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Bevel")

def create_dining_table():
    # --- Dimensions ---
    TABLE_W = 1.0  # X axis (Width)
    TABLE_D = 1.0  # Y axis (Depth)
    TABLE_T = 0.04 # Thickness of tabletop
    LEG_H = 0.72   # Height from floor to bottom of tabletop
    SLED_WIDTH = 0.8  # Total width of the U-frames along Y
    SLED_SPACING = 0.6 # Distance between the two U-frames along X
    
    # Sled Profile: Flat bars rather than square posts
    BAR_W = 0.06   # The 'flat' dimension (width)
    BAR_T = 0.02   # The 'thin' dimension (thickness)
    SHELF_H = 0.18  # Height of the shelf from floor

    # --- Tabletop: Wood Grain effect via planks ---
    # Using a larger number of narrower planks for a more realistic grain look
    PLANK_COUNT = 12
    plank_w = TABLE_W / PLANK_COUNT
    gap = 0.003
    for i in range(PLANK_COUNT):
        x_pos = -TABLE_W/2 + (i * plank_w) + plank_w/2
        create_box(f"Plank_{i}", 
                   (plank_w - gap, TABLE_D, TABLE_T), 
                   (x_pos, 0, LEG_H + TABLE_T/2))

    # --- Sled Base: Two Inverted-U shaped legs ---
    # Each U-frame is in the YZ plane, flat along the X axis (BAR_T thin, BAR_W wide)
    for side in [-1, 1]: # Left and Right frames
        x_pos = side * (SLED_SPACING / 2)
        
        # Vertical posts of the U - oriented as flat bars
        # We want them to look like sled runners: thin in X, wide in Y? 
        # No, for an inverted U that connects across Y, they should be thin in X, but a bit wider.
        # To make it "sled-style", the width of the bar is visible from the side.
        create_box(f"LegVertL_{side}", (BAR_T, BAR_W, LEG_H), 
                   (x_pos, -SLED_WIDTH/2, LEG_H/2))
        create_box(f"LegVertR_{side}", (BAR_T, BAR_W, LEG_H), 
                   (x_pos, SLED_WIDTH/2, LEG_H/2))
        
        # Top bar of the Inverted-U connecting vertical posts along Y
        create_box(f"LegTop_{side}", (BAR_T, SLED_WIDTH - BAR_W, BAR_T), 
                   (x_pos, 0, LEG_H))

    # --- Shelf Structure: Crossbars and a Surface ---
    crossbar_len = SLED_SPACING # Length between center of frames
    
    # Front crossbar (along X)
    create_box("ShelfBarFront", (crossbar_len, BAR_T, BAR_T), 
               (0, SLED_WIDTH/2, SHELF_H))
    # Back crossbar (along X)
    create_box("ShelfBarBack", (crossbar_len, BAR_T, BAR_T), 
               (0, -SLED_WIDTH/2, SHELF_H))

    # The Shelf Surface itself
    create_box("ShelfSurface", (crossbar_len, SLED_WIDTH - BAR_W, 0.015), 
               (0, 0, SHELF_H + BAR_T/2))

    # Final Polish: Bevel all components for realism
    for obj in bpy.data.objects:
        apply_bevel(obj)

def main():
    clear_scene()
    create_dining_table()

if __name__ == "__main__":
    main()
