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
    # Materials
    dark_mat = create_material("DarkBody", (0.02, 0.02, 0.02, 1.0), 0.3)
    blue_mat = create_material("BlueTop", (0.1, 0.3, 0.8, 1.0), 0.1)

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

    # Top vertices (Z=h_canopy)
    v4 = bm.verts.new(Vector((-tw/2, -td/2, h_canopy)))
    v5 = bm.verts.new(Vector((tw/2, -td/2, h_canopy)))
    v6 = bm.verts.new(Vector((tw/2, td/2, h_canopy)))
    v7 = bm.verts.new(Vector((-tw/2, td/2, h_canopy)))

    # Canopy faces (Sides)
    bm.faces.new((v0, v1, v5, v4)) # Front
    bm.faces.new((v1, v2, v6, v5)) # Right
    bm.faces.new((v2, v3, v7, v6)) # Back
    bm.faces.new((v3, v0, v4, v7)) # Left
    # Top face of canopy (where chimney attaches)
    f_canopy_top = bm.faces.new((v4, v5, v6, v7))
    # Bottom face (the vent area)
    f_canopy_bottom = bm.faces.new((v0, v3, v2, v1))

    # --- Chimney Geometry ---
    # Dimensions: W=0.3, D=0.25, Height=1.0 (from Z=h_canopy to h_canopy + 1.0)
    cw, cd = 0.3, 0.25
    h_chimney = 1.0

    # Bottom vertices of chimney (Z=h_canopy)
    cv0 = bm.verts.new(Vector((-cw/2, -cd/2, h_canopy)))
    cv1 = bm.verts.new(Vector((cw/2, -cd/2, h_canopy)))
    cv2 = bm.verts.new(Vector((cw/2, cd/2, h_canopy)))
    cv3 = bm.verts.new(Vector((-cw/2, cd/2, h_canopy)))

    # Top vertices of chimney (Z=h_canopy + h_chimney)
    cv4 = bm.verts.new(Vector((-cw/2, -cd/2, h_canopy + h_chimney)))
    cv5 = bm.verts.new(Vector((cw/2, -cd/2, h_canopy + h_chimney)))
    cv6 = bm.verts.new(Vector((cw/2, cd/2, h_canopy + h_chimney)))
    cv7 = bm.verts.new(Vector((-cw/2, cd/2, h_canopy + h_chimney)))

    # Chimney faces
    bm.faces.new((cv0, cv1, cv5, cv4)) # Front
    bm.faces.new((cv1, cv2, cv6, cv5)) # Right
    bm.faces.new((cv2, cv3, cv7, cv6)) # Back
    bm.faces.new((cv3, cv0, cv4, cv7)) # Left
    f_chimney_top = bm.faces.new((cv4, cv5, cv6, cv7))
    # The bottom of the chimney is technically inside the canopy top

    # --- Add Detail: Filter Grill at Bottom ---
    # Create a small inset frame on the bottom face
    bmesh.ops.inset_individual(bm, faces=[f_canopy_bottom], thickness=0.05)
    inner_face = None
    for f in bm.faces:
        if len(f.verts) == 4 and f.normal.z < -0.9:
            # The original bottom face was v0,v3,v2,v1. After inset, the central one is the filter.
            # We just need to find the face with smaller area or specific center.
            if abs(f.calc_center().z) < 0.1:
                inner_face = f

    # Subdivide inner face to create grill slats
    if inner_face:
        res = 8
        # We simulate a grill by creating small rectangles
        # For simplicity in BMesh, we will just keep it as a separate material area
        pass

    # Finalize mesh
    mesh = bpy.data.meshes.new("RangeHood")
    obj = bpy.data.objects.new("RangeHood", mesh)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(mesh)
    bm.free()

    # Materials assignment
    obj.data.materials.append(dark_mat) # Index 0
    obj.data.materials.append(blue_mat) # Index 1

    for poly in obj.data.polygons:
        poly.material_index = 0
        # Top face of chimney gets blue material
        # Use coordinate check to avoid the index error from previous attempt
        center_z = sum(obj.data.vertices[v].co.z for v in poly.vertices) / len(poly.vertices)
        if center_z > (h_canopy + h_chimney - 0.01):
            poly.material_index = 1

    # Move object so base is at origin
    obj.location = (0, 0, 0)

if __name__ == "__main__":
    clear_scene()
    create_range_hood()
