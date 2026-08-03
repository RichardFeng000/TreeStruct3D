import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

# ---------- clear scene ----------
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for col in (bpy.data.meshes, bpy.data.materials, bpy.data.curves, bpy.data.lights, bpy.data.cameras):
    for b in list(col):
        col.remove(b)

random.seed(7)

# ---------- materials ----------
def make_mat(name, color, roughness=0.4, metallic=0.0, clearcoat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = clearcoat
    elif "Clearcoat" in bsdf.inputs:
        bsdf.inputs["Clearcoat"].default_value = clearcoat
    return m

mat_body = make_mat("StrawberryFlesh", (0.88, 0.38, 0.34), roughness=0.24, clearcoat=0.28)
mat_seed = make_mat("Achene", (0.96, 0.91, 0.74), roughness=0.45)
mat_green = make_mat("Calyx", (0.18, 0.52, 0.16), roughness=0.50)
mat_stem = make_mat("Stem", (0.32, 0.50, 0.20), roughness=0.55)

# ---------- strawberry body ----------
H = 3.0
profile = [
    (0.00, 0.04),
    (0.02, 0.14),
    (0.04, 0.27),
    (0.08, 0.47),
    (0.14, 0.69),
    (0.22, 0.91),
    (0.32, 1.09),
    (0.43, 1.25),
    (0.55, 1.37),
    (0.66, 1.44),
    (0.74, 1.47),
    (0.81, 1.45),
    (0.87, 1.35),
    (0.92, 1.19),
    (0.96, 0.95),
    (1.00, 0.60),
]
segments = 96

def profile_radius(hf):
    if hf <= profile[0][0]:
        return profile[0][1]
    if hf >= profile[-1][0]:
        return profile[-1][1]
    for i in range(len(profile) - 1):
        h0, r0 = profile[i]
        h1, r1 = profile[i + 1]
        if h0 <= hf <= h1:
            t = (hf - h0) / (h1 - h0) if h1 > h0 else 0.0
            ts = t * t * (3 - 2 * t)
            return r0 + (r1 - r0) * ts
    return profile[-1][1]

def profile_deriv(hf, eps=0.008):
    return (profile_radius(hf + eps) - profile_radius(hf - eps)) / (2 * eps)

mesh = bpy.data.meshes.new("StrawberryBody")
bm = bmesh.new()
n_prof = 90
rings = []
for i in range(n_prof + 1):
    hf = i / n_prof
    r = profile_radius(hf)
    h = hf * H
    ring = []
    for s in range(segments):
        ang = 2 * math.pi * s / segments
        nz = 0.010 * math.sin(ang * 3.0 + hf * 9.0) * math.sin(hf * 7.0)
        nz += 0.006 * math.sin(ang * 7.0 - hf * 11.0)
        rr = r + nz
        x = rr * math.cos(ang)
        y = rr * math.sin(ang)
        v = bm.verts.new((x, y, h))
        ring.append(v)
    rings.append(ring)

for i in range(n_prof):
    r0 = rings[i]
    r1 = rings[i + 1]
    for s in range(segments):
        s2 = (s + 1) % segments
        try:
            bm.faces.new([r0[s], r0[s2], r1[s2], r1[s]])
        except ValueError:
            pass

# bottom tip
cb = bm.verts.new((0.0, 0.0, -0.02))
r0 = rings[0]
for s in range(segments):
    s2 = (s + 1) % segments
    try:
        bm.faces.new([cb, r0[s2], r0[s]])
    except ValueError:
        pass
# top cap
ct = bm.verts.new((0.0, 0.0, H))
rN = rings[-1]
for s in range(segments):
    s2 = (s + 1) % segments
    try:
        bm.faces.new([ct, rN[s], rN[s2]])
    except ValueError:
        pass

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh)
bm.free()
body_obj = bpy.data.objects.new("StrawberryBody", mesh)
bpy.context.collection.objects.link(body_obj)
body_obj.data.materials.append(mat_body)

# ---------- seed positions (phyllotaxis) ----------
N_SEEDS = 220
golden = math.pi * (3.0 - math.sqrt(5.0))
hf_min, hf_max = 0.05, 0.92

seed_data = []
for i in range(N_SEEDS):
    t = i / max(1, N_SEEDS - 1)
    hf = hf_min + (hf_max - hf_min) * t
    hf += random.uniform(-0.015, 0.015)
    hf = max(hf_min * 0.5, min(hf_max + 0.02, hf))
    theta = i * golden + random.uniform(-0.12, 0.12)
    r = profile_radius(hf)
    rprime = profile_deriv(hf)
    h = hf * H
    P = Vector((r * math.cos(theta), r * math.sin(theta), h))
    nrm = Vector((H * math.cos(theta), H * math.sin(theta), -rprime))
    nrm.normalize()
    t_theta = Vector((-math.sin(theta), math.cos(theta), 0.0))
    t_hf = nrm.cross(t_theta)
    t_hf.normalize()
    seed_data.append((P, nrm, t_hf, t_theta))

# ---------- carve dimples ----------
bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
kd = KDTree(len(bm.verts))
for i, v in enumerate(bm.verts):
    kd.insert(v.co.copy(), i)
kd.balance()

dimple_radius = 0.12
dimple_depth = 0.022
sigma = 0.065

for (P, nrm, t_hf, t_theta) in seed_data:
    for (co, idx, dist) in kd.find_range(P, dimple_radius):
        v = bm.verts[idx]
        d = (v.co - P).length
        falloff = math.exp(-((d / sigma) ** 2))
        v.co -= nrm * (dimple_depth * falloff)

bm.to_mesh(mesh)
bm.free()

# ---------- seeds ----------
seed_mesh = bpy.data.meshes.new("Seeds")
bm = bmesh.new()
bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
template_verts = [v.co.copy() for v in bm.verts]
template_faces = [tuple(v.index for v in f.verts) for f in bm.faces]
bm.clear()

sx, sy, sz = 0.032, 0.07, 0.035
raise_out = 0.025

for (P, nrm, t_hf, t_theta) in seed_data:
    sfac = random.uniform(0.75, 1.05)
    spin = random.uniform(-0.7, 0.7)
    cs, sn = math.cos(spin), math.sin(spin)
    ax = nrm * (sx * sfac)
    ay = (t_hf * cs + t_theta * sn) * (sy * sfac)
    az = (-t_hf * sn + t_theta * cs) * (sz * sfac)
    origin = P + nrm * raise_out
    vmap = {}
    for j, tv in enumerate(template_verts):
        co = origin + ax * tv.x + ay * tv.y + az * tv.z
        vmap[j] = bm.verts.new(co)
    for f in template_faces:
        try:
            bm.faces.new([vmap[j] for j in f])
        except ValueError:
            pass

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(seed_mesh)
bm.free()
seed_obj = bpy.data.objects.new("Seeds", seed_mesh)
bpy.context.collection.objects.link(seed_obj)
seed_obj.data.materials.append(mat_seed)

# ---------- calyx ----------
calyx_mesh = bpy.data.meshes.new("Calyx")
bm = bmesh.new()

def build_sepal(bm, length, max_width, n_u, n_v, droop_amp, crinkle_amp, tilt, base_angle, z_base, scale_z=1.0):
    ua = 0.45 / 1.15
    wmax = (ua ** 0.45) * ((1 - ua) ** 0.7)
    width_scale = max_width / wmax

    def width(u):
        return (u ** 0.45) * ((1 - u) ** 0.7) * width_scale

    base_vert = bm.verts.new((0.0, 0.0, 0.0))
    rows = [base_vert]
    for i in range(1, n_u + 1):
        u = i / n_u
        w = width(u)
        row = []
        for j in range(-n_v, n_v + 1):
            v = j / n_v
            x = u * length
            y = v * w
            cup = 0.08 * (1 - 0.4 * u) * (v * v) * scale_z
            crinkle = crinkle_amp * math.sin(u * 6.0 + base_angle * 2.0) * math.sin(v * 3.0 + 0.5)
            edge_wave = crinkle_amp * 0.9 * math.sin(u * 10.0 + base_angle) * (v * v) * (1 - u * 0.6)
            droop = -droop_amp * (u ** 1.8)
            z = (cup + crinkle + edge_wave + droop) * scale_z
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)

    row1 = rows[1]
    for j in range(-n_v, n_v):
        a = row1[j + n_v]
        b = row1[j + n_v + 1]
        try:
            bm.faces.new([base_vert, b, a])
        except ValueError:
            pass
    for i in range(1, n_u):
        r0 = rows[i]
        r1 = rows[i + 1]
        for j in range(-n_v, n_v):
            a = r0[j + n_v]
            b = r0[j + n_v + 1]
            c = r1[j + n_v + 1]
            d = r1[j + n_v]
            try:
                bm.faces.new([a, b, c, d])
            except ValueError:
                pass

    all_verts = [base_vert] + [v for row in rows[1:] for v in row]
    M = Matrix.Translation((0.0, 0.0, z_base)) @ Matrix.Rotation(base_angle, 4, 'Z') @ Matrix.Rotation(tilt, 4, 'Y')
    for v in all_verts:
        v.co = M @ v.co
    return all_verts

z_top = H * 0.99
for k in range(5):
    ang = 2 * math.pi * k / 5
    build_sepal(bm, length=1.7, max_width=0.6, n_u=20, n_v=8,
                droop_amp=0.12, crinkle_amp=0.055, tilt=0.4, base_angle=ang, z_base=z_top)
for k in range(5):
    ang = 2 * math.pi * k / 5 + math.pi / 5
    build_sepal(bm, length=0.95, max_width=0.38, n_u=14, n_v=6,
                droop_amp=0.06, crinkle_amp=0.035, tilt=0.15, base_angle=ang, z_base=z_top + 0.04, scale_z=0.95)

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(calyx_mesh)
bm.free()
calyx_obj = bpy.data.objects.new("Calyx", calyx_mesh)
bpy.context.collection.objects.link(calyx_obj)
calyx_obj.data.materials.append(mat_green)

sol = calyx_obj.modifiers.new("Solidify", 'SOLIDIFY')
sol.thickness = 0.025
sol.offset = 0.0
sub = calyx_obj.modifiers.new("Subsurf", 'SUBSURF')
sub.levels = 1
sub.render_levels = 2

# ---------- stem ----------
stem_mesh = bpy.data.meshes.new("Stem")
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=24,
                      radius1=0.075, radius2=0.05, depth=0.85)
bmesh.ops.translate(bm, vec=(0.0, 0.0, 0.425), verts=list(bm.verts))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(stem_mesh)
bm.free()
stem_obj = bpy.data.objects.new("Stem", stem_mesh)
bpy.context.collection.objects.link(stem_obj)
stem_obj.location = (0.0, 0.0, H - 0.03)
stem_obj.rotation_euler = (math.radians(10.0), math.radians(-8.0), 0.0)
stem_obj.data.materials.append(mat_stem)

# ---------- mottled brown-orange patches ----------
bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
for i in range(20):
    hf = random.uniform(0.1, 0.88)
    theta = random.uniform(0, 2 * math.pi)
    r = profile_radius(hf)
    h = hf * H
    P = Vector((r * math.cos(theta), r * math.sin(theta), h))
    nrm = Vector((H * math.cos(theta), H * math.sin(theta), -profile_deriv(hf)))
    nrm.normalize()
    for v in bm.verts:
        d = (v.co - P).length
        if d < 0.5:
            falloff = math.exp(-(d / 0.22) ** 2)
            v.co += nrm * (0.015 * falloff)
bm.to_mesh(mesh)
bm.free()

# ---------- smooth shading ----------
for obj in (body_obj, seed_obj, calyx_obj, stem_obj):
    for p in obj.data.polygons:
        p.use_smooth = True

# ---------- assemble ----------
for child in (seed_obj, calyx_obj, stem_obj):
    child.parent = body_obj
body_obj.name = "Strawberry"

bpy.context.view_layer.update()