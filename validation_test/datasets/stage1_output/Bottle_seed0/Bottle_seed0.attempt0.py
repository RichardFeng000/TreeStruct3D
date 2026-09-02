import bpy
import bmesh
import math

# ============================================================
# Clear scene
# ============================================================
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for block in list(bpy.data.meshes):
    bpy.data.meshes.remove(block)
for block in list(bpy.data.materials):
    bpy.data.materials.remove(block)
for block in list(bpy.data.curves):
    bpy.data.curves.remove(block)

# ============================================================
# Materials
# ============================================================
def make_material(name, color, roughness=0.4, metallic=0.0, transmission=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        for tname in ["Transmission Weight", "Transmission"]:
            if tname in bsdf.inputs:
                bsdf.inputs[tname].default_value = transmission
                break
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = 1.45
    return mat

mat_glass = make_material("BottleGlass", (0.04, 0.28, 0.08), 0.05, 0.0, 0.75)
mat_cap = make_material("Cap", (0.76, 0.76, 0.80), 0.25, 0.85)
mat_label = make_material("LabelBase", (0.96, 0.94, 0.88), 0.7)
mat_red = make_material("LabelRed", (0.82, 0.12, 0.15), 0.5)
mat_blue = make_material("LabelBlue", (0.08, 0.22, 0.65), 0.5)
mat_gold = make_material("LabelGold", (0.88, 0.68, 0.18), 0.3, 0.7)
mat_green = make_material("LabelGreen", (0.10, 0.48, 0.20), 0.5)

# ============================================================
# Helpers
# ============================================================
def revolve(name, profile, segments=64, material=None):
    mesh = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0, h)) for r, h in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(
        bm,
        geom=edges + verts,
        axis=(0, 0, 1),
        cent=(0, 0, 0),
        angle=2 * math.pi,
        steps=segments,
        use_merge=True,
    )
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    if material:
        obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def radius_at(h, profile):
    for i in range(len(profile) - 1):
        r1, h1 = profile[i]
        r2, h2 = profile[i + 1]
        if h1 <= h <= h2:
            t = (h - h1) / (h2 - h1) if h2 > h1 else 0
            return r1 * (1 - t) + r2 * t
    return 0.0


# ============================================================
# Bottle body profile (bottom → top)
# ============================================================
r_neck = 0.26
p = []

# Bottom (closed, flat with chamfer)
p.append((0.0, 0.0))
p.append((0.78, 0.0))
p.append((0.86, 0.03))
p.append((0.93, 0.08))
p.append((0.97, 0.15))
p.append((1.0, 0.25))

# Tapered conical body with subtle belly curve
for i in range(1, 19):
    t = i / 18
    r = 1.0 * (1 - t) + 0.50 * t + 0.055 * math.sin(t * math.pi * 0.85)
    h = 0.25 + t * 2.6
    p.append((r, h))

# Shoulder transition (body → neck)
for i in range(1, 11):
    t = i / 10
    s = t * t * (3 - 2 * t)
    r = 0.50 * (1 - s) + r_neck * s
    h = 2.85 + t * 0.5
    p.append((r, h))

# Neck (narrow cylindrical)
for i in range(1, 6):
    t = i / 5
    r = r_neck * (1 - t * 0.015)
    h = 3.35 + t * 0.6
    p.append((r, h))

# Neck ring and lip
h3 = 3.95
p.append((r_neck * 1.10, h3))
p.append((r_neck * 1.10, h3 + 0.05))
p.append((r_neck * 0.93, h3 + 0.07))
p.append((r_neck * 0.90, h3 + 0.09))

bottle = revolve("Bottle", p, 72, mat_glass)
sub = bottle.modifiers.new("Subsurf", 'SUBSURF')
sub.levels = 1
sub.render_levels = 2
bev = bottle.modifiers.new("Bevel", 'BEVEL')
bev.width = 0.004
bev.segments = 2

# ============================================================
# Cap (small rounded cap)
# ============================================================
cp = []
cap_r0 = r_neck * 1.14
cap_r1 = r_neck * 1.06
cap_h0 = h3 + 0.05
cap_h1 = h3 + 0.40

# Inside + bottom edge
cp.append((r_neck * 0.92, cap_h0))
cp.append((cap_r0, cap_h0 + 0.01))
cp.append((cap_r0, cap_h0 + 0.04))

# Slightly tapered sides
for i in range(1, 7):
    t = i / 6
    r = cap_r0 * (1 - t) + cap_r1 * t
    h = cap_h0 + 0.04 + t * (cap_h1 - cap_h0 - 0.04)
    cp.append((r, h))

# Rounded dome top
for i in range(1, 11):
    t = i / 10
    a = t * math.pi / 2
    r = cap_r1 * math.cos(a)
    h = cap_h1 + cap_r1 * math.sin(a) * 0.65
    cp.append((r, h))
cp.append((0.0, cap_h1 + cap_r1 * 0.65))

cap = revolve("Cap", cp, 64, mat_cap)
sub2 = cap.modifiers.new("Subsurf", 'SUBSURF')
sub2.levels = 1
sub2.render_levels = 2

# ============================================================
# Label band (decorative, around mid-section)
# ============================================================
lh0, lh1 = 1.05, 2.35
lthick = 0.010

lp = []
for i in range(25):
    t = i / 24
    h = lh0 + t * (lh1 - lh0)
    r = radius_at(h, p) + lthick
    lp.append((r, h))

label = revolve("Label", lp, 72, mat_label)

# ============================================================
# Label pattern: vertical colored stripes
# ============================================================
colors = [mat_red, mat_blue, mat_gold, mat_green]
n_stripes = 16
sw = 0.04  # angular half-width

for i in range(n_stripes):
    ang = i * (2 * math.pi / n_stripes)
    color = colors[i % len(colors)]

    mesh = bpy.data.meshes.new(f"Stripe_{i}")
    obj = bpy.data.objects.new(f"Stripe_{i}", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    grid = []
    for j in range(7):
        a = ang - sw + j * (2 * sw / 6)
        row = []
        for k in range(13):
            t = k / 12
            h = lh0 + 0.08 + t * (lh1 - lh0 - 0.16)
            r = radius_at(h, p) + lthick + 0.004
            v = bm.verts.new((r * math.cos(a), r * math.sin(a), h))
            row.append(v)
        grid.append(row)

    for j in range(6):
        for k in range(12):
            bm.faces.new((grid[j][k], grid[j + 1][k], grid[j + 1][k + 1], grid[j][k + 1]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(color)
    for poly in obj.data.polygons:
        poly.use_smooth = True

# ============================================================
# Label pattern: raised dots between stripes
# ============================================================
for i in range(n_stripes):
    ang = (i + 0.5) * (2 * math.pi / n_stripes)
    color = colors[(i + 2) % len(colors)]

    hc = (lh0 + lh1) / 2
    rc = radius_at(hc, p) + lthick + 0.006

    mesh = bpy.data.meshes.new(f"Dot_{i}")
    obj = bpy.data.objects.new(f"Dot_{i}", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    n_seg = 16
    dr = 0.05
    dd = 0.008

    ox, oy = math.cos(ang), math.sin(ang)
    tx, ty = -math.sin(ang), math.cos(ang)
    cx, cy = rc * ox, rc * oy

    front = []
    for j in range(n_seg):
        a = j * (2 * math.pi / n_seg)
        lx = dr * math.cos(a)
        ly = dr * math.sin(a)
        wx = cx + lx * tx + dd * ox
        wy = cy + lx * ty + dd * oy
        wz = hc + ly
        front.append(bm.verts.new((wx, wy, wz)))

    cf = bm.verts.new((cx + dd * ox, cy + dd * oy, hc))
    for j in range(n_seg):
        j2 = (j + 1) % n_seg
        bm.faces.new((front[j], front[j2], cf))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(color)
    for poly in obj.data.polygons:
        poly.use_smooth = True

# ============================================================
# Label pattern: gold border rings (top & bottom)
# ============================================================
for hb in [lh0 + 0.04, lh1 - 0.04]:
    rb = radius_at(hb, p) + lthick + 0.005

    mesh = bpy.data.meshes.new(f"Ring_{hb:.2f}")
    obj = bpy.data.objects.new(f"Ring_{hb:.2f}", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    mj, mn = 72, 8
    mr = 0.012

    grid = []
    for j in range(mj):
        a = j * (2 * math.pi / mj)
        row = []
        for k in range(mn):
            ma = k * (2 * math.pi / mn)
            rr = rb + mr * math.cos(ma)
            zo = mr * math.sin(ma)
            row.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), hb + zo)))
        grid.append(row)

    for j in range(mj):
        j2 = (j + 1) % mj
        for k in range(mn):
            k2 = (k + 1) % mn
            bm.faces.new((grid[j][k], grid[j2][k], grid[j2][k2], grid[j][k2]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(mat_gold)
    for poly in obj.data.polygons:
        poly.use_smooth = True

# ============================================================
# Central emblem on front of label (raised gold medallion)
# ============================================================
eh = (lh0 + lh1) / 2
er = radius_at(eh, p) + lthick + 0.010

mesh = bpy.data.meshes.new("Emblem")
eobj = bpy.data.objects.new("Emblem", mesh)
bpy.context.collection.objects.link(eobj)
bm = bmesh.new()

n_e = 32
es = 0.11
ed = 0.012
ang = 0.0

ox, oy = math.cos(ang), math.sin(ang)
tx, ty = -math.sin(ang), math.cos(ang)
cx, cy = er * ox, er * oy

ring = []
for j in range(n_e):
    a = j * (2 * math.pi / n_e)
    lx = es * math.copysign(abs(math.cos(a)) ** 0.6, math.cos(a))
    ly = es * 0.65 * math.copysign(abs(math.sin(a)) ** 0.6, math.sin(a))
    wx = cx + lx * tx + ed * ox
    wy = cy + lx * ty + ed * oy
    wz = eh + ly
    ring.append(bm.verts.new((wx, wy, wz)))

ce = bm.verts.new((cx + ed * ox, cy + ed * oy, eh))
for j in range(n_e):
    j2 = (j + 1) % n_e
    bm.faces.new((ring[j], ring[j2], ce))

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh)
bm.free()
eobj.data.materials.append(mat_gold)
for poly in eobj.data.polygons:
    poly.use_smooth = True

# ============================================================
# Cap grip ridges (vertical raised lines on cap sides)
# ============================================================
n_ridges = 32
for i in range(n_ridges):
    ang = i * (2 * math.pi / n_ridges)

    mesh = bpy.data.meshes.new(f"CapRidge_{i}")
    obj = bpy.data.objects.new(f"CapRidge_{i}", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    ridge_h0 = cap_h0 + 0.06
    ridge_h1 = cap_h1 - 0.02
    ridge_w = 0.012
    ridge_d = 0.005
    n_h = 5
    n_a = 3

    grid = []
    for j in range(n_a):
        a_off = (j - 1) * ridge_w
        a = ang + a_off
        row = []
        for k in range(n_h):
            t = k / (n_h - 1)
            r_cap = cap_r0 * (1 - t) + cap_r1 * t
            ridge_profile = ridge_d * (1 - abs(a_off) / ridge_w)
            r = r_cap + ridge_profile
            h = ridge_h0 + t * (ridge_h1 - ridge_h0)
            v = bm.verts.new((r * math.cos(a), r * math.sin(a), h))
            row.append(v)
        grid.append(row)

    for j in range(n_a - 1):
        for k in range(n_h - 1):
            bm.faces.new((grid[j][k], grid[j + 1][k], grid[j + 1][k + 1], grid[j][k + 1]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(mat_cap)
    for poly in obj.data.polygons:
        poly.use_smooth = True

# ============================================================
# Small decorative star elements on label (4 around emblem)
# ============================================================
star_positions = [
    (0.0, 0.18),
    (0.0, -0.18),
    (0.16, 0.0),
    (-0.16, 0.0),
]

for si, (sx, sy) in enumerate(star_positions):
    mesh = bpy.data.meshes.new(f"Star_{si}")
    obj = bpy.data.objects.new(f"Star_{si}", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    n_star = 10
    star_r_outer = 0.035
    star_r_inner = 0.014
    star_depth = 0.010

    cx_s = er * math.cos(0) + sx * (-math.sin(0))
    cy_s = er * math.sin(0) + sx * math.cos(0)
    cz_s = eh + sy

    verts_star = []
    for j in range(n_star):
        a = j * (2 * math.pi / n_star) - math.pi / 2
        r_s = star_r_outer if j % 2 == 0 else star_r_inner
        lx = r_s * math.cos(a)
        ly = r_s * math.sin(a)
        wx = cx_s + lx * (-math.sin(0)) + star_depth * math.cos(0)
        wy = cy_s + lx * math.cos(0) + star_depth * math.sin(0)
        wz = cz_s + ly
        verts_star.append(bm.verts.new((wx, wy, wz)))

    center_s = bm.verts.new((cx_s + star_depth * math.cos(0), cy_s + star_depth * math.sin(0), cz_s))
    for j in range(n_star):
        j2 = (j + 1) % n_star
        bm.faces.new((verts_star[j], verts_star[j2], center_s))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(mat_red if si % 2 == 0 else mat_blue)
    for poly in obj.data.polygons:
        poly.use_smooth = True

print("Beverage bottle model created successfully.")