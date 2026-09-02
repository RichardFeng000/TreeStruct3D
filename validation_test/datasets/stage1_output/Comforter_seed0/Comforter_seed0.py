import bpy
import bmesh
import math
import random

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.9
    return mat

def create_duvet():
    clear_scene()

    # Dimensions
    width = 2.4
    length = 3.0
    thickness = 0.06
    rows, cols = 6, 8 # Patchwork grid size
    res_per_patch = 6  # Resolution within each patch for puffiness

    # Materials
    mats_dict = {
        'peach': create_material('PeachPink', (1.0, 0.75, 0.6, 1.0)),
        'lavender': create_material('Lavender', (0.8, 0.7, 0.9, 1.0)),
        'blue': create_material('BlueDotted', (0.6, 0.8, 1.0, 1.0)),
        'cream': create_material('Cream', (0.95, 0.92, 0.8, 1.0)),
        'pale_pink': create_material('PalePink', (1.0, 0.85, 0.85, 1.0))
    }
    # Distribution list to favor peach-pink as dominant background
    mat_pool = [mats_dict['peach']] * 4 + [mats_dict['lavender'], mats_dict['blue'], mats_dict['cream'], mats_dict['pale_pink']]

    # --- Main duvet body ---
    mesh = bpy.data.meshes.new("DuvetMesh")
    obj = bpy.data.objects.new("Comforter", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    total_x, total_y = cols * res_per_patch, rows * res_per_patch
    verts_grid = []
    for i in range(total_x + 1):
        for j in range(total_y + 1):
            # Centering the duvet at origin
            x = (i / total_x) * width - (width / 2)
            y = (j / total_y) * length - (length / 2)
            verts_grid.append(bm.verts.new((x, y, 0)))

    for i in range(total_x):
        for j in range(total_y):
            v1 = verts_grid[i * (total_y + 1) + j]
            v2 = verts_grid[(i + 1) * (total_y + 1) + j]
            v3 = verts_grid[(i + 1) * (total_y + 1) + j + 1]
            v4 = verts_grid[i * (total_y + 1) + j + 1]
            bm.faces.new((v1, v2, v3, v4))

    # Quilting puffiness and Patchwork logic
    for face in bm.faces:
        c = face.calc_center_median()
        # Determine which patch this face belongs to
        px = int((c.x + width/2) / width * cols)
        py = int((c.y + length/2) / length * rows)
        px, py = max(0, min(cols-1, px)), max(0, min(rows-1, py))
        face.material_index = (px + py * cols) % len(mat_pool)

    for v in bm.verts:
        # Local coordinate relative to patch grid for periodic puffing
        lx = ((v.co.x + width/2) / width) * cols
        ly = ((v.co.y + length/2) / length) * rows
        # Create "bubbles" by using sin of fractional part
        puff_x = math.sin(lx * math.pi) 
        puff_y = math.sin(ly * math.pi)
        v.co.z += puff_x * puff_y * 0.05

    bm.to_mesh(mesh)
    bm.free()

    # Assign materials to the object slots
    for m in mat_pool:
        obj.data.materials.append(m)

    # Modifiers for main body
    solidify = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify.thickness = thickness
    solidify.offset = -1 
    subsurf = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf.levels = 2

    # --- Folded Border Strip ---
    fold_depth = 0.5
    fold_width = width
    
    bm_f = bmesh.new()
    res_x, res_y = 15, 15
    verts_f = []
    for i in range(res_x + 1):
        for j in range(res_y + 1):
            # Start from the edge of the duvet (y=length/2)
            x = (i / res_x) * fold_width - (fold_width / 2)
            y = (j / res_y) * fold_depth
            verts_f.append(bm_f.verts.new((x, y, 0))) # Explicitly 3D vector

    for i in range(res_x):
        for j in range(res_y):
            v1 = verts_f[i * (res_y + 1) + j]
            v2 = verts_f[(i+1) * (res_y + 1) + j]
            v3 = verts_f[(i+1) * (res_y + 1) + j + 1]
            v4 = verts_f[i * (res_y + 1) + j + 1]
            bm_f.faces.new((v1, v2, v3, v4))

    # Deform the rectangle into a fold that curves back over the duvet
    for v in bm_f.verts:
        # Normalizing y to [0, 1]
        norm_y = v.co.y / fold_depth
        # Curve it: start at length/2, go up and then bend back towards center
        # The angle represents the progress along the strip's depth
        angle = norm_y * math.pi * 0.8
        v.co.y = (length / 2) + math.sin(angle) * (fold_depth * 0.3) - (norm_y * fold_depth * 0.4)
        v.co.z = math.sin(angle) * (fold_depth * 0.5)
        # Add slight irregularities to make it look like fabric
        v.co.x += random.uniform(-0.01, 0.01)

    mesh_f = bpy.data.meshes.new("FoldMesh")
    obj_f = bpy.data.objects.new("BorderFold", mesh_f)
    bpy.context.collection.objects.link(obj_f)
    bm_f.to_mesh(mesh_f)
    bm_f.free()

    # Material for fold (peach-pink dominant)
    obj_f.data.materials.append(mats_dict['peach'])

    solidify_f = obj_f.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify_f.thickness = thickness * 1.1
    solidify_f.offset = -1
    subsurf_f = obj_f.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf_f.levels = 2

if __name__ == "__main__":
    create_duvet()
