import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a blush fabric material with slight emission for visibility in dark environments."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Principled BSDF for the soft fabric look
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 0.8
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.2
        
    # Emission to ensure the light pink is visible and doesn't look grey/black
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = color
    emission.inputs['Strength'].default_value = 0.4
    
    mix = nodes.new('ShaderNodeMixShader')
    mix.inputs[0].default_value = 0.7 # Blend BSDF and Emission
    
    output = nodes.new('ShaderNodeOutputMaterial')
    
    links = mat.node_tree.links
    links.new(bsdf.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs[0])
    
    return mat

def create_pants():
    """Constructs a pair of pants laid flat as a fabric piece with an inverted-V crotch gap."""
    bm = bmesh.new()
    
    # Silhouette coordinates for a realistic 'flat lay' garment
    # We define the outer boundary and then bridge it to create a 3D slab
    # (x, y) pairs: Waist L -> Waist R -> Hip R -> Ankle R Out -> Ankle R In -> Crotch Apex -> Ankle L In -> Ankle L Out -> Hip L -> back to start
    coords = [
        (-1.5, 6), (1.5, 6),  # Waist
        (2.2, 3),            # Outer Right Hip
        (2.8, -7),           # Outer Right Ankle
        (1.0, -7),           # Inner Right Ankle
        (0.0, 0.5),          # Crotch Apex (creates the inverted-V gap between legs)
        (-1.0, -7),          # Inner Left Ankle
        (-2.8, -7),          # Outer Left Ankle
        (-2.2, 3),           # Outer Left Hip
    ]

    # Create vertices for top face and bottom face to make a slab (thickness)
    verts_top = [bm.verts.new(Vector((x, y, 0.05))) for x, y in coords]
    verts_bot = [bm.verts.new(Vector((x, y, -0.05))) for x, y in coords]

    # Connect boundary edges for top and bottom faces
    for i in range(len(coords)):
        next_i = (i + 1) % len(coords)
        bm.edges.new((verts_top[i], verts_top[next_i]))
        bm.edges.new((verts_bot[i], verts_bot[next_i]))

    # Connect top and bottom boundaries to create the 'sides' of the fabric piece
    for i in range(len(coords)):
        bm.edges.new((verts_top[i], verts_bot[i]))

    # Create the main faces (Top, Bottom, Sides)
    # Top face
    try:
        bm.faces.new(verts_top)
    except ValueError: pass 
    # Bottom face
    try:
        bm.faces.new(verts_bot)
    except ValueError: pass
    
    # Side faces (quads)
    for i in range(len(coords)):
        next_i = (i + 1) % len(coords)
        try:
            bm.faces.new((verts_top[i], verts_top[next_i], verts_bot[next_i], verts_bot[i]))
        except ValueError: pass

    # Add subtle organic detail: subdivide and nudge vertices for a "soft fabric" look
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=2)
    for v in bm.verts:
        if v.co.y < 0: # Only nudge the legs slightly to simulate folds
            import random
            v.co.z += (random.random() - 0.5) * 0.1

    mesh = bpy.data.meshes.new("PantsMesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("BlushPants", mesh)
    bpy.context.collection.objects.link(obj)

    # Use Subdivision Surface for a soft, organic textile feel
    subdiv = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 2

    return obj

def main():
    clear_scene()

    # Soft light pink/blush color: (R, G, B, A)
    blush_color = (1.0, 0.75, 0.75, 1.0)
    pink_mat = create_material("BlushFabric", blush_color)

    pants_obj = create_pants()

    # Assign material
    if not pants_obj.data.materials:
        pants_obj.data.materials.append(pink_mat)
    else:
        pants_obj.data.materials[0] = pink_mat

    # Smooth shading for a fabric-like appearance
    bpy.context.view_layer.objects.active = pants_obj
    bpy.ops.object.shade_smooth()
    
    pants_obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
