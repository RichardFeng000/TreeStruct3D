import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Removes all objects from the current scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_plank(name, width, depth, height, location):
    """Creates a rectangular plank centered at the provided location."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    # Create a cube of size 1 and scale it to the requested dimensions
    bmesh.ops.create_cube(bm, size=1.0)
    
    for v in bm.verts:
        v.co.x *= width / 2
        v.co.y *= depth / 2
        v.co.z *= height / 2
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    return obj

def main():
    clear_scene()

    # --- Parametric Dimensions ---
    B_HEIGHT = 2.1   # Total height of the bookshelf
    B_WIDTH = 0.9    # Overall width
    B_DEPTH = 0.3    # Depth of shelves
    T_THICK = 0.03   # Thickness of planks (slightly thicker for visibility)
    NUM_SHELVES = 6  # Total horizontal tiers

    planks = []

    # 1. Vertical Side Supports
    # Positioned so the outer edge is at +/- B_WIDTH/2
    side_x = (B_WIDTH / 2) - (T_THICK / 2)
    z_center_sides = B_HEIGHT / 2
    
    left_side = create_plank("Side_Left", T_THICK, B_DEPTH, B_HEIGHT, Vector((-side_x, 0, z_center_sides)))
    right_side = create_plank("Side_Right", T_THICK, B_DEPTH, B_HEIGHT, Vector((side_x, 0, z_center_sides)))
    planks.extend([left_side, right_side])

    # 2. Horizontal Shelves
    # The shelves fit BETWEEN the side supports
    inner_width = B_WIDTH - (2 * T_THICK)
    
    # Distribute shelves evenly from bottom to top
    # Bottom shelf center is at T_THICK/2, top shelf center at B_HEIGHT - T_THICK/2
    shelf_interval = (B_HEIGHT - T_THICK) / (NUM_SHELVES - 1)
    
    for i in range(NUM_SHELVES):
        z_pos = (T_THICK / 2) + (i * shelf_interval)
        shelf = create_plank(f"Shelf_{i}", inner_width, B_DEPTH, T_THICK, Vector((0, 0, z_pos)))
        planks.append(shelf)

    # 3. Back Panel
    # A thin sheet covering the back of the unit
    back_thickness = 0.01
    back_panel = create_plank("BackPanel", B_WIDTH, back_thickness, B_HEIGHT, Vector((0, (B_DEPTH / 2) + (back_thickness / 2), z_center_sides)))
    planks.append(back_panel)

    # --- Join into one object ---
    bpy.ops.object.select_all(action='DESELECT')
    for p in planks:
        p.select_set(True)
    
    bpy.context.view_layer.objects.active = planks[0]
    bpy.ops.object.join()
    
    bookshelf = bpy.context.active_object
    bookshelf.name = "Bookshelf"

    # Subtle bevel for realism
    bevel = bookshelf.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.003
    bevel.segments = 3
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = 0.523599 # 30 degrees

    # Final positioning: ensure it is centered and sits on Z=0
    # Since we built from Z=0, the bottom vertices are at 0.
    # We just need to make sure the origin is at the base center for stability.
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    
    # Correcting location so the actual mesh bottom is at Z=0 after moving origin to bounds center
    bbox = bookshelf.bound_box
    min_z_local = min([v[2] for v in bbox])
    bookshelf.location.z -= min_z_local

if __name__ == "__main__":
    main()
