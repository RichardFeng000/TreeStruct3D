import bpy
import bmesh
import random
import math
from mathutils import Vector

def setup_scene():
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
        # Set base color and slightly reduce specular for a matte canvas look
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.8
    return mat

def create_frame(width, height, depth, thickness):
    """Creates the rectangular wooden frame as four separate slats."""
    slats = []
    # Top & Bottom
    for z in [height/2, -height/2]:
        bpy.ops.mesh.primitive_cube_add(size=1)
        s = bpy.context.active_object
        s.scale = (width, depth, thickness)
        s.location = (0, 0, z)
        slats.append(s)
    # Left & Right
    for x in [width/2, -width/2]:
        bpy.ops.mesh.primitive_cube_add(size=1)
        s = bpy.context.active_object
        s.scale = (thickness, depth, height - thickness * 2)
        s.location = (x, 0, 0)
        slats.append(s)

    # Join slats into one object for convenience
    bpy.ops.object.select_all(action='DESELECT')
    for s in slats:
        s.select_set(True)
    bpy.context.view_layer.objects.active = slats[0]
    bpy.ops.object.join()
    
    final_frame = bpy.context.active_object
    final_frame.name = "WoodenFrame"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return final_frame

def create_canvas_bg(width, height, thickness):
    """Creates the main canvas panel."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    canvas = bpy.context.active_object
    canvas.name = "CanvasBackground"
    # Scale to fit inside frame (assuming frame border is 0.03 each side)
    canvas.scale = (width - 0.06, thickness, height - 0.06)
    # Position so front face is exactly at Y=0
    canvas.location = (0, -thickness/2, 0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return canvas

def create_painting_element(name, width, height, color_mat, pos_x, pos_z, is_organic=False):
    """Creates an element of the painting placed slightly in front of the background."""
    # All elements sit just above Y=0 to avoid z-fighting with canvas background
    y_pos = 0.001 
    thickness = 0.002

    if not is_organic:
        # Rectangular block
        bpy.ops.mesh.primitive_cube_add(size=1)
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = (width, thickness, height)
        obj.location = (pos_x, y_pos + thickness/2, pos_z)
    else:
        # Organic patch using BMesh
        bm = bmesh.new()
        segments = 16
        radius = width / 2
        verts = []
        for i in range(segments):
            angle = (2 * math.pi / segments) * i
            r = radius * random.uniform(0.7, 1.3)
            vx = math.cos(angle) * r
            vz = math.sin(angle) * r
            verts.append(bm.verts.new((vx, 0, vz)))
        
        bm.faces.new(verts)
        # Extrude for small thickness
        bmesh.ops.extrude_face_region(bm, geom=bm.faces)
        for v in bm.verts:
            if v.index >= segments: 
                v.co.y += thickness

        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        bm.to_mesh(mesh)
        bm.free()
        obj.location = (pos_x, y_pos, pos_z)

    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(color_mat)
    return obj

def main():
    setup_scene()

    # Dimensions
    W, H = 0.8, 1.2
    D = 0.04 # Total depth of frame
    T_bg = 0.01 # Thickness of the canvas board itself
    
    # Materials - Adjusted for clarity and contrast
    mat_wood = create_material("Wood", (0.76, 0.65, 0.5, 1.0))       # Light tan wood-grain
    mat_bg = create_material("CanvasBG", (0.3, 0.5, 0.6, 1.0))      # Clearer pale blue-teal
    mat_orange = create_material("OrangeTan", (0.85, 0.5, 0.3, 1.0)) # Orange-tan
    mat_green1 = create_material("Green", (0.1, 0.3, 0.1, 1.0))     # Dark green
    mat_green2 = create_material("Olive", (0.4, 0.4, 0.2, 1.0))    # Olive

    # Frame
    frame_obj = create_frame(W, H, D, 0.03)
    frame_obj.data.materials.append(mat_wood)

    # Canvas Background
    canvas_obj = create_canvas_bg(W, H, T_bg)
    canvas_obj.data.materials.append(mat_bg)

    # Orange-Tan rectangular block (placed centrally but offset)
    create_painting_element("OrangeBlock", 0.2, 0.3, mat_orange, 0.15, 0.1, is_organic=False)

    # Organic patches (Green and Olive) - scattered composition
    patch_configs = [
        (0.1, 0.4, 0.18, mat_green1),   # x, z, size, mat
        (-0.25, -0.2, 0.22, mat_green2),
        (0.0, -0.5, 0.25, mat_green1),
        (-0.1, 0.3, 0.15, mat_green2),
        (0.3, -0.4, 0.2, mat_green1)
    ]

    for i, (px, pz, size, mat) in enumerate(patch_configs):
        create_painting_element(f"Patch_{i}", size, size, mat, px, pz, is_organic=True)

if __name__ == "__main__":
    main()
