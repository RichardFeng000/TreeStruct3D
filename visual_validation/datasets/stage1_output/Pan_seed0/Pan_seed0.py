import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, rgba, metallic=0.2, roughness=0.4):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = rgba
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def build_frying_pan():
    # --- Parameters ---
    radius = 0.18
    height = 0.045
    thickness = 0.006
    segments = 64
    handle_length = 0.32
    handle_width = 0.028
    handle_depth = 0.014

    # --- Materials ---
    mat_interior = create_material("MatInterior", (0.15, 0.2, 0.3, 1.0), metallic=0.4, roughness=0.3) # Dark blue-gray
    mat_exterior = create_material("MatExterior", (0.05, 0.05, 0.05, 1.0), metallic=0.8, roughness=0.5) # Dark charcoal
    mat_wood = create_material("MatWood", (0.5, 0.3, 0.15, 1.0), metallic=0.0, roughness=0.7)

    # --- Pan Body Construction ---
    bm = bmesh.new()
    # Create the main dish shape
    bmesh.ops.create_circle(bm, cap_ends=True, radius=radius, segments=segments)
    
    # Extrude for walls
    bm.faces.ensure_lookup_table()
    bottom_face = bm.faces[0]
    res = bmesh.ops.extrude_face_region(bm, geom=[bottom_face])
    verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in verts_extruded:
        v.co.z += height
        # Flare the sides slightly
        v.co.x *= 1.08
        v.co.y *= 1.08

    # Convert to mesh and apply Solidify for real thickness
    mesh_data = bpy.data.meshes.new("PanBody")
    bm.to_mesh(mesh_data)
    pan_obj = bpy.data.objects.new("FryingPan", mesh_data)
    bpy.context.collection.objects.link(pan_obj)
    bm.free()

    solid = pan_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = thickness
    solid.offset = -1 
    
    bevel = pan_obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.005
    bevel.segments = 3

    bpy.context.view_layer.objects.active = pan_obj
    bpy.ops.object.modifier_apply(modifier="Solidify")
    bpy.ops.object.modifier_apply(modifier="Bevel")

    # Material Assignment: Interior (top/inside) vs Exterior
    pan_obj.data.materials.append(mat_exterior) # Index 0
    pan_obj.data.materials.append(mat_interior) # Index 1
    
    bm = bmesh.new()
    bm.from_mesh(pan_obj.data)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        # Faces pointing generally upwards are the interior/bottom floor
        if f.normal.z > -0.1:
            f.material_index = 1
        else:
            f.material_index = 0
    bm.to_mesh(pan_obj.data)
    bm.free()

    # --- Handle Construction ---
    # Start handle deeper into the pan to ensure no gap
    handle_start_x = radius * 0.75 
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= (handle_length / 2)
        v.co.y *= (handle_width / 2)
        v.co.z *= (handle_depth / 2)
    
    # Center the handle so its left edge is at handle_start_x
    offset_x = handle_start_x + (handle_length / 2)
    for v in bm.verts:
        v.co.x += offset_x
        v.co.z += height * 0.4

    handle_mesh = bpy.data.meshes.new("HandleMetal")
    bm.to_mesh(handle_mesh)
    handle_obj = bpy.data.objects.new("HandleMetal", handle_mesh)
    bpy.context.collection.objects.link(handle_obj)
    bm.free()
    handle_obj.data.materials.append(mat_exterior)

    # Boolean hole at the end of the handle (clearer size)
    far_x = offset_x + (handle_length / 2)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(far_x - 0.015, 0, height * 0.4))
    cutter = bpy.context.active_object
    cutter.scale = (0.04, handle_width * 1.2, handle_depth * 1.2)
    
    bool_mod = handle_obj.modifiers.new(name="Hole", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = cutter
    bpy.context.view_layer.objects.active = handle_obj
    bpy.ops.object.modifier_apply(modifier="Hole")
    bpy.data.objects.remove(cutter, do_unlink=True)

    # --- Wooden Grip Construction ---
    grip_len = 0.15
    grip_w = handle_width * 1.2
    grip_d = handle_depth * 1.4
    
    # Place grip near the end but leave space for the hole
    grip_x = far_x - (grip_len / 2) - 0.06
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(grip_x, 0, height * 0.4))
    grip_obj = bpy.context.active_object
    grip_obj.name = "HandleGrip"
    grip_obj.scale = (grip_len, grip_w, grip_d)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    bev_wood = grip_obj.modifiers.new(name="BevelGrip", type='BEVEL')
    bev_wood.width = 0.008
    bev_wood.segments = 3
    bpy.context.view_layer.objects.active = grip_obj
    bpy.ops.object.modifier_apply(modifier="BevelGrip")
    grip_obj.data.materials.append(mat_wood)

    # --- Final Finishing ---
    for obj in [pan_obj, handle_obj, grip_obj]:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    clear_scene()
    build_frying_pan()
