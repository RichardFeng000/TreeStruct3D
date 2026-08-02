import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple principled BSDF material for fabric."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Base Color
        bsdf.inputs['Base Color'].default_value = color
        # Fabric properties in Blender 4.0+ / 5.0: Roughness high, Specular low
        bsdf.inputs['Roughness'].default_value = 0.85
        if 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.2
    return mat

def create_pants():
    """Constructs a pair of pants laid flat using BMesh."""
    # Define the silhouette vertices (X, Y) for a garment laid flat on Z=0
    # The coordinates form the outer boundary of the fabric
    verts_coords = [
        (-6, 15),   # 0: Top Left Waist
        (6, 15),    # 1: Top Right Waist
        (9, 12),    # 2: Right Hip
        (8, -15),   # 3: Right Leg Outer Hem
        (3, -15),   # 4: Right Leg Inner Hem
        (0, 2),     # 5: Crotch Point (creates the inverted-V)
        (-3, -15),  # 6: Left Leg Inner Hem
        (-8, -15),  # 7: Left Leg Outer Hem
        (-9, 12),   # 8: Left Hip
    ]

    bm = bmesh.new()

    # Create vertices
    verts = [bm.verts.new(Vector((x, y, 0))) for x, y in verts_coords]
    
    # Create edges to form the perimeter
    for i in range(len(verts)):
        bm.edges.new((verts[i], verts[(i + 1) % len(verts)]))

    # Create the main surface face
    try:
        bm.faces.new(verts)
    except ValueError:
        pass

    # Subdivide edges to provide enough geometry for modifiers to look smooth
    # We remove the 'method' argument which caused the previous crash
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=6)
    
    # Further refine internal face geometry by subdividing the face itself 
    # into a grid rather than just perimeter subdivisions
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=4)

    # Convert BMesh to mesh object
    mesh = bpy.data.meshes.new("PantsMesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("BlushPants", mesh)
    bpy.context.collection.objects.link(obj)

    # --- Modifiers for Fabric Fidelity ---
    
    # 1. Solidify: Give the fabric a slight physical thickness
    solidify = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify.thickness = 0.12
    solidify.offset = 0

    # 2. Subdivision Surface: Round off edges and smooth out the surface
    subdiv = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 3

    return obj

def main():
    clear_scene()

    # Color: Soft light pink / blush (Pale pink)
    # RGBA: (1.0, 0.85, 0.82, 1.0)
    blush_color = (1.0, 0.85, 0.82, 1.0)
    pink_mat = create_material("BlushFabric", blush_color)

    # Create the geometry
    pants_obj = create_pants()

    # Assign material
    if not pants_obj.data.materials:
        pants_obj.data.materials.append(pink_mat)
    else:
        pants_obj.data.materials[0] = pink_mat

    # Set shading to smooth for a softer fabric look
    bpy.context.view_layer.objects.active = pants_obj
    bpy.ops.object.shade_smooth()
    
    # Center and position the object at origin
    pants_obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
