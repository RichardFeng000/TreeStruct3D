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
    width = 2.5
    height = 2.0
    resolution = 100  # Vertex density for smooth ripples
    
    mesh = bpy.data.meshes.new("BlanketMesh")
    obj = bpy.data.objects.new("Blanket", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Create grid of vertices
    verts = []
    for i in range(resolution + 1):
        row = []
        for j in range(resolution + 1):
            x = (i / resolution) * width - (width / 2)
            y = (j / resolution) * height - (height / 2)
            
            # Procedural rumpling: combination of sine waves and random-ish offsets
            z = 0.0
            z += 0.05 * math.sin(x * 1.8 + y * 1.2)
            z += 0.04 * math.cos(y * 3.2 - x * 0.8)
            z += 0.02 * math.sin(x * 6.0) * math.cos(y * 6.0)
            # Subtle global curvature to simulate gravity/resting on surface
            dist_sq = (x*x + y*y) * 0.015
            z += dist_sq
            
            row.append(bm.verts.new((x, y, z)))
        verts.append(row)
            
    # Create faces for the grid
    for i in range(resolution):
        for j in range(resolution):
            v1 = verts[i][j]
            v2 = verts[i+1][j]
            v3 = verts[i+1][j+1]
            v4 = verts[i][j+1]
            bm.faces.new((v1, v2, v3, v4))
            
    bm.to_mesh(mesh)
    bm.free()
    
    # Set smooth shading
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    # Subdivision Surface for extra softness
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    subsurf.render_levels = 2

def create_animal_print_material():
    """Creates a procedural material with pastel animal print colors."""
    mat = bpy.data.materials.new(name="PastelAnimalPrint")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    for n in nodes:
        nodes.remove(n)
        
    node_output = nodes.new('ShaderNodeOutputMaterial')
    node_bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    node_bsdf.inputs['Roughness'].default_value = 0.85
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    
    # Voronoi for animal print spots
    node_voronoi = nodes.new('ShaderNodeTexVoronoi')
    node_voronoi.voronoi_dimensions = '3D'
    if 'Randomness' in node_voronoi.inputs:
        node_voronoi.inputs['Randomness'].default_value = 1.0
    node_voronoi.inputs['Scale'].default_value = 8.0
    
    # ColorRamp for the palette
    node_ramp = nodes.new('ShaderNodeValToRGB')
    elements = node_ramp.color_ramp.elements
    
    # Blender ColorRamps start with two elements (0 and 1).
    # We modify them and add others in between.
    
    # White background is the dominant color, so it should be at the high end of distance
    # Spots are closer to cells, so lower distances get colors.
    
    # Define palette: Pastel Pink, Lavender, Blue, Cream, White
    palette = [
        (0.0, (1.0, 0.75, 0.8, 1.0)),  # Pastel Pink
        (0.2, (0.8, 0.7, 1.0, 1.0)),  # Lavender
        (0.4, (0.7, 0.85, 1.0, 1.0)), # Pastel Blue
        (0.6, (1.0, 0.95, 0.85, 1.0)), # Cream
    ]
    
    # Setup the base elements first to avoid index errors
    elements[0].position = 0.0
    elements[0].color = palette[0][1]
    elements[-1].position = 0.7
    elements[-1].color = (1.0, 1.0, 1.0, 1.0) # White
    
    # Add the intermediate colors from our palette
    for i in range(1, len(palette)):
        pos, col = palette[i]
        if pos < 0.7: # Only add if it's before the white threshold
            elem = elements.new(pos)
            elem.color = col

    # To make "spots" more distinct and less like a gradient, we could use constant interpolation
    node_ramp.color_ramp.interpolation = 'LINEAR' 
    # Actually, for animal prints, slightly sharper transitions are better:
    # We simulate this by keeping the palette positions tight or using a math node.
    # But linear with a white cutoff usually looks soft and "pastel".

    links.new(node_voronoi.outputs['Distance'], node_ramp.inputs['Fac'])
    links.new(node_ramp.outputs['Color'], node_bsdf.inputs['Base Color'])
    
    return mat

def main():
    clear_scene()
    
    # Geometry
    create_blanket_geometry()
    blanket = bpy.context.active_object
    
    # Material
    mat = create_animal_print_material()
    if blanket.data.materials:
        blanket.data.materials[0] = mat
    else:
        blanket.data.materials.append(mat)

if __name__ == "__main__":
    main()
