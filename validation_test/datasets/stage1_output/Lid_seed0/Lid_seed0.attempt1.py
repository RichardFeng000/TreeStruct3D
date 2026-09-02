import bpy
import bmesh
import math

# Clear scene
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for block in list(bpy.data.meshes):
    bpy.data.meshes.remove(block)
for block in list(bpy.data.materials):
    bpy.data.materials.remove(block)

# Parameters
lid_radius = 1.0
dome_height = 0.08
rim_depth = 0.02
rim_thickness = 0.03
spin_segments = 96

def make_material(name, color, roughness=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

# === Lid body ===
bm = bmesh.new()

profile = []

# Top surface - slightly domed (parabolic)
n_top = 40
for i in range(n_top + 1):
    t = i / n_top
    r = t * lid_radius
    h = dome_height * (1 - t * t * 0.7)  # More pronounced dome
    profile.append((r, h))

# Thin rim going down
profile.append((lid_radius, h - rim_depth))
profile.append((lid_radius - rim_thickness, h - rim_depth))

# Underside back to center
n_bot = 24
under_r = lid_radius - rim_thickness
for i in range(1, n_bot + 1):
    t = i / n_bot
    r = under_r * (1 - t)
    h = (h - rim_depth) * (1 - t) * 0.15
    profile.append((r, h))
profile.append((0.0, 0.0))

# Create profile vertices and edges
verts = [bm.verts.new((r, 0, z)) for r, z in profile]
edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]

# Spin around Z axis
geom = bm.verts[:] + bm.edges[:]
bmesh.ops.spin(
    bm, geom=geom, axis=(0, 0, 1), cent=(0, 0, 0),
    angle=2 * math.pi, steps=spin_segments,
    use_merge=True, use_duplicate=False
)

bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

lid_mesh = bpy.data.meshes.new("LidMesh")
bm.to_mesh(lid_mesh)
bm.free()
lid_obj = bpy.data.objects.new("PotLid", lid_mesh)
bpy.context.collection.objects.link(lid_obj)

for poly in lid_mesh.polygons:
    poly.use_smooth = True

# Bevel for smooth edge transitions
bevel = lid_obj.modifiers.new("Bevel", 'BEVEL')
bevel.width = 0.008
bevel.segments = 4
bevel.limit_method = 'ANGLE'
bevel.angle_limit = math.radians(30)

# === Knob handle ===
bm2 = bmesh.new()

knob_r = 0.08
knob_body_h = 0.06
knob_cap_h = 0.05
knob_base_z = dome_height
knob_seg = 64

# Cylindrical body (pink)
bot_ring = []
top_ring = []
for i in range(knob_seg):
    a = 2 * math.pi * i / knob_seg
    x, y = knob_r * math.cos(a), knob_r * math.sin(a)
    bot_ring.append(bm2.verts.new((x, y, knob_base_z)))
    top_ring.append(bm2.verts.new((x, y, knob_base_z + knob_body_h)))

# Side faces (pink)
for i in range(knob_seg):
    j = (i + 1) % knob_seg
    f = bm2.faces.new((bot_ring[i], bot_ring[j], top_ring[j], top_ring[i]))
    f.material_index = 0

# Bottom face (pink)
bot_face = bm2.faces.new(list(reversed(bot_ring)))
bot_face.material_index = 0

# Rounded hemispherical cap (dark blue)
cap_rings = 20
prev = top_ring
for ri in range(1, cap_rings):
    t = ri / cap_rings
    ang = t * math.pi * 0.5
    rr = knob_r * math.cos(ang)
    rz = knob_base_z + knob_body_h + knob_cap_h * math.sin(ang)
    curr = []
    for i in range(knob_seg):
        a = 2 * math.pi * i / knob_seg
        curr.append(bm2.verts.new((rr * math.cos(a), rr * math.sin(a), rz)))
    for i in range(knob_seg):
        j = (i + 1) % knob_seg
        f = bm2.faces.new((prev[i], prev[j], curr[j], curr[i]))
        f.material_index = 1
    prev = curr

# Cap apex
apex = bm2.verts.new((0, 0, knob_base_z + knob_body_h + knob_cap_h))
for i in range(knob_seg):
    j = (i + 1) % knob_seg
    f = bm2.faces.new((prev[i], prev[j], apex))
    f.material_index = 1

bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)

knob_mesh = bpy.data.meshes.new("KnobMesh")
bm2.to_mesh(knob_mesh)
bm2.free()
knob_obj = bpy.data.objects.new("Knob", knob_mesh)
bpy.context.collection.objects.link(knob_obj)

for poly in knob_mesh.polygons:
    poly.use_smooth = True

# === Materials ===
mat_lid = make_material("LidMat", (0.82, 0.70, 0.63), 0.55)
mat_pink = make_material("PinkMat", (0.88, 0.35, 0.45), 0.45)
mat_blue = make_material("BlueMat", (0.04, 0.08, 0.25), 0.45)

lid_obj.data.materials.append(mat_lid)
knob_obj.data.materials.append(mat_pink)
knob_obj.data.materials.append(mat_blue)

# Parent knob to lid
knob_obj.parent = lid_obj