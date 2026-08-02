import bpy
import bmesh
import math

def setup_scene():
    """Clears the default scene of all objects."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material():
    """Creates a dark matte blue-gray material with visible subtle surface variation."""
    mat = bpy.data.materials.new(name="PotMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default nodes
    for node in nodes:
        nodes.remove(node)

    # Create Principled BSDF
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.9  # High roughness for matte finish
    
    # Dark blue-gray base color
    dark_blue_gray = (0.08, 0.1, 0.12, 1.0) # Very dark slate
    bsdf.inputs['Base Color'].default_value = dark_blue_gray

    # Setup noise for subtle surface variation
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 15.0
    noise.inputs['Detail'].default_value = 4.0

    # Color ramp to map noise to subtle color shifts
    color_ramp = nodes.new('ShaderNodeValToRGB')
    color_ramp.color_ramp.elements[0].color = (0.05, 0.07, 0.1, 1.0) # Darker shade
    color_ramp.color_ramp.elements[1].color = (0.12, 0.15, 0.18, 1.0) # Lighter shade

    # Mix the noise-driven color with the base for subtlety
    # In Blender 4.0+, ShaderNodeMixRGB is still available but often replaced by ShaderNodeMix.
    # We use MixRGB for broad compatibility within the 3.x/4.x/5.x range if available,
    # or construct a standard mix setup.
    mix = nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MIX'
    mix.inputs['Fac'].default_value = 0.4 # Blend factor between flat and noisy
    mix.inputs[1].default_value = dark_blue_gray

    output = nodes.new('ShaderNodeOutputMaterial')

    # Linkage: Noise -> ColorRamp -> Mix(with base) -> BSDF
    links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], mix.inputs[2]) # Slot 2 is the second color input
    links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    return mat

def create_cooking_pot():
    """Creates a cylindrical cooking pot with vertical walls and dark matte material."""
    # Parameters
    outer_radius = 1.0
    height = 1.3
    thickness = 0.06
    resolution = 64

    mesh = bpy.data.meshes.new("CookingPotMesh")
    obj = bpy.data.objects.new("CookingPot", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # Create the base disk
    bmesh.ops.create_circle(bm, radius=outer_radius, segments=resolution)
    # Fill the circle to create a bottom face
    edges = [e for e in bm.edges]
    bmesh.ops.contextual_create(bm, geom=edges)

    # Extrude walls upward to create the cylinder body
    # Identify boundary edges (the outer ring of the disk)
    boundary_edges = [e for e in bm.edges if e.is_boundary]
    res = bmesh.ops.extrude_edge_only(bm, edges=boundary_edges)
    
    # Move the extruded vertices up to create height
    for geom in res['geom']:
        if isinstance(geom, bmesh.types.BMVert):
            geom.co.z += height

    bm.to_mesh(mesh)
    bm.free()

    # Solidify to create wall thickness and bottom depth
    solidify = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify.thickness = thickness
    solidify.offset = -1 # Offset inward to keep outer dimensions consistent with radius

    # Bevel the edges for a realistic finish (top rim and bottom edge)
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.02
    bevel.segments = 3
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = math.radians(30)

    # Set shading to smooth
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    # Assign material explicitly
    pot_mat = create_material()
    if obj.data.materials:
        obj.data.materials[0] = pot_mat
    else:
        obj.data.materials.append(pot_mat)

if __name__ == "__main__":
    setup_scene()
    create_cooking_pot()
