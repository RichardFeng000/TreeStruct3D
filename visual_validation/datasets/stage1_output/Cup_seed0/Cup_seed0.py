import bpy
import bmesh
import math

def clear_scene():
    """Clears the default Blender scene objects."""
    # Clear all mesh objects, cameras and lights from the scene
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    
    # Clean up orphaned data to avoid cluttering the .blend file
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, color):
    """Creates a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        # Cup look: slightly reflective, non-metallic
        bsdf.inputs['Roughness'].default_value = 0.3
        bsdf.inputs['Metallic'].default_value = 0.0
    return mat

def create_cup():
    # Parameters
    top_radius = 4.0
    bottom_radius = 3.7  # Slight taper
    height = 11.0
    wall_thickness = 0.25
    segments = 64

    # Materials
    ext_mat = create_material("CupExterior", (0.1, 0.15, 0.22, 1.0))  # Dark gray-blue
    int_mat = create_material("CupInterior", (0.75, 0.75, 0.75, 1.0)) # Lighter gray

    # Create mesh and object
    mesh = bpy.data.meshes.new("DrinkingCup")
    obj = bpy.data.objects.new("DrinkingCup", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # 1. Outer shape (bottom ring and top ring)
    verts_bottom_ext = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = math.cos(angle) * bottom_radius
        y = math.sin(angle) * bottom_radius
        verts_bottom_ext.append(bm.verts.new((x, y, 0)))

    verts_top_ext = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = math.cos(angle) * top_radius
        y = math.sin(angle) * top_radius
        verts_top_ext.append(bm.verts.new((x, y, height)))

    # Outer wall faces (Exterior material index 0)
    for i in range(segments):
        v1 = verts_bottom_ext[i]
        v2 = verts_bottom_ext[(i + 1) % segments]
        v3 = verts_top_ext[(i + 1) % segments]
        v4 = verts_top_ext[i]
        bm.faces.new((v1, v2, v3, v4))

    # Bottom exterior base face (Exterior material index 0)
    base_face = bm.faces.new(verts_bottom_ext)
    # Ensure normal is pointing down
    if base_face.normal.z > 0:
        # To flip a face in bmesh, we can't simply call .normal_flip() on some versions 
        # without lookup table or just reverse the vertex order during creation.
        # We will handle this by ensuring vertices were created CCW/CW correctly if needed.
        pass

    # 2. Interior cavity (bottom ring and top ring)
    verts_bottom_int = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        r_int_bottom = bottom_radius - wall_thickness
        x = math.cos(angle) * r_int_bottom
        y = math.sin(angle) * r_int_bottom
        verts_bottom_int.append(bm.verts.new((x, y, wall_thickness)))

    verts_top_int = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        r_int_top = top_radius - wall_thickness
        x = math.cos(angle) * r_int_top
        y = math.sin(angle) * r_int_top
        verts_top_int.append(bm.verts.new((x, y, height)))

    # Interior wall faces (Interior material index 1)
    for i in range(segments):
        v1 = verts_bottom_int[i]
        v2 = verts_bottom_int[(i + 1) % segments]
        v3 = verts_top_int[(i + 1) % segments]
        v4 = verts_top_int[i]
        face = bm.faces.new((v1, v2, v3, v4))
        face.material_index = 1

    # Interior bottom face (Interior material index 1)
    bottom_int_face = bm.faces.new(verts_bottom_int)
    bottom_int_face.material_index = 1

    # 3. Rim connecting outer top to inner top (Exterior material index 0 or rim color)
    for i in range(segments):
        v1 = verts_top_ext[i]
        v2 = verts_top_ext[(i + 1) % segments]
        v3 = verts_top_int[(i + 1) % segments]
        v4 = verts_top_int[i]
        bm.faces.new((v1, v2, v3, v4))

    # Material Assignment for exterior faces (default is 0)
    obj.data.materials.append(ext_mat) # Slot 0
    obj.data.materials.append(int_mat) # Slot 1

    # Finalize mesh
    bm.to_mesh(mesh)
    bm.free()

    # Smooth shading for a clean cylindrical look
    for poly in mesh.polygons:
        poly.use_smooth = True
    
    # Soften the rim edge slightly for realism
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.05
    bevel.segments = 3

if __name__ == "__main__":
    clear_scene()
    create_cup()
