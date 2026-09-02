import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Clear all existing objects from the scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_bevel_modifier(obj, width=0.003, segments=3):
    """Adds a bevel modifier to soften edges."""
    bev = obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = width
    bev.segments = segments
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Bevel")

def create_box(name, size, location):
    """Helper to create a box mesh."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
        v.co += Vector(location)
    
    bm.to_mesh(mesh)
    bm.free()
    return obj

def create_dining_table():
    # Dimensions
    TABLE_W = 1.0  # X axis
    TABLE_D = 1.0  # Y axis
    TABLE_T = 0.04 # Thickness
    LEG_H = 0.72   # Height to bottom of tabletop
    SLED_WIDTH = 0.8  # The width of the U-shape (along Y)
    SLED_SPACING = 0.6 # Distance between the two U-frames (along X)
    THICKNESS = 0.04 # Thickness of legs and frames
    SHELF_H = 0.18  # Height of shelf bars

    # --- Tabletop (Planks for Wood Grain effect) ---
    PLANK_COUNT = 7
    plank_w = TABLE_W / PLANK_COUNT
    for i in range(PLANK_COUNT):
        x_pos = -TABLE_W/2 + (i * plank_w) + plank_w/2
        # Slight gap between planks to make the "grain" structure visible
        create_box(f"Plank_{i}", 
                   (plank_w - 0.005, TABLE_D, TABLE_T), 
                   (x_pos, 0, LEG_H + TABLE_T/2))

    # --- Sled Base: Two Inverted-U shaped legs ---
    # These are parallel to the Y axis, spaced along X
    for side in [-1, 1]: # Left frame and Right frame
        x_pos = side * (SLED_SPACING / 2)
        
        # Vertical posts of the U
        create_box(f"LegVertL_{side}", (THICKNESS, THICKNESS, LEG_H), 
                   (x_pos, -SLED_WIDTH/2, LEG_H/2))
        create_box(f"LegVertR_{side}", (THICKNESS, THICKNESS, LEG_H), 
                   (x_pos, SLED_WIDTH/2, LEG_H/2))
        
        # Top bar of the Inverted-U (connecting vertical posts)
        # This sits right under the tabletop
        create_box(f"LegTop_{side}", (THICKNESS, SLED_WIDTH, THICKNESS), 
                   (x_pos, 0, LEG_H))

    # --- Shelf Structure: Crossbars connecting the two U-frames ---
    # The crossbars run along X axis at SHELF_H
    crossbar_len = SLED_SPACING - THICKNESS # Fitting between posts
    
    # Front bar
    create_box("ShelfFront", (crossbar_len, THICKNESS, THICKNESS), 
               (0, SLED_WIDTH/2, SHELF_H))
    # Back bar
    create_box("ShelfBack", (crossbar_len, THICKNESS, THICKNESS), 
               (0, -SLED_WIDTH/2, SHELF_H))

    # Final Polish: Bevel all components
    for obj in bpy.data.objects:
        create_bevel_modifier(obj)

def main():
    clear_scene()
    create_dining_table()

if __name__ == "__main__":
    main()
