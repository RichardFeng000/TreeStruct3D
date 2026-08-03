import bpy
import bmesh
import math

def setup_scene():
    """Clears the default scene of all objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material():
    """Creates a dark matte blue-gray material with subtle surface variation."""
    mat = bpy.data.materials.new(name="PotMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default nodes
    for node in nodes:
        nodes.remove(node)

    # Create Principled BSDF
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.85 # Matte finish
    
    # Define dark blue-gray color
    base_color = (0.12, 0.15, 0.18, 1.0) # Dark slate blue-gray
    
    # Setup noise for subtle surface variation
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 10.0
    noise.inputs['Detail'].default_value = 2.0

    color_ramp = nodes.new('ShaderNodeValToRGB')
    # Set ramp to vary slightly around the base color
    color_ramp.color_ramp.elements[0].color = (0.1, 0.13, 0.16, 1.0) # Slightly darker
    color_ramp.color_ramp.elements[1].color = (0.15, 0.18, 0.22, 1.0) # Slightly lighter

    # Mix the noise-driven color with a constant for control if needed, 
    # but here we just use the ramp to define the range of "variation".
    output = nodes.new('ShaderNodeOutputMaterial')

    links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    return mat

def create_cooking_pot():
    """Creates a cylindrical cooking pot with vertical walls and dark matte material."""
    # Parameters
    outer_radius = 1.0
    height = 1.3
    thickness = 0.05
    resolution = 64

    mesh = bpy.data.meshes.new("CookingPotMesh")
    obj = bpy.data.objects.new("CookingPot", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # Create the base disk
    bmesh.ops.create_circle(bm, radius=outer_radius, segments=resolution)
    edges = [e for e in bm.edges]
    bmesh.ops.contextual_create(bm, geom=edges)

    # Identify boundary edges to extrude walls upward
    boundary_edges = [e for e in bm.edges if e.is_boundary]
    res = bmesh.ops.extrude_edge_only(bm, edges=boundary_edges)
    
    for geom in res['geom']:
        if isinstance(geom, bmesh.types.BMVert):
            geom.co.z += height

    bm.to_mesh(mesh)
    bm.free()

    # Solidify to create wall thickness and bottom depth
    solidify = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify.thickness = thickness
    solidify.offset = -1 # Offset inward

    # Bevel the edges for a realistic finish and to prevent sharp CG looks
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.015
    bevel.segments = 3
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = math.radians(30)

    # We omit Subdivision Surface here because the resolution is already high (64),
    # and Subdiv causes bloating of vertical walls unless complex support loops are added.
    # This ensures "straight vertical walls".

    # Set shading to smooth
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    # Assign material
    pot_mat = create_material()
    obj.data.materials.append(pot_mat)

if __name__ == "__main__":
    setup_scene()
    create_cooking_pot()
