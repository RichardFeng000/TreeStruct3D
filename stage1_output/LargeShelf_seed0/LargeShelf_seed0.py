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
    # Create a cube of size 1.0 (vertices at +/- 0.5)
    bmesh.ops.create_cube(bm, size=1.0)
    
    # To get total width W, we multiply the existing coordinates (+/- 0.5) by W.
    # Result: vertices will be at +/- W/2, spanning exactly W.
    for v in bm.verts:
        v.co.x *= width
        v.co.y *= depth
        v.co.z *= height
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    return obj

def main():
    clear_scene()

    # --- Parametric Dimensions ---
    B_HEIGHT = 2.1   # Total height
    B_WIDTH = 0.9    # Overall width
    B_DEPTH = 0.3    # Depth of shelves
    T_THICK = 0.03   # Thickness of material
    NUM_SHELVES = 6  # Number of horizontal tiers

    planks = []

    # 1. Vertical Side Supports
    # Outer edges at +/- B_WIDTH/2. Centers are at +/- (B_WIDTH/2 - T_THICK/2)
    side_x = (B_WIDTH / 2) - (T_THICK / 2)
    z_center_sides = B_HEIGHT / 2
    
    left_side = create_plank("Side_Left", T_THICK, B_DEPTH, B_HEIGHT, Vector((-side_x, 0, z_center_sides)))
    right_side = create_plank("Side_Right", T_THICK, B_DEPTH, B_HEIGHT, Vector((side_x, 0, z_center_sides)))
    planks.extend([left_side, right_side])

    # 2. Horizontal Shelves
    # They fit BETWEEN the side supports. Total width = B_WIDTH - (2 * T_THICK)
    inner_width = B_WIDTH - (2 * T_THICK)
    
    # Space shelves evenly from Z=0 to Z=B_HEIGHT
    # We place them at intervals including top and bottom edges.
    if NUM_SHELVES > 1:
        shelf_interval = (B_HEIGHT - T_THICK) / (NUM_SHELVES - 1)
    else:
        shelf_interval = 0

    for i in range(NUM_SHELVES):
        z_pos = (T_THICK / 2) + (i * shelf_interval)
        shelf = create_plank(f"Shelf_{i}", inner_width, B_DEPTH, T_THICK, Vector((0, 0, z_pos)))
        planks.append(shelf)

    # 3. Back Panel (Thin sheet for stability/look)
    back_thickness = 0.01
    # Centered at Y = B_DEPTH/2 (approx), spanning full width and height
    back_panel = create_plank("BackPanel", B_WIDTH, back_thickness, B_HEIGHT, Vector((0, (B_DEPTH / 2) + (back_thickness / 2), z_center_sides)))
    planks.append(back_panel)

    # --- Combine and Finalize ---
    bpy.ops.object.select_all(action='DESELECT')
    for p in planks:
        p.select_set(True)
    
    bpy.context.view_layer.objects.active = planks[0]
    bpy.ops.object.join()
    
    bookshelf = bpy.context.active_object
    bookshelf.name = "Bookshelf"

    # White material for the "clean white appearance"
    mat = bpy.data.materials.new(name="WhitePaint")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.9, 0.9, 0.9, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.4
    bookshelf.data.materials.append(mat)

    # Subtle bevel for realism
    bevel = bookshelf.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.002
    bevel.segments = 3
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = 0.523599 # 30 degrees

    # Center origin and set base to Z=0
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    bbox = bookshelf.bound_box
    min_z_local = min([v[2] for v in bbox])
    bookshelf.location.z -= min_z_local

if __name__ == "__main__":
    main()
