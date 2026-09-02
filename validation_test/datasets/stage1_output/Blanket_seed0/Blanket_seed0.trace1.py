import bpy
import bmesh
import math
import random

def clear_scene():
    """Removes all objects from the current scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_blanket_geometry():
    """Creates a high-resolution plane with procedural rumpling."""
    # Parameters for the blanket
    width = 2.0
    height = 2.0
    resolution = 128  # Vertex density for smooth ripples
    
    # Create initial mesh and object
    mesh = bpy.data.meshes.new("BlanketMesh")
    obj = bpy.data.objects.new("Blanket", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Create grid of vertices with procedural displacement (rumpling)
    verts = []
    for i in range(resolution + 1):
        for j in range(resolution + 1):
            x = (i / resolution) * width - (width / 2)
            y = (j / resolution) * height - (height / 2)
            
            # Procedural rumpling: combination of sine waves for a soft fabric look
            z = 0.0
            z += 0.04 * math.sin(x * 2.0 + y * 1.5)
            z += 0.03 * math.cos(y * 3.5 - x * 1.0)
            z += 0.015 * math.sin(x * 7.0) * math.cos(y * 7.0)
            # Subtle global curvature to prevent a perfectly flat look
            dist_sq = x*x + y*y
            z += (dist_sq * 0.02) 
            
            verts.append(bm.verts.new((x, y, z)))
            
    # Create faces for the grid
    for i in range(resolution):
        for j in range(resolution):
            v1 = verts[i * (resolution + 1) + j]
            v2 = verts[(i + 1) * (resolution + 1) + j]
            v3 = verts[(i + 1) * (resolution + 1) + (j + 1)]
            v4 = verts[i * (resolution + 1) + (j + 1)]
            bm.faces.new((v1, v2, v3, v4))
            
    bm.to_mesh(mesh)
    bm.free()
    
    # Set smooth shading for all polygons
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    # Add a Subdivision Surface modifier for extra softness and high-fidelity look
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    subsurf.render_levels = 2

def create_animal_print_material():
    """Creates a procedural material with pastel animal print colors."""
    mat = bpy.data.materials.new(name="PastelAnimalPrint")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    for n in nodes:
        nodes.remove(n)
        
    # Output node
    node_output = nodes.new('ShaderNodeOutputMaterial')
    
    # Principled BSDF for fabric-like appearance
    node_bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    node_bsdf.inputs['Roughness'].default_value = 0.9 # Matte fabric
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    
    # Voronoi Texture for animal print "spots"
    node_voronoi = nodes.new('ShaderNodeTexVoronoi')
    node_voronoi.voronoi_dimensions = '3D'
    # Fixing the previous error: access Randomness via inputs['Randomness'].default_value
    if 'Randomness' in node_voronoi.inputs:
        node_voronoi.inputs['Randomness'].default_value = 1.0
    node_voronoi.inputs['Scale'].default_value = 6.0
    
    # ColorRamp to define the pastel palette
    node_ramp = nodes.new('ShaderNodeValTorgb')
    elements = node_ramp.color_ramp.elements
    
    # Clear default elements
    while len(elements) > 0:
        elements.remove(elements[0])
        
    # Color mapping (White background with pastel spots)
    # We use the Distance output from Voronoi; low values are center of cells (spots)
    colors = [
        (0.0, (1.0, 0.75, 0.8, 1.0)),  # Pastel Pink
        (0.2, (0.8, 0.7, 1.0, 1.0)),  # Lavender
        (0.4, (0.7, 0.85, 1.0, 1.0)), # Pastel Blue
        (0.6, (1.0, 0.95, 0.85, 1.0)), # Cream
        (0.7, (1.0, 1.0, 1.0, 1.0)),  # Transition to White
        (1.0, (1.0, 1.0, 1.0, 1.0)),  # White base
    ]
    
    for pos, rgba in colors:
        elem = elements.new(pos)
        elem.color = rgba

    # Link Voronoi -> ColorRamp -> BSDF Base Color
    links.new(node_voronoi.outputs['Distance'], node_ramp.inputs['Fac'])
    links.new(node_ramp.outputs['Color'], node_bsdf.inputs['Base Color'])
    
    return mat

def main():
    clear_scene()
    
    # Generate the blanket geometry
    create_blanket_geometry()
    blanket = bpy.context.active_object
    
    # Create and assign the procedural material
    mat = create_animal_print_material()
    if blanket.data.materials:
        blanket.data.materials[0] = mat
    else:
        blanket.data.materials.append(mat)

if __name__ == "__main__":
    main()
