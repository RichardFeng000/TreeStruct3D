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
    return mat

def create_box(name, w, h, d, location, material=None):
    """Creates a box using bmesh to avoid scale application issues."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Create cube centered at origin with size 1, then scale and translate
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale the bmesh vertices directly to avoid bpy.ops.object.transform_apply
    # The default cube is -0.5 to 0.5 in each axis (size=1).
    for v in bm.verts:
        v.co.x *= w
        v.co.y *= h
        v.co.z *= d
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    if material:
        obj.data.materials.append(material)
    return obj

def main():
    clear_scene()

    # Dimensions (in meters)
    WIDTH = 0.6  # External width
    HEIGHT = 1.2 # External height
    DEPTH = 0.3  # External depth
    THICKNESS = 0.02  # Panel thickness
    SHELF_COUNT = 2

    # Material (White appearance)
    white_mat = create_material("BookcaseWhite", (0.9, 0.9, 0.9, 1.0))

    # Coordinate mapping: 
    # X = Width, Y = Height, Z = Depth
    
    # Side Panels (Left and Right) - Full height
    left_side = create_box("Side_L", THICKNESS, HEIGHT, DEPTH, 
                           (-WIDTH/2 + THICKNESS/2, 0, 0), white_mat)
    right_side = create_box("Side_R", THICKNESS, HEIGHT, DEPTH, 
                            (WIDTH/2 - THICKNESS/2, 0, 0), white_mat)

    # Top and Bottom Panels - Fit between the sides
    inner_width = WIDTH - (2 * THICKNESS)
    top_panel = create_box("Top", inner_width, THICKNESS, DEPTH, 
                           (0, HEIGHT/2 - THICKNESS/2, 0), white_mat)
    bottom_panel = create_box("Bottom", inner_width, THICKNESS, DEPTH, 
                              (0, -HEIGHT/2 + THICKNESS/2, 0), white_mat)

    # Back Panel - Thin sheet fitting inside the outer frame and behind other panels
    back_panel = create_box("Back", WIDTH - THICKNESS, HEIGHT - THICKNESS, THICKNESS/4, 
                            (0, 0, -DEPTH/2 + THICKNESS/8), white_mat)

    # Internal Shelves
    shelf_spacing = (HEIGHT - (2 * THICKNESS)) / (SHELF_COUNT + 1)
    for i in range(SHELF_COUNT):
        y_pos = -HEIGHT/2 + THICKNESS + (i + 1) * shelf_spacing
        create_box(f"Shelf_{i+1}", inner_width, THICKNESS, DEPTH - THICKNESS, 
                   (0, y_pos, 0), white_mat)

    # --- Mounting Holes ---
    hole_radius = 0.008  # 8mm radius
    
    # Hole positions relative to the side panel center (X, Y, Z)
    # Placed on the sides near corners
    hole_offsets = [
        (0, HEIGHT/2 - 0.05, DEPTH/2 - 0.05), # Top Rear
        (0, HEIGHT/2 - 0.05, -DEPTH/2 + 0.05),# Top Front
        (0, -HEIGHT/2 + 0.05, DEPTH/2 - 0.05),# Bottom Rear
        (0, -HEIGHT/2 + 0.05, -DEPTH/2 + 0.05),# Bottom Front
    ]

    def add_holes_to_panel(panel):
        for offset in hole_offsets:
            # Calculate world position for the cutter
            loc = (panel.location[0], offset[1], offset[2])
            
            # Create a cylinder as boolean cutter
            bpy.ops.mesh.primitive_cylinder_add(
                radius=hole_radius, 
                depth=THICKNESS * 3, 
                location=loc, 
                rotation=(0, math.radians(90), 0)
            )
            cutter = bpy.context.active_object
            
            # Apply Boolean Modifier to the panel
            bool_mod = panel.modifiers.new(name="MountHole", type='BOOLEAN')
            bool_mod.operation = 'DIFFERENCE'
            bool_mod.object = cutter
            
            # Set active object and apply modifier
            bpy.context.view_layer.objects.active = panel
            bpy.ops.object.modifier_apply(modifier=bool_mod.name)
            
            # Remove the cutter object
            bpy.data.objects.remove(cutter, do_unlink=True)

    add_holes_to_panel(left_side)
    add_holes_to_panel(right_side)

    # --- Final Join ---
    bpy.ops.object.select_all(action='DESELECT')
    objs_to_join = [obj for obj in bpy.data.objects if "Side" in obj.name or 
                    "Top" in obj.name or "Bottom" in obj.name or 
                    "Back" in obj.name or "Shelf" in obj.name]
    
    for obj in objs_to_join:
        obj.select_set(True)
    
    if objs_to_join:
        bpy.context.view_layer.objects.active = objs_to_join[0]
        bpy.ops.object.join()
        bpy.context.active_object.name = "CompactBookcase"

if __name__ == "__main__":
    main()
