import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_principled.inputs['Base Color'].default_value = color
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_backplate():
    """Creates the rectangular backplate and its border frame."""
    width = 0.8
    height = 0.4
    depth = 0.02
    frame_thickness = 0.03
    
    # Material for panel (lighter) and frame (darker)
    panel_mat = create_material("PanelMat", (0.9, 0.9, 0.9, 1))
    frame_mat = create_material("FrameMat", (0.1, 0.1, 0.1, 1))

    # Main Panel
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    panel = bpy.context.active_object
    panel.name = "Backplate_Panel"
    panel.scale = (width, depth, height)
    panel.data.materials.append(panel_mat)
    bpy.ops.object.transform_apply(scale=True)

    # Create the frame border
    # Top and Bottom bars
    for z in [height/2 + frame_thickness/2, -height/2 - frame_thickness/2]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, z))
        bar = bpy.context.active_object
        bar.scale = (width + frame_thickness*2, depth * 1.2, frame_thickness)
        bar.data.materials.append(frame_mat)
        bpy.ops.object.transform_apply(scale=True)

    # Left and Right bars
    for x in [-(width/2 + frame_thickness/2), width/2 + frame_thickness/2]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 0))
        bar = bpy.context.active_object
        bar.scale = (frame_thickness, depth * 1.2, height)
        bar.data.materials.append(frame_mat)
        bpy.ops.object.transform_apply(scale=True)

def create_hook(x_pos):
    """Creates a curved J-hook at the specified X position."""
    # Hook starts at bottom of plate and curves forward then down
    z_start = -0.15 
    y_start = 0.01
    
    bm = bmesh.new()
    path_points = [
        (0, 0, 0),
        (0, 0.02, 0),
        (0, 0.04, -0.02),
        (0, 0.05, -0.06),
        (0, 0.03, -0.08),
        (0, 0.01, -0.07),
    ]
    
    bmesh.ops.create_circle(bm, radius=0.012, segments=12)
    current_face = bm.faces[:]
    for i in range(1, len(path_points)):
        p_prev = Vector(path_points[i-1])
        p_curr = Vector(path_points[i])
        offset = p_curr - p_prev
        res = bmesh.ops.extrude_face_region(bm, geom=current_face)
        verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BVVert)]
        for v in verts:
            v.co += offset
        current_face = [f for f in res['geom'] if isinstance(f, bmesh.types.BVFace)]

    mesh = bpy.data.meshes.new("HookMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Hook", mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = (x_pos, y_start, z_start)
    
    hook_mat = create_material("HookMat", (0.4, 0.4, 0.4, 1))
    obj.data.materials.append(hook_mat)
    return obj

def create_spatula(style, x_pos):
    """Creates different types of kitchen spatulas."""
    bm = bmesh.new()
    handle_len = 0.25
    handle_w = 0.02
    handle_h = 0.012
    
    # Create handle
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co.x *= (handle_w / 2)
        v.co.y *= (handle_h / 2)
        v.co.z *= (handle_len / 2)

    # Define styles for heads
    if style == "silicone":
        head_w, head_h, head_t = 0.08, 0.14, 0.01
        bmesh.ops.create_cube(bm, size=1)
        for v in bm.verts:
            v.co.z += (handle_len/2 + head_h/2)
            v.co.x *= (head_w / 2)
            v.co.y *= (head_t / 2)
            v.co.z *= (head_h / 2)
    elif style == "metal":
        head_w, head_h, head_t = 0.10, 0.16, 0.005
        bmesh.ops.create_cube(bm, size=1)
        for v in bm.verts:
            v.co.z += (handle_len/2 + head_h/2)
            v.co.x *= (head_w / 2)
            v.co.y *= (head_t / 2)
            v.co.z *= (head_h / 2)
    else: # Fish turner
        head_w, head_h, head_t = 0.12, 0.18, 0.005
        bmesh.ops.create_cube(bm, size=1)
        for v in bm.verts:
            v.co.z += (handle_len/2 + head_h/2)
            v.co.x *= (head_w / 2)
            v.co.y *= (head_t / 2)
            v.co.z *= (head_h / 2)
            if v.co.z > handle_len/2:
                v.co.x += abs(v.co.x) * 0.2 # slight flare

    mesh = bpy.data.meshes.new(f"Spatula_{style}")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(f"Spatula_{style}", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Position the spatula to hang on the hook: 
    # Hook bottom is around z=-0.23, y=0.05. Handle center there.
    obj.location = (x_pos, 0.05, -0.23)
    obj.rotation_euler = (math.radians(2), 0, math.radians(5))
    
    # Color based on style
    if style == "silicone":
        mat = create_material("SpatulaSil", (0.8, 0.1, 0.1, 1)) # Red
    elif style == "metal":
        mat = create_material("SpatulaMet", (0.7, 0.7, 0.8, 1)) # Silver
    else:
        mat = create_material("SpatulaFish", (0.9, 0.9, 0.6, 1)) # Champagne
    obj.data.materials.append(mat)
    
    return obj

def main():
    clear_scene()
    create_backplate()
    
    num_hooks = 5
    start_x = -0.32
    spacing = 0.16
    styles = ["silicone", "metal", "fish", "silicone", "metal"]
    
    for i in range(num_hooks):
        x = start_x + (i * spacing)
        create_hook(x)
        create_spatula(styles[i], x)

if __name__ == "__main__":
    main()
