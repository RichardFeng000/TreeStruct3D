import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene of all objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material():
    """Creates a deep navy blue-gray material."""
    mat = bpy.data.materials.new(name="KnifeMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Deep navy blue-gray color (RGBA)
        bsdf.inputs['Base Color'].default_value = (0.05, 0.08, 0.15, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.3
        bsdf.inputs['Metallic'].default_value = 0.6
    return mat

def create_knife():
    """Procedurally generates a knife with a wide flat blade and seamless handle."""
    # Dimensions
    h_len = 4.0
    b_len = 10.0
    t_len = 1.5 # transition length
    
    h_w = 0.8   # handle width (x)
    h_t = 0.6   # handle thickness (z)
    
    b_base_w = 2.2 # blade base wide x
    b_thick = 0.1  # blade flat z
    
    res = 32
    
    mesh = bpy.data.meshes.new("Knife")
    obj = bpy.data.objects.new("Knife", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # Generate cross-section vertices for the handle base
    verts_base = []
    for i in range(res):
        angle = (2 * math.pi * i) / res
        x = math.cos(angle) * h_w * 0.5
        z = math.sin(angle) * h_t * 0.5
        verts_base.append(bm.verts.new((x, 0, z)))
    
    face = bm.faces.new(verts_base)

    # 1. Extrude Handle
    last_face = face
    h_steps = 8
    for s in range(h_steps):
        res_ext = bmesh.ops.extrude_face_region(bm, geom=[last_face])
        verts_ext = [v for v in res_ext['geom'] if isinstance(v, bmesh.types.BMVert)]
        faces_ext = [f for f in res_ext['geom'] if isinstance(f, bmesh.types.BMFace)]
        for v in verts_ext:
            v.co.y += h_len / h_steps
        last_face = faces_ext[0]

    # 2. Transition from Handle to Blade Base (Widening and Flattening)
    res_trans = bmesh.ops.extrude_face_region(bm, geom=[last_face])
    verts_trans = [v for v in res_trans['geom'] if isinstance(v, bmesh.types.BMVert)]
    faces_trans = [f for f in res_trans['geom'] if isinstance(f, bmesh.types.BMFace)]
    
    for v in verts_trans:
        # Find relative position to map ellipse -> wide flat rectangle
        v_old = [vert for vert in bm.verts if vert != v and vert.co.y < (h_len + 0.1)][-1] # approximate
        # Instead of complex mapping, we use the index or current pos
        # Calculate angle to preserve distribution
        angle = math.atan2(v.co.z, v.co.x)
        v.co.y += t_len
        v.co.x = math.cos(angle) * (b_base_w * 0.5)
        v.co.z = math.sin(angle) * (b_thick * 0.5)

    last_face = faces_trans[0]

    # 3. Extrude Blade (Tapering to a point)
    b_steps = 20
    for s in range(b_steps):
        res_ext = bmesh.ops.extrude_face_region(bm, geom=[last_face])
        verts_ext = [v for v in res_ext['geom'] if isinstance(v, bmesh.types.BMVert)]
        faces_ext = [f for f in res_ext['geom'] if isinstance(f, bmesh.types.BMFace)]
        
        progress = (s + 1) / b_steps
        dy = b_len / b_steps
        
        # Taper width linearly to point; thickness also tapers slightly
        taper_w = 1.0 - progress
        taper_z = (0.7 + 0.3 * (1.0 - progress)) # keep some thickness near base, thin at tip
        
        for v in verts_ext:
            v.co.y += dy
            # Curve the blade slightly outwards then inwards
            curve_offset = math.sin(progress * math.pi) * 0.5
            v.co.x *= taper_w
            v.co.z *= (taper_z * (b_thick / b_thick)) # maintain flat profile
            # Apply slight curve to the spine/edge if desired, but keep it simple here
        
        last_face = faces_ext[0]

    # 4. Close the Tip
    tip_verts = [v for v in bm.verts if v.co.y > (h_len + t_len + b_len - 0.1)]
    if tip_verts:
        center_pt = Vector((0, max(v.co.y for v in tip_verts), 0))
        for v in tip_verts:
            v.co = center_pt
        bmesh.ops.remove_doubles(bm, verts=tip_verts, dist=0.01)

    bm.to_mesh(mesh)
    bm.free()

    # Center and Scale
    bbox_min = Vector((min(v.co.x for v in mesh.vertices), 
                      min(v.co.y for v in mesh.vertices), 
                      min(v.co.z for v in mesh.vertices)))
    bbox_max = Vector((max(v.co.x for v in mesh.vertices), 
                      max(v.co.y for v in mesh.vertices), 
                      max(v.co.z for v in mesh.vertices)))
    center = (bbox_min + bbox_max) / 2
    obj.location = -center

    # Smooth and Subdivide for seamless blend
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    for poly in mesh.polygons:
        poly.use_smooth = True

    return obj

if __name__ == "__main__":
    clear_scene()
    knife_obj = create_knife()
    knife_mat = create_material()
    if knife_obj.data.materials:
        knife_obj.data.materials[0] = knife_mat
    else:
        knife_obj.data.materials.append(knife_mat)
