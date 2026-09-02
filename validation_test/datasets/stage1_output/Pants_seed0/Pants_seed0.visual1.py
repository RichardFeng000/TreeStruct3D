import bpy
import bmesh
from mathutils import Vector
import random

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a soft fabric material with light pink coloring and slight emission for visibility."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Principled BSDF for the fabric look
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 0.9
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.1
        
    # Emission node to ensure visibility regardless of scene lighting
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = color
    emission.inputs['Strength'].default_value = 0.3 # Subtle glow for visibility
    
    # Mix BSDF and Emission so we keep some shading but avoid pure black renders
    mix = nodes.new('ShaderNodeMixShader')
    mix.inputs[0].default_value = 0.6 
    
    output = nodes.new('ShaderNodeOutputMaterial')
    
    links = mat.node_tree.links
    links.new(bsdf.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs[0])
    
    return mat

def create_pants():
    """Constructs a pair of pants laid flat with organic curves and an inverted-V crotch cutout."""
    # Define the silhouette coordinates for a more realistic garment shape
    # Sequence: Waist -> Hip R -> Hem Outer R -> Hem Inner R -> Crotch Apex -> Hem Inner L -> Hem Outer L -> Hip L -> Waist
    coords = [
        (0, 12), (2, 12), (4, 11.5), (6, 7), (5, -10), # Right side
        (2, -10),                                    # Right Hem Inner
        (0, -3),                                     # Crotch Apex (inverted-V)
        (-2, -10),                                   # Left Hem Inner
        (-5, -10), (-6, 7), (-4, 11.5), (-2, 12)      # Left side back to waist
    ]

    bm = bmesh.new()
    
    # Create vertices
    verts = [bm.verts.new(Vector((x, y, 0))) for x, y in coords]
    
    # Connect boundary edges
    for i in range(len(verts)):
        bm.edges.new((verts[i], verts[(i + 1) % len(verts)]))

    # Create the main face
    try:
        bm.faces.new(verts)
    except ValueError:
        pass

    # Triangulate and subdivide significantly to ensure Subdivision Surface modifier works smoothly
    bmesh.ops.triangulate(bm, faces=bm.faces)
    for _ in range(5):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1)

    # Add subtle random Z-axis noise to simulate soft fabric folds rather than a flat sheet
    for v in bm.verts:
        v.co.z += (random.random() - 0.5) * 0.25

    mesh = bpy.data.meshes.new("PantsMesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("BlushPants", mesh)
    bpy.context.collection.objects.link(obj)

    # Solidify for physical thickness (fabric weight)
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.12
    solid.offset = 0

    # Subdivision Surface for organic rounding of the garment edges
    subdiv = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 2

    return obj

def main():
    clear_scene()

    # Soft light pink / blush color: (R, G, B, A)
    blush_color = (1.0, 0.8, 0.75, 1.0)
    pink_mat = create_material("BlushFabric", blush_color)

    pants_obj = create_pants()

    # Assign material
    if not pants_obj.data.materials:
        pants_obj.data.materials.append(pink_mat)
    else:
        pants_obj.data.materials[0] = pink_mat

    # Apply smooth shading for soft fabric effect
    bpy.context.view_layer.objects.active = pants_obj
    bpy.ops.object.shade_smooth()
    
    pants_obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
