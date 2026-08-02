import bpy
import bmesh
import math

def clear_scene():
    """Clears the default scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        # Make it look clean white and slightly matte
        bsdf.inputs['Roughness'].default_value = 0.8
    return mat

def create_box(name, w, d, h, location, material=None):
    """Creates a box using bmesh. X=Width, Y=Depth, Z=Height."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    for v in bm.verts:
        v.co.x *= w
        v.co.y *= d
        v.co.z *= h
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    if material:
        obj.data.materials.append(material)
    return obj

def main():
    clear_scene()

    # Dimensions (meters)
    WIDTH = 0.6     # X axis
    DEPTH = 0.3     # Y axis
    HEIGHT = 1.2    # Z axis
    THICKNESS = 0.02
    SHELF_COUNT = 2

    white_mat = create_material("BookcaseWhite", (0.95, 0.95, 0.95, 1.0))

    # Side Panels - Full height, placed at ends of width
    left_side = create_box("Side_L", THICKNESS, DEPTH, HEIGHT, 
                           (-WIDTH/2 + THICKNESS/2, 0, 0), white_mat)
    right_side = create_box("Side_R", THICKNESS, DEPTH, HEIGHT, 
                            (WIDTH/2 - THICKNESS/2, 0, 0), white_mat)

    # Top and Bottom Panels - Fit between sides
    inner_width = WIDTH - (2 * THICKNESS)
    top_panel = create_box("Top", inner_width, DEPTH, THICKNESS, 
                           (0, 0, HEIGHT/2 - THICKNESS/2), white_mat)
    bottom_panel = create_box("Bottom", inner_width, DEPTH, THICKNESS, 
                              (0, 0, -HEIGHT/2 + THICKNESS/2), white_mat)

    # Back Panel - Covers the rear
    back_panel = create_box("Back", WIDTH, THICKNESS/3, HEIGHT, 
                            (0, DEPTH/2 - THICKNESS/6, 0), white_mat)

    # Internal Shelves - Distributed along Z
    shelf_spacing = (HEIGHT - (2 * THICKNESS)) / (SHELF_COUNT + 1)
    for i in range(SHELF_COUNT):
        z_pos = -HEIGHT/2 + THICKNESS + (i + 1) * shelf_spacing
        create_box(f"Shelf_{i+1}", inner_width, DEPTH - THICKNESS, THICKNESS, 
                   (0, -THICKNESS/2, z_pos), white_mat)

    # --- Mounting Holes ---
    hole_radius = 0.01  # Slightly larger for visibility (10mm)
    
    # Hole positions relative to panel center (X, Y, Z)
    # Placed at the four corners of the side panels' outer faces
    hole_offsets = [
        (0, DEPTH/2 - 0.05, HEIGHT/2 - 0.1),  # Top Rear
        (0, -DEPTH/2 + 0.05, HEIGHT/2 - 0.1), # Top Front (visible)
        (0, DEPTH/2 - 0.05, -HEIGHT/2 + 0.1), # Bottom Rear
        (0, -DEPTH/2 + 0.05, -HEIGHT/2 + 0.1),# Bottom Front (visible)
    ]

    def add_holes_to_panel(panel):
        for offset in hole_offsets:
            loc = (panel.location[0], offset[1], offset[2])
            
            # Create a cylinder as boolean cutter along X axis
            bpy.ops.mesh.primitive_cylinder_add(
                radius=hole_radius, 
                depth=THICKNESS * 3, 
                location=loc, 
                rotation=(0, math.radians(90), 0)
            )
            cutter = bpy.context.active_object
            
            bool_mod = panel.modifiers.new(name="MountHole", type='BOOLEAN')
            bool_mod.operation = 'DIFFERENCE'
            bool_mod.object = cutter
            
            bpy.context.view_layer.objects.active = panel
            bpy.ops.object.modifier_apply(modifier=bool_mod.name)
            
            bpy.data.objects.remove(cutter, do_unlink=True)

    add_holes_to_panel(left_side)
    add_holes_to_panel(right_side)

    # --- Final Join ---
    bpy.ops.object.select_all(action='DESELECT')
    objs_to_join = [obj for obj in bpy.data.objects if any(k in obj.name for k in ["Side", "Top", "Bottom", "Back", "Shelf"])]
    
    for obj in objs_to_join:
        obj.select_set(True)
    
    if objs_to_join:
        bpy.context.view_layer.objects.active = objs_to_join[0]
        bpy.ops.object.join()
        bpy.context.active_object.name = "CompactBookcase"

if __name__ == "__main__":
    main()
