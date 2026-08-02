import bpy
import bmesh
import math
import random
from mathutils import Vector

random.seed(42)

# ========== CLEAR SCENE ==========
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for cn in ['meshes', 'materials', 'particles', 'curves', 'lights', 'cameras', 'textures', 'images']:
    c = getattr(bpy.data, cn, None)
    if c:
        for b in list(c):
            c.remove(b)

# ========== HELPERS ==========

def add_ring(bm, x, cy, cz, ry, rz, n_seg, flatten=0.0):
    verts = []
    for j in range(n_seg):
        a = 2.0 * math.pi * j / n_seg
        py = cy + ry * math.cos(a)
        sa = math.sin(a)
        if sa < 0 and flatten > 0:
            pz = cz + rz * sa * (1.0 - flatten)
        else:
            pz = cz + rz * sa
        verts.append(bm.verts.new((x, py, pz)))
    return verts

def connect_rings(bm, r1, r2, n):
    for j in range(n):
        j2 = (j + 1) % n
        try:
            bm.faces.new([r1[j], r1[j2], r2[j2], r2[j]])
        except ValueError:
            pass

def cap_ring(bm, ring, reverse=False):
    r = ring[::-1] if reverse else ring
    n = len(r)
    cx = sum(v.co.x for v in r) / n
    cy = sum(v.co.y for v in r) / n
    cz = sum(v.co.z for v in r) / n
    cv = bm.verts.new((cx, cy, cz))
    for j in range(n):
        j2 = (j + 1) % n
        try:
            bm.faces.new([r[j], r[j2], cv])
        except ValueError:
            pass

def add_tube(bm, points, radii, n_seg=12):
    rings = []
    n = len(points)
    for i in range(n):
        p = points[i]
        r = radii[i]
        if n == 1:
            d = Vector((1, 0, 0))
        elif i == 0:
            d = points[1] - points[0]
            if d.length < 1e-6:
                d = Vector((1, 0, 0))
            d = d.normalized()
        elif i == n - 1:
            d = points[-1] - points[-2]
            if d.length < 1e-6:
                d = Vector((1, 0, 0))
            d = d.normalized()
        else:
            d = points[i + 1] - points[i - 1]
            if d.length < 1e-6:
                d = Vector((1, 0, 0))
            d = d.normalized()

        up = Vector((0, 0, 1))
        if abs(d.dot(up)) > 0.95:
            up = Vector((0, 1, 0))
        right = d.cross(up).normalized()
        up = right.cross(d).normalized()

        ring = []
        for j in range(n_seg):
            a = 2.0 * math.pi * j / n_seg
            offset = right * (r * math.cos(a)) + up * (r * math.sin(a))
            ring.append(bm.verts.new(p + offset))
        rings.append(ring)

    for i in range(len(rings) - 1):
        connect_rings(bm, rings[i], rings[i + 1], n_seg)

    return rings

# ========== BUILD TIGER ==========

bm = bmesh.new()

# --- Body ---
body_profile = [
    (-1.50, 0.10, 0.12, 0.78),
    (-1.35, 0.16, 0.20, 0.76),
    (-1.15, 0.23, 0.28, 0.74),
    (-0.95, 0.28, 0.35, 0.73),
    (-0.70, 0.32, 0.41, 0.73),
    (-0.45, 0.34, 0.44, 0.74),
    (-0.20, 0.35, 0.46, 0.75),
    ( 0.05, 0.35, 0.47, 0.77),
    ( 0.30, 0.34, 0.46, 0.79),
    ( 0.55, 0.32, 0.44, 0.82),
    ( 0.75, 0.27, 0.38, 0.85),
    ( 0.92, 0.22, 0.32, 0.89),
]

NS = 24
body_rings = []
for x, ry, rz, cz in body_profile:
    body_rings.append(add_ring(bm, x, 0, cz, ry, rz, NS, flatten=0.20))

for i in range(len(body_rings) - 1):
    connect_rings(bm, body_rings[i], body_rings[i + 1], NS)

cap_ring(bm, body_rings[0], reverse=True)

# --- Head ---
head_profile = [
    (0.92, 0.22, 0.30, 0.89),
    (1.02, 0.24, 0.32, 0.92),
    (1.12, 0.26, 0.34, 0.95),
    (1.22, 0.26, 0.34, 0.97),
    (1.30, 0.24, 0.31, 0.98),
    (1.38, 0.20, 0.27, 0.98),
    (1.46, 0.16, 0.22, 0.96),
    (1.54, 0.12, 0.18, 0.94),
    (1.60, 0.08, 0.14, 0.92),
    (1.64, 0.04, 0.08, 0.90),
]

NSH = 20
head_rings = []
for x, ry, rz, cz in head_profile:
    head_rings.append(add_ring(bm, x, 0, cz, ry, rz, NSH, flatten=0.12))

for i in range(len(head_rings) - 1):
    connect_rings(bm, head_rings[i], head_rings[i + 1], NSH)

cap_ring(bm, head_rings[-1], reverse=False)

# --- Ears ---
for side in [1, -1]:
    ear_pts = [
        Vector((1.06, 0.15 * side, 1.20)),
        Vector((1.09, 0.17 * side, 1.26)),
        Vector((1.11, 0.16 * side, 1.30)),
        Vector((1.09, 0.14 * side, 1.31)),
    ]
    ear_r = [0.055, 0.035, 0.018, 0.0]
    add_tube(bm, ear_pts, ear_r, 10)

# --- Eyes ---
for side in [1, -1]:
    eye_pts = [
        Vector((1.25, 0.11 * side, 1.005)),
        Vector((1.28, 0.125 * side, 1.012)),
    ]
    eye_r = [0.020, 0.010]
    add_tube(bm, eye_pts, eye_r, 8)

# --- Nose ---
nose_pts = [
    Vector((1.60, 0, 0.892)),
    Vector((1.65, 0, 0.90)),
]
nose_r = [0.028, 0.018]
add_tube(bm, nose_pts, nose_r, 8)

# --- Front legs (slightly bent, crouching) ---
for side in [1, -1]:
    pts = [
        Vector((0.46, 0.24 * side, 0.76)),
        Vector((0.50, 0.25 * side, 0.52)),
        Vector((0.54, 0.26 * side, 0.28)),
        Vector((0.56, 0.26 * side, 0.10)),
    ]
    radii = [0.13, 0.10, 0.08, 0.07]
    add_tube(bm, pts, radii, 14)

# --- Back legs (folded in crouch) ---
for side in [1, -1]:
    pts = [
        Vector((-0.90, 0.24 * side, 0.72)),
        Vector((-0.70, 0.25 * side, 0.46)),
        Vector((-0.92, 0.26 * side, 0.30)),
        Vector((-0.94, 0.26 * side, 0.10)),
    ]
    radii = [0.14, 0.11, 0.08, 0.07]
    add_tube(bm, pts, radii, 14)

# --- Paws with toes and claws ---
def build_paw(bm, cx, cy, cz):
    pad_pts = [
        Vector((cx - 0.04, cy, cz + 0.035)),
        Vector((cx, cy, cz + 0.025)),
        Vector((cx + 0.04, cy, cz + 0.015)),
    ]
    pad_r = [0.065, 0.060, 0.045]
    add_tube(bm, pad_pts, pad_r, 14)

    for i in range(4):
        offset = (i - 1.5) * 0.028
        tx = cx + 0.01 + abs(offset) * 0.15
        ty = cy + offset * 0.7
        tz = cz
        toe_pts = [
            Vector((tx - 0.015, ty, tz + 0.028)),
            Vector((tx + 0.005, ty, tz + 0.015)),
            Vector((tx + 0.025, ty, tz + 0.005)),
        ]
        toe_r = [0.024, 0.020, 0.012]
        add_tube(bm, toe_pts, toe_r, 8)

        claw_pts = [
            Vector((tx + 0.025, ty, tz + 0.005)),
            Vector((tx + 0.038, ty, tz - 0.005)),
            Vector((tx + 0.046, ty, tz - 0.020)),
        ]
        claw_r = [0.008, 0.005, 0.0]
        add_tube(bm, claw_pts, claw_r, 6)

build_paw(bm, 0.56, 0.26, 0.05)
build_paw(bm, 0.56, -0.26, 0.05)
build_paw(bm, -0.94, 0.26, 0.05)
build_paw(bm, -0.94, -0.26, 0.05)

# --- Tail ---
tail_pts = [
    Vector((-1.50, 0, 0.78)),
    Vector((-1.66, 0.02, 0.70)),
    Vector((-1.83, 0.04, 0.66)),
    Vector((-1.99, 0.06, 0.66)),
    Vector((-2.11, 0.08, 0.70)),
    Vector((-2.19, 0.09, 0.76)),
]
tail_r = [0.09, 0.07, 0.055, 0.04, 0.025, 0.012]
add_tube(bm, tail_pts, tail_r, 16)

# Recalculate normals
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

# ========== CREATE MESH ==========
mesh = bpy.data.meshes.new("TigerMesh")
bm.to_mesh(mesh)
bm.free()
obj = bpy.data.objects.new("Tiger", mesh)
bpy.context.scene.collection.objects.link(obj)

# ========== COLOR ATTRIBUTES ==========
color_attr = mesh.color_attributes.new(name="Col", type='BYTE_COLOR', domain='POINT')

ORANGE = (0.82, 0.33, 0.10, 1.0)
BLACK = (0.04, 0.04, 0.04, 1.0)
CREAM = (0.93, 0.86, 0.72, 1.0)
GRAY = (0.55, 0.55, 0.52, 1.0)
DARK = (0.10, 0.07, 0.04, 1.0)

# Generate stripe positions deterministically
stripe_centers = []
sx = -1.22
while sx < 0.78:
    sw = 0.028 + random.uniform(-0.005, 0.012)
    stripe_centers.append((sx, sw))
    sx += 0.082 + random.uniform(-0.012, 0.020)

tail_stripes = [-1.55, -1.70, -1.85, -2.00, -2.10]

def get_color(pos):
    x, y, z = pos.x, pos.y, pos.z

    # Paws and claws
    if z < 0.025:
        return DARK
    if z < 0.08 and abs(y) > 0.18:
        return DARK

    # Head region
    if x > 0.92:
        # Nose
        if x > 1.59:
            return DARK
        # Muzzle (front, lower)
        if x > 1.38 and z < 0.97:
            return CREAM
        # Eye area — white and gray markings
        if 1.20 < x < 1.32 and z > 0.98:
            if abs(y) < 0.05:
                return CREAM
            elif abs(y) < 0.14:
                return GRAY
        # Cheeks — cream
        if 1.02 < x < 1.22 and z < 0.91:
            return CREAM
        # Ear backs — white spots
        if z > 1.16 and abs(y) > 0.10:
            return CREAM
        # Stripes on head
        for cx, cw in stripe_centers:
            if abs(x - cx) < cw:
                return BLACK
        return ORANGE

    # Tail region — rings
    if x < -1.40:
        for cx in tail_stripes:
            if abs(x - cx) < 0.022:
                return BLACK
        return ORANGE

    # Body region
    cz_est = 0.75
    rz_est = 0.40
    for px, pry, prz, pcz in body_profile:
        if abs(px - x) < 0.15:
            cz_est = pcz
            rz_est = prz
            break

    rel_z = (z - cz_est) / max(rz_est, 0.01)

    # Belly — creamy white
    if rel_z < -0.25:
        return CREAM

    # Legs — orange with stripes
    if abs(y) > 0.20 and z < 0.65:
        for cx, cw in stripe_centers:
            if abs(x - cx) < cw * 1.2:
                return BLACK
        return ORANGE

    # Body stripes — upper body and sides
    angle = math.atan2(z - cz_est, y) if (abs(y) > 0.001 or abs(z - cz_est) > 0.001) else 0.0
    if angle > -0.4:
        for cx, cw in stripe_centers:
            variation = 0.012 * math.sin(angle * 2.5 + cx * 8.0)
            if abs(x - cx + variation) < cw:
                return BLACK

    return ORANGE

for i, v in enumerate(mesh.vertices):
    color_attr.data[i].color = get_color(v.co)

# ========== MATERIAL ==========
mat = bpy.data.materials.new("TigerFur")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
nodes = nt.nodes
links = nt.links

out_node = nodes.new('ShaderNodeOutputMaterial')
out_node.location = (400, 0)

bsdf = nodes.new('ShaderNodeBsdfPrincipled')
bsdf.location = (200, 0)
bsdf.inputs['Roughness'].default_value = 0.85

vc_node = nodes.new('ShaderNodeVertexColor')
vc_node.layer_name = "Col"
vc_node.location = (-200, 0)

links.new(vc_node.outputs['Color'], bsdf.inputs['Base Color'])
links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

mesh.materials.append(mat)

# ========== MODIFIERS ==========
sub = obj.modifiers.new("Subsurf", type='SUBSURF')
sub.levels = 2
sub.render_levels = 3

for poly in mesh.polygons:
    poly.use_smooth = True

# ========== PARTICLE HAIR SYSTEM ==========
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
for o in bpy.context.scene.objects:
    if o != obj:
        o.select_set(False)

try:
    bpy.ops.object.particle_system_add()
    psys = obj.particle_systems[-1]
    pset = psys.settings
except Exception:
    pset = bpy.data.particles.new("TigerFur")
    try:
        psys = obj.particle_systems.new("Fur")
        psys.settings = pset
    except Exception:
        psys = None
        pset = None

if pset is not None:
    pset.type = 'HAIR'
    pset.count = 30000
    pset.hair_length = 0.07
    pset.hair_step = 7

    # Children for density
    pset.child_type = 'INTERPOLATED'
    pset.rendered_child_count = 20

    # Set properties with safe fallbacks
    safe_props = [
        ('use_advanced_hair', True),
        ('child_nbr', 4),
        ('child_length', 1.0),
        ('child_length_threshold', 0.0),
        ('root_radius', 0.0004),
        ('tip_radius', 0.0001),
        ('radius_scale', 1.0),
        ('roughness_1', 0.05),
        ('roughness_1_end', 0.30),
        ('roughness_2', 0.04),
        ('roughness_2_threshold', 0.3),
        ('roughness_1_size', 1.0),
        ('use_rotations', True),
        ('rotation_factor_random', 0.3),
        ('phase_factor_random', 0.4),
        ('render_type', 'PATH'),
    ]
    for prop, val in safe_props:
        try:
            setattr(pset, prop, val)
        except Exception:
            pass

obj.select_set(False)
bpy.context.view_layer.update()