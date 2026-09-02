import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a soft fabric material with light pink coloring."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Base Color (Pale Pink/Blush)
        bsdf.inputs['Base Color'].default_value = color
        # Fabric-like roughness
        bsdf.inputs['Roughness'].default_value = 0.9
        # Lower specular to avoid plastic look
        if 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.1
    return mat

def create_pants():
    """Constructs a pair of pants laid flat with characteristic inverted-V gaps."""
    # Define the perimeter silhouette for a garment laid flat (X, Y)
    # Sequence: Waist -> Hip R -> Hem Outer R -> Hem Inner R -> Crotch -> Hem Inner L -> Hem Outer L -> Hip L -> Waist
    coords = [
        (-6, 15),   # Top Left Waist
        (6, 15),    # Top Right Waist
        (8, 10),    # Right Hip
        (7, -12),   # Right Leg Outer Hem
        (2, -12),   # Right Leg Inner Hem
        (0, 3),     # Crotch Point (The apex of the inverted-V)
        (-2, -12),  # Left Leg Inner Hem
        (-7, -12),  # Left Leg Outer Hem
        (-8, 10),   # Left Hip
    ]

    bm = bmesh.new()

    # Create vertices based on coordinates
    verts = [bm.verts.new(Vector((x, y, 0))) for x, y in coords]
    
    # Ensure the vertex loop is closed by connecting the last to the first
    for i in range(len(verts)):
        bm.edges.new((verts[i], verts[(i + 1) % len(verts)]))

    # Create the main surface face (N-gon)
    try:
        bm.faces.new(verts)
    except ValueError:
        pass # Handle cases where vertices might overlap or be invalid

    # To prevent subdivision issues with large N-gons and avoid timeouts, 
    # we triangulate the mesh first to create interior edges for the subdivider.
    bmesh.ops.triangulate(bm, faces=bm.faces)
    
    # Subdivide internal geometry moderately to allow modifiers to round corners smoothly
    # This creates a grid-like structure across the fabric surface
    for _ in range(3):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1)

    # Convert BMesh to Blender Mesh object
    mesh = bpy.data.meshes.new("PantsMesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("BlushPants", mesh)
    bpy.context.collection.objects.link(obj)

    # --- Modifiers for Physical Fidelity ---
    
    # 1. Solidify: Give the fabric a tangible thinness (0.1 units)
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.1
    solid.offset = 0

    # 2. Subdivision Surface: Smooth out the edges and create organic fabric curves
    subdiv = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 2

    return obj

def main():
    # Start clean
    clear_scene()

    # Soft light pink / blush color: (R, G, B, A)
    blush_color = (1.0, 0.85, 0.82, 1.0)
    pink_mat = create_material("BlushFabric", blush_color)

    # Construct the garment geometry
    pants_obj = create_pants()

    # Assign material
    if not pants_obj.data.materials:
        pants_obj.data.materials.append(pink_mat)
    else:
        pants_obj.data.materials[0] = pink_mat

    # Apply smooth shading for the soft fabric effect
    bpy.context.view_layer.objects.active = pants_obj
    bpy.ops.object.shade_smooth()
    
    # Ensure object is centered at origin
    pants_obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
