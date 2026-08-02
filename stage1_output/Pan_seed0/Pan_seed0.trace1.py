import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    # Clear orphaned data
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, rgba, metallic=0.2, roughness=0.4):
    """Creates a principled BSDF material."""
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
    height = 0.05
    wall_thickness = 0.006
    segments = 64
    handle_length = 0.32
    handle_width = 0.03
    handle_depth = 0.015

    # --- Materials ---
    mat_interior = create_material("MatInterior", (0.1, 0.15, 0.25, 1.0), metallic=0.3, roughness=0.3) # Dark blue-gray
    mat_exterior = create_material("MatExterior", (0.04, 0.04, 0.04, 1.0), metallic=0.6, roughness=0.5) # Dark charcoal
    mat_wood = create_material("MatWood", (0.7, 0.5, 0.3, 1.0), metallic=0.0, roughness=0.8)           # Light wood

    # --- Pan Body Construction ---
    # We'll start with a circle and extrude to create the "dish" shape
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=radius, segments=segments)
    
    # The circle is created on XY plane at Z=0
    face = bm.faces[0]
    
    # Extrude upwards to create the walls
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in verts_extruded:
        # Flare the walls slightly outwards to make "curved sides" feel
        scale_factor = 1.05
        v.co.x *= scale_factor
        v.co.y *= scale_factor
        v.co.z += height

    # Now we have a bowl-like shape (bottom face and side walls). 
    # To create thickness, we'll use Solidify modifier later or manual extrusion.
    # Manual is better for material control.
    
    # We need to extrude the current geometry 'inward/downward'
    # First, ensure all faces are selected
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    # Create a mesh object and apply modifiers for thickness and smoothing
    mesh_data = bpy.data.meshes.new("PanBody")
    bm.to_mesh(mesh_data)
    pan_obj = bpy.data.objects.new("FryingPan", mesh_data)
    bpy.context.collection.objects.link(pan_obj)
    bm.free()

    # Add Solidify for real thickness
    solid = pan_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = wall_thickness
    solid.offset = 1 # Offset inside
    bpy.ops.object.modifier_apply(modifier="Solidify")

    # Add Bevel to the top rim for a polished look
    bevel = pan_obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.003
    bevel.segments = 3
    bpy.ops.object.modifier_apply(modifier="Bevel")

    # Material Assignment for Body
    pan_obj.data.materials.append(mat_exterior) # Slot 0
    pan_obj.data.materials.append(mat_interior) # Slot 1
    
    bm = bmesh.new()
    bm.from_mesh(pan_obj.data)
    for f in bm.faces:
        # Interior faces usually point 'up' (Z > 0) inside the bowl
        if f.normal.z > 0.1:
            f.material_index = 1
        else:
            f.material_index = 0
    bm.to_mesh(pan_obj.data)
    bm.free()

    # --- Handle Construction ---
    # The handle is a long flat piece. 
    # Position it so it starts at the edge of the pan and extends out.
    handle_start_x = radius * 0.9 # Slight overlap into the pan body
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    # Scale to handle dimensions
    for v in bm.verts:
        v.co.x *= (handle_length / 2)
        v.co.y *= (handle_width / 2)
        v.co.z *= (handle_depth / 2)
    
    # Move it to the side of the pan
    offset_x = handle_start_x + (handle_length / 2)
    for v in bm.verts:
        v.co.x += offset_x
        v.co.z += height * 0.5 # Align with pan walls

    # Create a hole at the end of the handle
    # The far end is at x = offset_x + (handle_length/2)
    far_x = offset_x + (handle_length / 2)
    
    # We'll use a boolean cube to cut the hole
    bm.to_mesh(bpy.data.meshes.new("TempHandle"))
    handle_obj = bpy.data.objects.new("HandleMetal", pan_obj.data.copy()) # Placeholder, will replace
    # Actually just create it properly:
    handle_mesh = bpy.data.meshes.new("HandleMetal")
    bm.to_mesh(handle_mesh)
    handle_obj = bpy.data.objects.new("HandleMetal", handle_mesh)
    bpy.context.collection.objects.link(handle_obj)
    bm.free()

    # Boolean for the hole
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(far_x - 0.02, 0, height * 0.5))
    cutter = bpy.context.active_object
    cutter.scale = (0.04, handle_width * 1.2, handle_depth * 1.2)
    
    bool_mod = handle_obj.modifiers.new(name="Hole", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = cutter
    bpy.context.view_layer.objects.active = handle_obj
    bpy.ops.object.modifier_apply(modifier="Hole")
    
    # Remove cutter
    bpy.data.objects.remove(cutter, do_unlink=True)
    handle_obj.data.materials.append(mat_exterior)

    # Bevel the handle edges
    bev_h = handle_obj.modifiers.new(name="Bevel", type='BEVEL')
    bev_h.width = 0.005
    bev_h.segments = 2
    bpy.ops.object.modifier_apply(modifier="Bevel")

    # --- Wooden Grip Construction ---
    grip_len = 0.12
    grip_w = handle_width * 1.2
    grip_d = handle_depth * 1.6
    
    # Position the grip towards the end but not covering the hole
    grip_x = far_x - (grip_len / 2) - 0.04
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(grip_x, 0, height * 0.5 + handle_depth/2))
    grip_obj = bpy.context.active_object
    grip_obj.name = "HandleGrip"
    grip_obj.scale = (grip_len, grip_w, grip_d)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Soften the wood grip
    bev_wood = grip_obj.modifiers.new(name="Bevel", type='BEVEL')
    bev_wood.width = 0.008
    bev_wood.segments = 3
    bpy.ops.object.modifier_apply(modifier="Bevel")
    
    grip_obj.data.materials.append(mat_wood)

    # --- Final Touches ---
    # Set smooth shading for everything
    for obj in [pan_obj, handle_obj, grip_obj]:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth()
        
    # Center the whole assembly slightly if needed
    # Currently it's at (0,0,0) with handle extending in +X
    # To make it perfectly centered as a single object:
    total_width = radius + handle_length
    shift = - (total_width / 2) + radius
    
    # For now, we leave it sitting at the origin for simplicity, as per standard.

if __name__ == "__main__":
    clear_scene()
    build_frying_pan()
