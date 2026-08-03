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
        bsdf.inputs['Base Color'].default_value = (0.05, 0.08, 0.12, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.3
        bsdf.inputs['Metallic'].default_value = 0.7
    return mat

def create_knife():
    """Procedurally generates a knife with a wide flat blade and seamless handle."""
    # Dimensions
    h_len = 4.5
    b_len = 12.0
    t_len = 1.5  # Transition zone
    
    h_w = 0.7   # Handle width (X)
    h_t = 0.5   # Handle thickness (Z)
    
    b_base_w = 2.5 # Blade wide base (X)
    b_thick = 0.1  # Blade flat thickness (Z)
    
    res = 32 # resolution of the cross-section circles/ellipses
    
    mesh = bpy.data.meshes.new("Knife")
    obj = bpy.data.objects.new("Knife", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # We will create slices along the Y axis and connect them
    slices = []
    
    # 1. Handle Section (0 to h_len)
    for i in range(2): # Start and end of handle
        y_pos = i * h_len
        slice_verts = []
        for j in range(res):
            angle = (2 * math.pi * j) / res
            x = math.cos(angle) * h_w * 0.5
            z = math.sin(angle) * h_t * 0.5
            slice_verts.append(bm.verts.new((x, y_pos, z)))
        slices.append(slice_verts)

    # 2. Transition Section (h_len to h_len + t_len)
    y_trans = h_len + t_len
    slice_base_blade = []
    for j in range(res):
        angle = (2 * math.pi * j) / res
        # Map ellipse handle to flat wide blade base
        x = math.cos(angle) * b_base_w * 0.5
        z = math.sin(angle) * b_thick * 0.5
        slice_base_blade.append(bm.verts.new((x, y_trans, z)))
    slices.append(slice_base_blade)

    # 3. Blade Section (y_trans to y_trans + b_len)
    b_steps = 20
    for s in range(1, b_steps + 1):
        progress = s / b_steps
        y_pos = y_trans + (progress * b_len)
        
        # Taper width linearly to a point, keep thickness very thin
        current_w = b_base_w * (1.0 - progress)
        current_t = b_thick * (1.0 - (progress * 0.5)) # slight taper in thickness too
        
        slice_verts = []
        for j in range(res):
            angle = (2 * math.pi * j) / res
            x = math.cos(angle) * current_w * 0.5
            z = math.sin(angle) * current_t * 0.5
            slice_verts.append(bm.verts.new((x, y_pos, z)))
        slices.append(slice_verts)

    # Create faces between slices
    for i in range(len(slices) - 1):
        s1 = slices[i]
        s2 = slices[i+1]
        for j in range(res):
            v1 = s1[j]
            v2 = s1[(j + 1) % res]
            v3 = s2[(j + 1) % res]
            v4 = s2[j]
            bm.faces.new((v1, v2, v3, v4))

    # Close the end cap (handle start) and tip (blade end)
    # Handle start
    bm.faces.new(slices[0])
    # Blade tip - merge all last verts to a single point
    last_slice = slices[-1]
    tip_vert = bm.verts.new((0, slices[-1][0].co.y, 0))
    for v in last_slice:
        # Create triangles to close the tip
        idx = last_slice.index(v)
        v_next = last_slice[(idx + 1) % res]
        bm.faces.new((v, v_next, tip_vert))

    # Remove doubles for a clean mesh at the tip
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)

    bm.to_mesh(mesh)
    bm.free()

    # Center the object
    bbox_min = Vector((min(v.co.x for v in mesh.vertices), 
                      min(v.co.y for v in mesh.vertices), 
                      min(v.co.z for v in mesh.vertices)))
    bbox_max = Vector((max(v.co.x for v in mesh.vertices), 
                      max(v.co.y for v in mesh.vertices), 
                      max(v.co.z for v in mesh.vertices)))
    center = (bbox_min + bbox_max) / 2
    obj.location = -center

    # Smoothing and Subdiv
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
