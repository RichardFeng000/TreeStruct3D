import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
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
    width, height, depth = 0.8, 0.4, 0.03
    frame_w = 0.04
    
    panel_mat = create_material("PanelMat", (0.95, 0.95, 0.95, 1))
    frame_mat = create_material("FrameMat", (0.05, 0.05, 0.05, 1))

    # Main Panel
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    panel = bpy.context.active_object
    panel.scale = (width, depth, height)
    panel.data.materials.append(panel_mat)
    bpy.ops.object.transform_apply(scale=True)

    # Frame Border (Top/Bottom)
    for z in [height/2, -height/2]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, z))
        bar = bpy.context.active_object
        bar.scale = (width + frame_w*2, depth * 1.2, frame_w)
        bar.data.materials.append(frame_mat)
        bpy.ops.object.transform_apply(scale=True)

    # Frame Border (Left/Right)
    for x in [-(width/2 + frame_w/2), width/2 + frame_w/2]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 0))
        bar = bpy.context.active_object
        bar.scale = (frame_w, depth * 1.2, height)
        bar.data.materials.append(frame_mat)
        bpy.ops.object.transform_apply(scale=True)

def create_j_hook(x_pos):
    # Points for the hook curve: start at wall -> out -> down -> slightly in/up
    points = [
        Vector((0, 0, 0)),
        Vector((0, 0.04, 0)),
        Vector((0, 0.06, -0.02)),
        Vector((0, 0.05, -0.06)),
        Vector((0, 0.03, -0.08))
    ]
    
    bm = bmesh.new()
    # Start with a small circle as the base of the hook
    bmesh.ops.create_circle(bm, radius=0.01, segments=12)
    face = bm.faces[0]
    
    for i in range(len(points)-1):
        p_start = points[i]
        p_end = points[i+1]
        direction = p_end - p_start
        
        # Extrude and move
        res = bmesh.ops.extrude_face_region(bm, geom=[face])
        verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BVVert)]
        for v in verts:
            v.co += direction
        face = [f for f in res['geom'] if isinstance(f, bmesh.types.BVFace)][0]

    # Cap the end
    bmesh.ops.contextual_create(bm, geom=face)
    
    mesh = bpy.data.meshes.new("HookMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Hook", mesh)
    bpy.context.collection.objects.link(obj)
    # Position at the bottom of the panel, spaced across X
    obj.location = (x_pos, depth/2, -0.1) 
    
    hook_mat = create_material("HookMat", (0.6, 0.6, 0.6, 1))
    obj.data.materials.append(hook_mat)
    return obj

def create_spatula(style, x_pos):
    bm = bmesh.new()
    # Handle: long cylinder-like box
    h_len, h_rad = 0.2, 0.015
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co.x *= h_rad
        v.co.y *= h_rad
        v.co.z *= (h_len / 2)
    
    # Head: flat plate
    head_w, head_h, head_t = 0.07, 0.13, 0.01
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co.z += (h_len / 2 + head_h / 2)
        v.co.x *= (head_w / 2)
        v.co.y *= (head_t / 2)
        v.co.z *= (head_h / 2)

    mesh = bpy.data.meshes.new(f"Spatula_{style}")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(f"Spatula_{style}", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Hang the spatula on the hook:
    # Hook end is at relative y=0.03, z=-0.08 from its origin (x_pos, depth/2, -0.1)
    # Absolute position of hook tip: (x_pos, depth/2 + 0.03, -0.1 - 0.08) = (x_pos, ~0.045, -0.18)
    # We place the top of the handle there. Handle center is h_len/2 below the tip.
    obj.location = (x_pos, 0.045, -0.18 - (h_len / 2))
    obj.rotation_euler = (math.radians(2), 0, math.radians(-3))
    
    colors = {
        "silicone": (0.8, 0.1, 0.1, 1), # Red
        "metal": (0.7, 0.7, 0.8, 1),    # Silver
        "wood": (0.6, 0.4, 0.2, 1)      # Brown
    }
    mat = create_material(f"Mat_{style}", colors.get(style, (0.5, 0.5, 0.5, 1)))
    obj.data.materials.append(mat)
    return obj

def main():
    clear_scene()
    create_backplate()
    
    num_hooks = 5
    spacing = 0.14
    start_x = -((num_hooks-1)*spacing)/2
    styles = ["silicone", "metal", "wood", "silicone", "metal"]
    
    for i in range(num_hooks):
        x = start_x + (i * spacing)
        create_j_hook(x)
        create_spatula(styles[i], x)

if __name__ == "__main__":
    main()
