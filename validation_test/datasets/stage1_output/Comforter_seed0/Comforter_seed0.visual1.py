import bpy
import bmesh
import math

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
        bsdf.inputs['Roughness'].default_value = 0.8
    return mat

def create_duvet():
    clear_scene()

    # Dimensions
    width = 2.4
    length = 3.0
    thickness = 0.08
    rows, cols = 6, 8 # Quilt grid size
    res_per_patch = 5 # Higher res for better puffiness

    # Materials
    mats_dict = {
        'peach': create_material('PeachPink', (1.0, 0.75, 0.6, 1.0)),
        'lavender': create_material('Lavender', (0.8, 0.7, 0.9, 1.0)),
        'blue': create_material('BlueDotted', (0.6, 0.8, 1.0, 1.0)),
        'cream': create_material('Cream', (0.95, 0.92, 0.8, 1.0)),
        'pale_pink': create_material('PalePink', (1.0, 0.85, 0.85, 1.0))
    }
    mat_list = [mats_dict['peach']] * 3 + [mats_dict['lavender'], mats_dict['blue'], mats_dict['cream'], mats_dict['pale_pink']]

    # Main duvet body
    mesh = bpy.data.meshes.new("DuvetMesh")
    obj = bpy.data.objects.new("Comforter", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    total_x, total_y = cols * res_per_patch, rows * res_per_patch
    verts = []
    for i in range(total_x + 1):
        for j in range(total_y + 1):
            x = (i / total_x) * width - (width / 2)
            y = (j / total_y) * length - (length / 2)
            verts.append(bm.verts.new((x, y, 0)))

    for i in range(total_x):
        for j in range(total_y):
            v1 = verts[i * (total_y + 1) + j]
            v2 = verts[(i + 1) * (total_y + 1) + j]
            v3 = verts[(i + 1) * (total_y + 1) + j + 1]
            v4 = verts[i * (total_y + 1) + j + 1]
            bm.faces.new((v1, v2, v3, v4))

    # Quilting puffiness
    for v in bm.verts:
        nx = (v.co.x + width/2) / width * cols
        ny = (v.co.y + length/2) / length * rows
        lx, ly = nx % 1.0, ny % 1.0
        # Use a more pronounced bubble shape
        z_offset = math.sin(lx * math.pi) * math.sin(ly * math.pi) * 0.07
        v.co.z += z_offset

    # Patchwork coloring
    for face in bm.faces:
        c = face.calc_center_median()
        px = int((c.x + width/2) / width * cols)
        py = int((c.y + length/2) / length * rows)
        px, py = max(0, min(cols-1, px)), max(0, min(rows-1, py))
        # Deterministic selection from the weighted list
        face.material_index = (px + py * cols) % len(mat_list)

    bm.to_mesh(mesh)
    bm.free()

    for m in mat_list:
        obj.data.materials.append(m)

    # Modifiers for body
    solidify = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify.thickness = thickness
    solidify.offset = -1 # Offset downwards
    subsurf = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf.levels = 1

    # Folded Border Strip (at one short end: y = length/2)
    fold_depth = 0.4
    fold_width = width
    
    bm_f = bmesh.new()
    res_x, res_y = 10, 10
    # Create a flat rectangle first
    v_coords = []
    for i in range(res_x + 1):
        for j in range(res_y + 1):
            x = (i / res_x) * fold_width - (fold_width / 2)
            y = (j / res_y) * fold_depth
            v_coords.append((x, y))

    verts_f = []
    for coord in v_coords:
        verts_f.append(bm_f.verts.new(coord))

    for i in range(res_x):
        for j in range(res_y):
            v1 = verts_f[i * (res_y + 1) + j]
            v2 = verts_f[(i+1) * (res_y + 1) + j]
            v3 = verts_f[(i+1) * (res_y + 1) + j + 1]
            v4 = verts_f[i * (res_y + 1) + j + 1]
            bm_f.faces.new((v1, v2, v3, v4))

    # Deform the rectangle into a fold
    for v in bm_f.verts:
        # local y from 0 to fold_depth
        ly = (v.co.y / fold_depth)
        # The fold starts at length/2 and curves back over the duvet
        # Curve: Y moves out slightly then folds back, Z rises in middle
        angle = ly * math.pi
        v.co.y = (length / 2) + math.sin(angle) * (fold_depth * 0.3) - (ly * fold_depth * 0.5)
        v.co.z = math.sin(angle) * (fold_depth * 0.4)

    mesh_f = bpy.data.meshes.new("FoldMesh")
    obj_f = bpy.data.objects.new("BorderFold", mesh_f)
    bpy.context.collection.objects.link(obj_f)
    bm_f.to_mesh(mesh_f)
    bm_f.free()

    # Material for fold (Peach dominant)
    obj_f.data.materials.append(mats_dict['peach'])

    solidify_f = obj_f.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify_f.thickness = thickness * 1.2
    subsurf_f = obj_f.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf_f.levels = 1

if __name__ == "__main__":
    create_duvet()
