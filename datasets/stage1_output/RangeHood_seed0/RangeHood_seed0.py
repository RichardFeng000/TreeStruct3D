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

def create_material(name, color, roughness=0.4):
    """Creates a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

def create_range_hood():
    # Materials - Ensuring "Dark Body" is actually dark (nearly black/charcoal)
    dark_mat = create_material("DarkBody", (0.03, 0.03, 0.03, 1.0), 0.2)
    blue_mat = create_material("BlueTop", (0.1, 0.4, 0.9, 1.0), 0.1)

    # Create main mesh object
    mesh = bpy.data.meshes.new("RangeHood")
    obj = bpy.data.objects.new("RangeHood", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # --- Canopy Geometry ---
    # Dimensions: Base(W=1.2, D=0.6), Top(W=0.4, D=0.3), Height=0.5
    bw, bd = 1.2, 0.6
    tw, td = 0.4, 0.3
    h_canopy = 0.5

    # Base vertices (Z=0)
    v0 = bm.verts.new(Vector((-bw/2, -bd/2, 0)))
    v1 = bm.verts.new(Vector((bw/2, -bd/2, 0)))
    v2 = bm.verts.new(Vector((bw/2, bd/2, 0)))
    v3 = bm.verts.new(Vector((-bw/2, bd/2, 0)))

    # Top vertices of canopy (Z=h_canopy)
    v4 = bm.verts.new(Vector((-tw/2, -td/2, h_canopy)))
    v5 = bm.verts.new(Vector((tw/2, -td/2, h_canopy)))
    v6 = bm.verts.new(Vector((tw/2, td/2, h_canopy)))
    v7 = bm.verts.new(Vector((-tw/2, td/2, h_canopy)))

    # Canopy faces (Sides)
    bm.faces.new((v0, v1, v5, v4)) # Front
    bm.faces.new((v1, v2, v6, v5)) # Right
    bm.faces.new((v2, v3, v7, v6)) # Back
    bm.faces.new((v3, v0, v4, v7)) # Left
    # Bottom face (the underside of the hood)
    f_canopy_bottom = bm.faces.new((v0, v3, v2, v1))

    # --- Chimney Geometry ---
    # Dimensions: W=0.3, D=0.25, Height=1.0 (from Z=h_canopy to h_canopy + 1.0)
    cw, cd = 0.3, 0.25
    h_chimney = 1.0

    # Bottom vertices of chimney (Z=h_canopy) - positioned on the top surface of canopy
    cv0 = bm.verts.new(Vector((-cw/2, -cd/2, h_canopy)))
    cv1 = bm.verts.new(Vector((cw/2, -cd/2, h_canopy)))
    cv2 = bm.verts.new(Vector((cw/2, cd/2, h_canopy)))
    cv3 = bm.verts.new(Vector((-cw/2, cd/2, h_canopy)))

    # Top vertices of chimney (Z=h_canopy + h_chimney)
    cv4 = bm.verts.new(Vector((-cw/2, -cd/2, h_canopy + h_chimney)))
    cv5 = bm.verts.new(Vector((cw/2, -cd/2, h_canopy + h_chimney)))
    cv6 = bm.verts.new(Vector((cw/2, cd/2, h_canopy + h_chimney)))
    cv7 = bm.verts.new(Vector((-cw/2, cd/2, h_canopy + h_chimney)))

    # Chimney faces (Vertical sides)
    bm.faces.new((cv0, cv1, cv5, cv4)) # Front
    bm.faces.new((cv1, cv2, cv6, cv5)) # Right
    bm.faces.new((cv2, cv3, cv7, cv6)) # Back
    bm.faces.new((cv3, cv0, cv4, cv7)) # Left
    # Chimney top cap face
    f_chimney_top = bm.faces.new((cv4, cv5, cv6, cv7))

    # --- Connecting Canopy Top to Chimney Base ---
    # The space on the canopy's top surface around the chimney base needs faces.
    # We create a face from the outer ring (v4-v7) to the inner ring (cv0-cv3).
    bm.faces.new((v4, v5, cv1, cv0)) # Front strip
    bm.faces.new((v5, v6, cv2, cv1)) # Right strip
    bm.faces.new((v6, v7, cv3, cv2)) # Back strip
    bm.faces.new((v7, v4, cv0, cv3)) # Left strip

    # Finalize mesh
    bm.to_mesh(mesh)
    bm.free()

    # Assign Materials
    obj.data.materials.append(dark_mat) # Index 0
    obj.data.materials.append(blue_mat) # Index 1

    for poly in obj.data.polygons:
        poly.material_index = 0
        # Top face of chimney gets blue material
        center_z = sum(obj.data.vertices[v].co.z for v in poly.vertices) / len(poly.vertices)
        if center_z > (h_canopy + h_chimney - 0.01):
            poly.material_index = 1

    # Center object at origin
    obj.location = (0, 0, 0)

if __name__ == "__main__":
    clear_scene()
    create_range_hood()
