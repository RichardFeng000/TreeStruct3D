import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, color):
    """Creates a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Set base color (RGBA)
        bsdf.inputs["Base Color"].default_value = color
        # Make it slightly matte for a kitchen appliance look
        bsdf.inputs["Roughness"].default_value = 0.4
    return mat

def create_range_hood():
    # Materials: Dark charcoal body and blue-tinted cap
    dark_mat = create_material("DarkBody", (0.02, 0.02, 0.02, 1.0))
    blue_mat = create_material("BlueTop", (0.05, 0.2, 0.7, 1.0))

    # --- Geometry Construction ---
    # We'll use a single BMesh for the whole object to ensure perfect alignment
    bm = bmesh.new()

    # Canopy Dimensions: Base(W=1.0, D=0.6), Top(W=0.6, D=0.4), Height=0.4
    # Bottom vertices (Z=0)
    v0 = bm.verts.new(Vector((-0.5, -0.3, 0.0)))
    v1 = bm.verts.new(Vector((0.5, -0.3, 0.0)))
    v2 = bm.verts.new(Vector((0.5, 0.3, 0.0)))
    v3 = bm.verts.new(Vector((-0.5, 0.3, 0.0)))

    # Top vertices (Z=0.4)
    v4 = bm.verts.new(Vector((-0.3, -0.2, 0.4)))
    v5 = bm.verts.new(Vector((0.3, -0.2, 0.4)))
    v6 = bm.verts.new(Vector((0.3, 0.2, 0.4)))
    v7 = bm.verts.new(Vector((-0.3, 0.2, 0.4)))

    # Canopy Faces
    bm.faces.new((v0, v1, v2, v3)) # Bottom
    bm.faces.new((v0, v1, v5, v4)) # Front
    bm.faces.new((v1, v2, v6, v5)) # Right
    bm.faces.new((v2, v3, v7, v6)) # Back
    bm.faces.new((v3, v0, v4, v7)) # Left
    # Note: We'll leave the top face for the chimney connection or cap it

    # Chimney Dimensions: W=0.3, D=0.25, Height=0.8 (From Z=0.4 to Z=1.2)
    # Bottom vertices (Z=0.4)
    cv0 = bm.verts.new(Vector((-0.15, -0.125, 0.4)))
    cv1 = bm.verts.new(Vector((0.15, -0.125, 0.4)))
    cv2 = bm.verts.new(Vector((0.15, 0.125, 0.4)))
    cv3 = bm.verts.new(Vector((-0.15, 0.125, 0.4)))

    # Top vertices (Z=1.2)
    cv4 = bm.verts.new(Vector((-0.15, -0.125, 1.2)))
    cv5 = bm.verts.new(Vector((0.15, -0.125, 1.2)))
    cv6 = bm.verts.new(Vector((0.15, 0.125, 1.2)))
    cv7 = bm.verts.new(Vector((-0.15, 0.125, 1.2)))

    # Chimney Faces
    bm.faces.new((cv0, cv1, cv2, cv3)) # Bottom (intersects canopy top)
    bm.faces.new((cv0, cv1, cv5, cv4)) # Front
    bm.faces.new((cv1, cv2, cv6, cv5)) # Right
    bm.faces.new((cv2, cv3, cv7, cv6)) # Back
    bm.faces.new((cv3, cv0, cv4, cv7)) # Left
    # The Top Face (will be blue)
    top_face = bm.faces.new((cv4, cv5, cv6, cv7))

    # Canopy top cover face to fill the gap around chimney
    # We create a ring of polygons or just a simple quad for now since it's mostly hidden
    bm.faces.new((v4, v5, v6, v7)) # Fill canopy top

    # Finalize mesh
    mesh = bpy.data.meshes.new("RangeHood")
    obj = bpy.data.objects.new("RangeHood", mesh)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(mesh)
    bm.free()

    # Assign Materials
    obj.data.materials.append(dark_mat) # Index 0
    obj.data.materials.append(blue_mat) # Index 1

    # Set all polygons to dark by default, then the top face to blue
    for poly in obj.data.polygons:
        poly.material_index = 0
    
    # Specifically find the very top polygon (Z=1.2) and make it blue
    for poly in obj.data.polygons:
        if all(v.co.z > 1.1 for v in poly.vertices):
            poly.material_index = 1

    obj.location = (0, 0, 0)

if __name__ == "__main__":
    clear_scene()
    create_range_hood()
