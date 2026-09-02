import bpy
import bmesh
import math

def setup_scene():
    """Clears the default Blender scene."""
    if "Cube" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
    if "Camera" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Camera"], do_unlink=True)
    if "Light" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Light"], do_unlink=True)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_pot():
    """Constructs the wide hemispherical plant pot with a flat base."""
    # Parameters
    radius = 1.5 
    height = 1.0  # Height of the bowl (Z-scale)
    thickness = 0.12
    flat_base_threshold = 0.15 # Range from bottom to flatten

    # Create a UV sphere as the base primitive
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=64, 
        ring_count=32, 
        radius=radius, 
        location=(0, 0, 0)
    )
    obj = bpy.context.active_object
    obj.name = "PlantPot"

    # Scale the sphere to make it a wide hemisphere
    obj.scale[2] = height / radius
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    # 1. Remove top half to create the open bowl (z > 0)
    verts_to_delete = [v for v in bm.verts if v.co.z > 0.001]
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')

    # 2. Create a truly flat base
    # Find the lowest point
    min_z = min([v.co.z for v in bm.verts])
    # Snap vertices near the bottom to the same Z level to create a flat surface
    for v in bm.verts:
        if v.co.z < min_z + flat_base_threshold:
            v.co.z = min_z

    bm.to_mesh(obj.data)
    bm.free()

    # Add Solidify modifier for wall thickness
    solidify = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify.thickness = thickness
    solidify.offset = 1 # Offset interior
    
    # Add Subdivision Surface for smoothness
    subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3

    bpy.ops.object.shade_smooth()

    return obj

def create_material():
    """Creates the deep purple-blue glossy material."""
    mat = bpy.data.materials.new(name="DeepPurpleBlueGloss")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for node in nodes:
        nodes.remove(node)

    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    output = nodes.new(type='ShaderNodeOutputMaterial')

    # Color: Deep Purple-Blue (darker, richer tone)
    # Linear RGB for a deep indigo/midnight purple
    bsdf.inputs['Base Color'].default_value = (0.06, 0.03, 0.2, 1.0)
    
    # Glossy properties: low roughness for high gloss
    bsdf.inputs['Roughness'].default_value = 0.08 
    bsdf.inputs['Specular IOR Level'].default_value = 0.7

    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def main():
    setup_scene()
    pot_obj = create_pot()
    pot_mat = create_material()
    
    if pot_obj.data.materials:
        pot_obj.data.materials[0] = pot_mat
    else:
        pot_obj.data.materials.append(pot_mat)

    # Position the object so the base sits on Z=0
    # Current min_z is roughly -1.0 (half of a scaled sphere)
    # We'll shift it up based on its bounding box bottom
    bbox = pot_obj.bound_box
    min_z = min([v[2] for v in bbox])
    pot_obj.location[2] = -min_z

if __name__ == "__main__":
    main()
