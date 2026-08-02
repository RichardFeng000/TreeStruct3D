import bpy
import bmesh
import math

def clear_scene():
    """Clears all default objects and data from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)

def create_material(name, color):
    """Creates a material with the specified base color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.4
        bsdf.inputs['Specular IOR Level'].default_value = 0.2
    return mat

def create_spatula():
    # Dimensions (meters)
    blade_w = 0.08
    blade_l = 0.12
    blade_t = 0.006
    handle_w = 0.025
    handle_l = 0.25
    handle_t = 0.012
    hole_r = 0.007

    # Create a BMesh for the main body (blade and handle)
    bm = bmesh.new()
    
    # --- BLADE ---
    # Center it at origin, extend along Y axis
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= (blade_w / 2)
        v.co.y *= (blade_l / 2)
        v.co.z *= (blade_t / 2)

    # --- HANDLE ---
    # Shift the handle so it starts at the top of the blade
    # Handle center Y = blade_l/2 + handle_l/2
    handle_center_y = (blade_l / 2) + (handle_l / 2)
    res = bmesh.ops.create_cube(bm, size=1.0)
    for v in res['verts']:
        v.co.x *= (handle_w / 2)
        v.co.y = (v.co.y * (handle_l / 2)) + handle_center_y
        v.co.z *= (handle_t / 2)

    # Merge overlapping vertices at the junction
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    
    # Create mesh and object from BMesh
    mesh = bpy.data.meshes.new("SpatulaMesh")
    obj = bpy.data.objects.new("Spatula", mesh)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(mesh)
    bm.free()

    # --- HOLE ---
    # Hole is at the top of the handle: Y = (blade_l/2 + handle_l) - offset
    hole_y = (blade_l / 2) + handle_l - 0.03
    bpy.ops.mesh.primitive_cylinder_add(
        radius=hole_r, 
        depth=handle_t * 2.5, 
        location=(0, hole_y, 0), 
        rotation=(1.5708, 0, 0) # Rotate to align with handle thickness (Z axis relative to object)
    )
    # Correction: Cylinder is created along local Z by default. 
    # The spatula's thickness is along the world Z. No rotation needed if depth is aligned with world Z.
    cutter = bpy.context.active_object
    cutter.location = (0, hole_y, 0)
    cutter.rotation_euler = (0, 0, 0) # Cylinder axis is Z

    # Apply Boolean difference
    bpy.context.view_layer.objects.active = obj
    bool_mod = obj.modifiers.new(name="Hole", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = cutter
    
    # Apply the modifier
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Hole")

    # Clean up the cutter object
    bpy.data.objects.remove(cutter, do_unlink=True)

    # Bevel for realism to soften sharp edges
    bevel_mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel_mod.width = 0.002
    bevel_mod.segments = 3
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Bevel")

    # Shading and Normals for high fidelity
    for poly in obj.data.polygons:
        poly.use_smooth = True
    
    wn_mod = obj.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
    wn_mod.keep_sharp = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="WeightedNormal")

    return obj

def main():
    clear_scene()
    
    # Dark brown color (sRGB)
    dark_brown_color = (0.15, 0.07, 0.03, 1.0)
    mat = create_material("DarkBrown", dark_brown_color)
    
    spatula = create_spatula()
    if not spatula.data.materials:
        spatula.data.materials.append(mat)
    else:
        spatula.data.materials[0] = mat

if __name__ == "__main__":
    main()
