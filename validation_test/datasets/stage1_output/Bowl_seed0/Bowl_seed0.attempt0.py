import bpy
import bmesh
import math

# ===== Clear scene =====
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for block in list(bpy.data.meshes):
    bpy.data.meshes.remove(block)
for block in list(bpy.data.materials):
    bpy.data.materials.remove(block)
for block in list(bpy.data.cameras):
    bpy.data.cameras.remove(block)
for block in list(bpy.data.lights):
    bpy.data.lights.remove(block)

# ===== Bowl parameters =====
rim_radius = 1.10
base_radius = 0.35
bowl_height = 0.90
bottom_thickness = 0.08
wall_thickness = 0.05
rim_round = 0.065
segments = 128

# ===== Build cross-section profile =====
# (radius, z, material_index) — 0 = dark exterior, 1 = deep blue-gray interior
profile = []

# Exterior wall — base edge to rim
n_ext = 44
for i in range(n_ext + 1):
    t = i / n_ext
    ease = math.sin(t * math.pi / 2)
    r = base_radius + (rim_radius - base_radius) * ease
    z = t * bowl_height
    profile.append((r, z, 0))

# Rounded rim — arc over the top
rim_cz = bowl_height
rim_cr = rim_radius - rim_round
n_rim = 24
for i in range(1, n_rim):
    ang = math.pi * i / n_rim
    r = rim_cr + rim_round * math.cos(ang)
    z = rim_cz + rim_round * math.sin(ang)
    mat = 0 if i <= n_rim // 2 else 1
    profile.append((r, z, mat))

# Interior wall — rim to inner base
inner_rim_r = rim_radius - 2 * rim_round
inner_base_r = base_radius - wall_thickness * 0.15
inner_height = bowl_height - bottom_thickness
n_int = 44
for i in range(1, n_int + 1):
    t = i / n_int
    ease = math.sin((1 - t) * math.pi / 2)
    r = inner_base_r + (inner_rim_r - inner_base_r) * ease
    z = inner_height * (1 - t)
    profile.append((r, z, 1))

# ===== Create mesh =====
mesh_data = bpy.data.meshes.new("Bowl")
bowl_obj = bpy.data.objects.new("Bowl", mesh_data)
bowl_obj.location = (0, 0, 0)
bpy.context.collection.objects.link(bowl_obj)

bm = bmesh.new()

# Vertex rings
rings = []
for r, z, _ in profile:
    ring = []
    for s in range(segments):
        ang = 2 * math.pi * s / segments
        v = bm.verts.new((r * math.cos(ang), r * math.sin(ang), z))
        ring.append(v)
    rings.append(ring)

# Side faces
for i in range(len(rings) - 1):
    ra = rings[i]
    rb = rings[i + 1]
    mat = profile[i][2]
    for s in range(segments):
        sn = (s + 1) % segments
        f = bm.faces.new([ra[s], ra[sn], rb[sn], rb[s]])
        f.material_index = mat

# Exterior base cap
base_cv = bm.verts.new((0, 0, 0))
for s in range(segments):
    sn = (s + 1) % segments
    f = bm.faces.new([base_cv, rings[0][sn], rings[0][s]])
    f.material_index = 0

# Interior base cap
inner_cv = bm.verts.new((0, 0, inner_height))
for s in range(segments):
    sn = (s + 1) % segments
    f = bm.faces.new([inner_cv, rings[-1][s], rings[-1][sn]])
    f.material_index = 1

# Recalculate normals
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

# Smooth shading
for f in bm.faces:
    f.smooth = True

bm.to_mesh(mesh_data)
bm.free()

# ===== Materials =====
mat_ext = bpy.data.materials.new("DarkExterior")
mat_ext.use_nodes = True
bsdf_e = mat_ext.node_tree.nodes["Principled BSDF"]
bsdf_e.inputs["Base Color"].default_value = (0.04, 0.035, 0.06, 1.0)
bsdf_e.inputs["Roughness"].default_value = 0.28

mat_int = bpy.data.materials.new("BlueGrayInterior")
mat_int.use_nodes = True
bsdf_i = mat_int.node_tree.nodes["Principled BSDF"]
bsdf_i.inputs["Base Color"].default_value = (0.10, 0.14, 0.21, 1.0)
bsdf_i.inputs["Roughness"].default_value = 0.20

mesh_data.materials.append(mat_ext)
mesh_data.materials.append(mat_int)

# ===== Subdivision surface =====
mod = bowl_obj.modifiers.new("Subsurf", 'SUBSURF')
mod.levels = 1
mod.render_levels = 2

# Smooth shading
for poly in mesh_data.polygons:
    poly.use_smooth = True

bpy.context.view_layer.objects.active = bowl_obj
bowl_obj.select_set(True)