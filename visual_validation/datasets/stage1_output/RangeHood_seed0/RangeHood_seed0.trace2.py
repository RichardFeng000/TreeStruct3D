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
    # Top face of canopy (where chimney attaches)
    f_canopy_top = bm.faces.new((v4, v5, v6, v7))
    # Bottom face
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

    # --- Filter Grill Detail ---
    # Create a recessed area at the bottom of the canopy
    # We'll manually create slats by subdividing the bottom face
    bmesh.ops.inset_individual(bm, faces=[f_canopy_bottom], thickness=0.05)
    
    # Find the newly created inner face (the one with center z near 0 and normal pointing down)
    inner_face = None
    for f in bm.faces:
        if len(f.verts) == 4:
            center = Vector((0,0,0))
            for v in f.verts: center += v.co
            center /= 4
            if abs(center.z) < 0.01 and f.normal.z < -0.9:
                inner_face = f
                break

    if inner_face:
        # To create real slats, we'll remove the inner face and bridge with small bars
        # Instead of complex ops, let's just offset it slightly to look recessed
        bmesh.ops.translate(bm, verts=inner_face.verts, vec=Vector((0, 0, -0.02)))
        
        # Create slats geometry
        slat_count = 10
        slat_width = (bw * 0.8) / slat_count
        for i in range(slat_count):
            x_start = -bw*0.4 + i * slat_width
            x_end = x_start + slat_width * 0.6 # gap between slats
            z_off = -0.02
            
            # Create a thin rectangular bar for each slat
            s_v0 = bm.verts.new(Vector((x_start, -bd*0.25, z_off)))
            s_v1 = bm.verts.new(Vector((x_end, -bd*0.25, z_off)))
            s_v2 = bm.verts.new(Vector((x_end, bd*0.25, z_off)))
            s_v3 = bm.verts.new(Vector((x_start, bd*0.25, z_off)))
            
            # Add small thickness to slats
            s_v4 = bm.verts.new(Vector((x_start, -bd*0.25, z_off - 0.01)))
            s_v5 = bm.verts.new(Vector((x_end, -bd*0.25, z_off - 0.01)))
            s_v6 = bm.verts.new(Vector((x_end, bd*0.25, z_off - 0.01)))
            s_v7 = bm.verts.new(Vector((x_start, bd*0.25, z_off - 0.01)))
            
            bm.faces.new((s_v0, s_v1, s_v2, s_v3)) # top
            bm.faces.new((s_v4, s_v7, s_v6, s_v5)) # bottom
            bm.faces.new((s_v0, s_v1, s_v5, s_v4)) # front
            bm.faces.new((s_v1, s_v2, s_v6, s_v5)) # right
            bm.faces.new((s_v2, s_v3, s_v7, s_v6)) # back
            bm.faces.new((s_v3, s_v0, s_v4, s_v7)) # left

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

    # Move object so base is at origin
    obj.location = (0, 0, 0)

if __name__ == "__main__":
    clear_scene()
    create_range_hood()
