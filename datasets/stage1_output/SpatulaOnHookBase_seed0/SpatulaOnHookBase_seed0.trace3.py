import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Removes all objects from the current scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Creates a basic principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Metallic'].default_value = metallic
    node_principled.inputs['Roughness'].default_value = roughness
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_backplate():
    """Creates the rectangular backplate and its dark frame border."""
    width, height, depth = 0.8, 0.4, 0.02
    frame_thickness = 0.03
    
    panel_mat = create_material("PanelMat", (0.95, 0.95, 0.95, 1), 0.0, 0.8)
    frame_mat = create_material("FrameMat", (0.02, 0.02, 0.02, 1), 0.2, 0.4)

    # Central Panel
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    panel = bpy.context.active_object
    panel.name = "BackplatePanel"
    panel.scale = (width, depth, height)
    panel.data.materials.append(panel_mat)
    bpy.ops.object.transform_apply(scale=True)

    # Frame - Top and Bottom
    for z in [height/2, -height/2]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, z))
        bar = bpy.context.active_object
        bar.scale = (width + frame_thickness*2, depth * 1.3, frame_thickness)
        bar.data.materials.append(frame_mat)
        bpy.ops.object.transform_apply(scale=True)

    # Frame - Left and Right
    for x in [-(width/2 + frame_thickness/2), width/2 + frame_thickness/2]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 0))
        bar = bpy.context.active_object
        bar.scale = (frame_thickness, depth * 1.3, height)
        bar.data.materials.append(frame_mat)
        bpy.ops.object.transform_apply(scale=True)

def create_j_hook(x_pos):
    """Creates a curved J-shaped hook at the specified x position."""
    # Hook path points (relative to its start point)
    points = [
        Vector((0, 0, 0)),
        Vector((0, 0.05, 0)),
        Vector((0, 0.06, -0.03)),
        Vector((0, 0.04, -0.08)),
        Vector((0, 0.02, -0.07))
    ]
    
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, radius=0.012, segments=16)
    # Fill the circle to create a face for extrusion
    bmesh.ops.contextual_create(bm, geom=bm.verts[:])
    
    bm.faces.ensure_lookup_table()
    face = bm.faces[0]
    
    for i in range(len(points)-1):
        p_start = points[i]
        p_end = points[i+1]
        direction = p_end - p_start
        
        res = bmesh.ops.extrude_face_region(bm, geom=[face])
        verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BVVert)]
        for v in verts:
            v.co += direction
        
        bm.faces.ensure_lookup_table()
        face = [f for f in res['geom'] if isinstance(f, bmesh.types.BVFace)][0]

    # Cap the end of the extrusion
    bmesh.ops.contextual_create(bm, geom=face.verts)
    
    mesh = bpy.data.meshes.new("HookMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Hook", mesh)
    bpy.context.collection.objects.link(obj)
    # Position hooks along the bottom edge of the panel (panel height is 0.4, so z=-0.2)
    obj.location = (x_pos, 0.01, -0.2) 
    
    hook_mat = create_material("HookMat", (0.8, 0.8, 0.8, 1), 1.0, 0.2)
    obj.data.materials.append(hook_mat)
    return obj

def create_spatula(style, x_pos):
    """Creates a spatula based on the provided style."""
    bm = bmesh.new()
    
    # Handle construction: Cylinder from z=0 down to -h_len
    h_len = 0.25
    h_rad = 0.012
    bmesh.ops.create_cylinder(bm, cap_ends=True, radius=h_rad, depth=h_len, segments=16)
    for v in bm.verts:
        v.co.z -= h_len/2

    # Head construction
    if style == "silicone":
        head_w, head_h, head_t = 0.07, 0.13, 0.015
        color = (0.8, 0.1, 0.1, 1) # Red
        roughness = 0.6
        metallic = 0.0
    elif style == "metal":
        head_w, head_h, head_t = 0.08, 0.14, 0.005
        color = (0.7, 0.7, 0.75, 1) # Silver
        roughness = 0.3
        metallic = 1.0
    else: # wood
        head_w, head_h, head_t = 0.06, 0.12, 0.02
        color = (0.5, 0.3, 0.15, 1) # Brown
        roughness = 0.8
        metallic = 0.0

    # Create the head as a cube and scale it
    bmesh.ops.create_cube(bm, size=1)
    bm.verts.ensure_lookup_table()
    # The last 8 vertices are from the cube we just added
    cube_verts = bm.verts[-8:]
    for v in cube_verts:
        v.co.x *= (head_w / 2)
        v.co.y *= (head_t / 2)
        v.co.z *= (head_h / 2)
        v.co.z += (head_h / 2)

    mesh = bpy.data.meshes.new(f"Spatula_{style}")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(f"Spatula_{style}", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Positioning: 
    # Hook Tip is roughly at (x_pos, 0.03, -0.27)
    obj.location = (x_pos, 0.035, -0.27)
    obj.rotation_euler = (math.radians(2), 0, math.radians(-5))
    
    mat = create_material(f"Mat_{style}", color, metallic=metallic, roughness=roughness)
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
