import bpy
import bmesh
import math

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)

def create_material(name, color):
    """Creates a dark brown material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # RGB for dark brown
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.7
        bsdf.inputs['Specular IOR Level'].default_value = 0.2
    return mat

def add_box(bm, w, l, h, tx, ty, tz):
    """Helper to add a scaled and translated box to a BMesh."""
    res = bmesh.ops.create_cube(bm, size=1.0)
    verts = res['verts']
    for v in verts:
        v.co.x = v.co.x * w + tx
        v.co.y = v.co.y * l + ty
        v.co.z = v.co.z * h + tz

def create_spatula():
    # Parameters (meters)
    blade_width = 0.08
    blade_length = 0.12
    blade_thick = 0.006
    handle_width = 0.025
    handle_length = 0.28
    handle_depth = 0.012
    hole_radius = 0.008

    bm = bmesh.new()
    # Blade centered on X, Z; top edge at Y=0
    add_box(bm, blade_width, blade_length, blade_thick, 0, -blade_length / 2, 0)
    # Handle centered on X, Z; bottom edge at Y=0
    add_box(bm, handle_width, handle_length, handle_depth, 0, handle_length / 2, 0)

    mesh = bpy.data.meshes.new("SpatulaMesh")
    obj = bpy.data.objects.new("Spatula", mesh)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(mesh)
    bm.free()

    # Ensure object is active and selected for Boolean operation
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Create the Hanging Hole Cutter
    bpy.ops.mesh.primitive_cylinder_add(
        radius=hole_radius, 
        depth=handle_depth * 3, 
        location=(0, handle_length - 0.04, 0), 
        rotation=(1.5708, 0, 0) # Rotate to align with thickness axis
    )
    cutter = bpy.context.active_object

    # Apply Boolean modifier
    bool_mod = obj.modifiers.new(name="Hole", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = cutter
    
    bpy.ops.object.modifier_apply(modifier="Hole")

    # Clean up the cutter object
    bpy.data.objects.remove(cutter, do_unlink=True)

    # Add a bevel to soften edges
    bevel_mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel_mod.width = 0.002
    bevel_mod.segments = 3
    bpy.ops.object.modifier_apply(modifier="Bevel")

    # Shading and Normal refinement
    for poly in obj.data.polygons:
        poly.use_smooth = True
        
    wn_mod = obj.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
    wn_mod.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier="WeightedNormal")

    return obj

def main():
    clear_scene()
    
    # Rich dark brown color
    dark_brown_color = (0.18, 0.08, 0.04, 1.0)
    mat = create_material("DarkBrown", dark_brown_color)
    
    spatula = create_spatula()
    if not spatula.data.materials:
        spatula.data.materials.append(mat)
    else:
        spatula.data.materials[0] = mat

if __name__ == "__main__":
    main()
