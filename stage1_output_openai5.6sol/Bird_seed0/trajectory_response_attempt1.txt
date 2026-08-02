import bpy
import math
import random
from mathutils import Vector, Matrix

random.seed(12)

# Clear the scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    for datablock in list(datablocks):
        if datablock.users == 0:
            datablocks.remove(datablock)

# Materials.
def make_material(name, color, roughness=0.75, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat

mat_charcoal = make_material("Charcoal plumage", (0.075, 0.082, 0.09), 0.92)
mat_dark_gray = make_material("Dark gray plumage", (0.14, 0.15, 0.16), 0.95)
mat_mid_gray = make_material("Mid gray plumage", (0.32, 0.34, 0.35), 0.97)
mat_pale = make_material("Pale gray plumage", (0.68, 0.70, 0.70), 0.98)
mat_light = make_material("Light feather tips", (0.86, 0.87, 0.84), 0.95)
mat_white = make_material("White wing highlights", (0.95, 0.95, 0.91), 0.92)
mat_black = make_material("Eye black", (0.006, 0.007, 0.008), 0.16)
mat_eye_glint = make_material("Eye glints", (0.92, 0.94, 0.95), 0.1)
mat_beak = make_material("Salmon pink beak", (0.82, 0.36, 0.28), 0.7)
mat_beak_dark = make_material("Beak shadow", (0.38, 0.13, 0.11), 0.72)
mat_leg = make_material("Orange red feet", (0.83, 0.20, 0.075), 0.82)
mat_claw = make_material("Claw tips", (0.35, 0.09, 0.035), 0.86)

def smooth_object(obj):
    if obj.type == 'MESH':
        for poly in obj.data.polygons:
            poly.use_smooth = True

def ellipsoid(name, location, scale, material, segments=40, rings=24, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=location,
        rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    smooth_object(obj)
    return obj

# Core rounded silhouette.
body = ellipsoid("Plump rounded body", (0.0, 0.05, 2.18), (0.98, 0.79, 1.33), mat_dark_gray, 48, 32)
chest = ellipsoid("Pale breast", (0.0, -0.625, 2.25), (0.72, 0.24, 1.08), mat_pale, 40, 28)
lower_chest = ellipsoid("Soft lower breast", (0.0, -0.48, 1.55), (0.67, 0.29, 0.56), mat_mid_gray, 36, 24)
head = ellipsoid("Rounded pale head", (0.0, -0.08, 3.52), (0.76, 0.67, 0.70), mat_pale, 48, 32)
crown = ellipsoid("Gray crown", (0.0, 0.02, 3.86), (0.66, 0.56, 0.34), mat_mid_gray, 40, 24)

# Folded wing masses.
left_wing = ellipsoid(
    "Left folded wing", (-0.84, 0.10, 2.25), (0.245, 0.58, 1.08),
    mat_charcoal, 40, 28, rotation=(0.03, -0.13, -0.05)
)
right_wing = ellipsoid(
    "Right folded wing", (0.84, 0.10, 2.25), (0.245, 0.58, 1.08),
    mat_charcoal, 40, 28, rotation=(0.03, 0.13, 0.05)
)

# Feather geometry accumulator. Each feather is a small domed, tapered solid.
feather_materials = [mat_charcoal, mat_dark_gray, mat_mid_gray, mat_pale, mat_light, mat_white]
feather_verts = []
feather_faces = []
feather_mats = []

outline = [
    (0.0, -0.56),
    (-0.15, -0.43),
    (-0.27, -0.12),
    (-0.29, 0.17),
    (-0.20, 0.43),
    (0.0, 0.55),
    (0.20, 0.43),
    (0.29, 0.17),
    (0.27, -0.12),
    (0.15, -0.43)
]

def add_feather(position, normal, up_direction, width, length, thickness, material_index, twist=0.0):
    normal = Vector(normal).normalized()
    up = Vector(up_direction)
    up -= normal * up.dot(normal)
    if up.length < 0.001:
        up = Vector((0.0, 1.0, 0.0))
        up -= normal * up.dot(normal)
    up.normalize()
    side = up.cross(normal).normalized()
    if twist:
        c = math.cos(twist)
        s = math.sin(twist)
        side, up = side * c + up * s, up * c - side * s

    base = len(feather_verts)
    # Domed upper center and upper outline.
    center_top = Vector(position) + normal * thickness
    feather_verts.append(tuple(center_top))
    for x, y in outline:
        dome = thickness * (0.18 + 0.38 * max(0.0, 1.0 - abs(x) / 0.30))
        p = Vector(position) + side * (x * width) + up * (y * length) + normal * dome
        feather_verts.append(tuple(p))
    # Flat lower center and outline, giving the cards actual thickness.
    center_bottom = Vector(position) - normal * thickness * 0.30
    feather_verts.append(tuple(center_bottom))
    for x, y in outline:
        p = Vector(position) + side * (x * width) + up * (y * length) - normal * thickness * 0.30
        feather_verts.append(tuple(p))

    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        feather_faces.append((base, base + 1 + i, base + 1 + j))
        feather_mats.append(material_index)
        feather_faces.append((base + 1 + n, base + 2 + n + j, base + 2 + n + i))
        feather_mats.append(material_index)
        feather_faces.append((base + 1 + i, base + 2 + n + i, base + 2 + n + j, base + 1 + j))
        feather_mats.append(material_index)

# Dense body feather shell.
body_center = Vector((0.0, 0.05, 2.18))
a, b, c = 0.98, 0.79, 1.33
for ring in range(17):
    theta = 0.23 + ring * (2.65 / 16.0)
    ring_count = max(10, int(18 * math.sin(theta) + 5))
    for j in range(ring_count):
        phi = 2.0 * math.pi * (j + 0.45 * (ring % 2)) / ring_count
        x = a * math.sin(theta) * math.cos(phi)
        y = b * math.sin(theta) * math.sin(phi)
        z = c * math.cos(theta)
        normal = Vector((x / (a * a), y / (b * b), z / (c * c))).normalized()
        pos = body_center + Vector((x, y, z)) + normal * 0.018
        frontness = -normal.y
        if frontness > 0.38:
            mi = random.choices([3, 4, 2], [0.70, 0.18, 0.12])[0]
        elif normal.y > 0.28:
            mi = random.choices([0, 1, 2], [0.46, 0.43, 0.11])[0]
        else:
            mi = random.choices([1, 2, 3], [0.47, 0.35, 0.18])[0]
        length = random.uniform(0.20, 0.27)
        width = random.uniform(0.49, 0.62) * length
        add_feather(pos, normal, (0, 0, 1), width, length, 0.018, mi, random.uniform(-0.12, 0.12))

# Fine head feathers, excluding the very front center where the beak emerges.
head_center = Vector((0.0, -0.08, 3.52))
ha, hb, hc = 0.76, 0.67, 0.70
for ring in range(9):
    theta = 0.24 + ring * (2.45 / 8.0)
    count = max(9, int(15 * math.sin(theta) + 4))
    for j in range(count):
        phi = 2.0 * math.pi * (j + 0.5 * (ring % 2)) / count
        x = ha * math.sin(theta) * math.cos(phi)
        y = hb * math.sin(theta) * math.sin(phi)
        z = hc * math.cos(theta)
        normal = Vector((x / (ha * ha), y / (hb * hb), z / (hc * hc))).normalized()
        pos = head_center + Vector((x, y, z)) + normal * 0.014
        if y < -0.55 and abs(x) < 0.25:
            continue
        if z > 0.27:
            mi = random.choices([2, 3, 4], [0.48, 0.43, 0.09])[0]
        else:
            mi = random.choices([3, 4, 2], [0.72, 0.18, 0.10])[0]
        length = random.uniform(0.13, 0.18)
        add_feather(pos, normal, (0, 0, 1), length * 0.55, length, 0.013, mi, random.uniform(-0.18, 0.18))

# Layered rows of long folded-wing feathers.
for side_sign in (-1, 1):
    outward = Vector((side_sign, 0.0, 0.0))
    for row in range(5):
        y = -0.35 + row * 0.19
        for k in range(8):
            z = 3.02 - k * 0.18 - row * 0.025
            taper = max(0.25, 1.0 - abs(z - 2.34) / 1.15)
            x = side_sign * (0.985 + 0.10 * taper)
            pos = Vector((x, y, z))
            normal = Vector((side_sign, -0.08 + 0.035 * row, 0.03)).normalized()
            highlight = random.random() < (0.11 if row in (0, 1, 2) else 0.06)
            mi = 5 if highlight else random.choices([0, 1, 2], [0.62, 0.31, 0.07])[0]
            length = random.uniform(0.38, 0.49)
            width = random.uniform(0.19, 0.24)
            add_feather(
                pos, normal, (0.0, 0.03, 1.0), width, length, 0.024,
                mi, random.uniform(-0.055, 0.055) * side_sign
            )

# Pale shoulder coverts forming a transition between back and wings.
for side_sign in (-1, 1):
    for i in range(13):
        ang = -0.75 + i * 0.125
        pos = Vector((
            side_sign * (0.77 + 0.12 * math.cos(ang)),
            -0.20 + 0.22 * math.sin(ang),
            2.93 - 0.055 * i
        ))
        normal = Vector((side_sign, -0.25, 0.22)).normalized()
        mi = random.choice([2, 2, 3, 4])
        add_feather(pos, normal, (0, 0, 1), 0.16, 0.28, 0.018, mi, side_sign * 0.08)

mesh = bpy.data.meshes.new("Dense geometric feather texture")
mesh.from_pydata(feather_verts, [], feather_faces)
mesh.update()
feather_obj = bpy.data.objects.new("Layered plumage feathers", mesh)
bpy.context.collection.objects.link(feather_obj)
for mat in feather_materials:
    mesh.materials.append(mat)
for poly, mi in zip(mesh.polygons, feather_mats):
    poly.material_index = mi
    poly.use_smooth = True

# Tail feathers, tucked behind the body.
for i in range(7):
    x = (i - 3) * 0.105
    rot_y = -0.12 * x
    tail = ellipsoid(
        "Tail feather",
        (x, 0.39 + 0.025 * abs(i - 3), 1.10 - 0.035 * abs(i - 3)),
        (0.11, 0.15, 0.67 - 0.035 * abs(i - 3)),
        mat_charcoal if i % 3 else mat_dark_gray,
        24, 16,
        rotation=(0.15, rot_y, 0.0)
    )

# Beak as a gently drooping tapered solid.
def make_beak():
    verts = []
    faces = []
    sections = [
        ((0.0, -0.685, 3.57), 0.285, 0.175),
        ((0.0, -0.93, 3.54), 0.205, 0.135),
        ((0.0, -1.16, 3.47), 0.105, 0.080),
        ((0.0, -1.34, 3.39), 0.012, 0.012)
    ]
    sides = 12
    for center, rx, rz in sections:
        cx, cy, cz = center
        for i in range(sides):
            ang = 2.0 * math.pi * i / sides
            verts.append((cx + rx * math.cos(ang), cy, cz + rz * math.sin(ang)))
    for s in range(len(sections) - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((s * sides + i, (s + 1) * sides + i, (s + 1) * sides + j, s * sides + j))
    faces.append(tuple(reversed(tuple(range(sides)))))
    faces.append(tuple((len(sections) - 1) * sides + i for i in range(sides)))
    me = bpy.data.meshes.new("Curved beak mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(mat_beak)
    me.materials.append(mat_beak_dark)
    for p in me.polygons:
        p.use_smooth = True
        if p.center.z < 3.49:
            p.material_index = 1
    ob = bpy.data.objects.new("Short salmon pink beak", me)
    bpy.context.collection.objects.link(ob)
    return ob

beak = make_beak()

# Beak seam.
def make_curve_object(name, points, radius, material, resolution=2):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = resolution
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    curve.resolution_u = 2
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(points) - 1)
    for bp, co in zip(spline.bezier_points, points):
        bp.co = co
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

make_curve_object(
    "Fine beak mouth seam",
    [(-0.24, -0.76, 3.50), (0.0, -1.03, 3.47), (0.08, -1.21, 3.43)],
    0.009, mat_beak_dark
)

# Eyes on both sides.
for side_sign in (-1, 1):
    eye = ellipsoid(
        "Black eye",
        (side_sign * 0.585, -0.515, 3.70),
        (0.105, 0.055, 0.105),
        mat_black, 28, 18
    )
    glint = ellipsoid(
        "Eye catchlight",
        (side_sign * 0.617, -0.565, 3.742),
        (0.024, 0.012, 0.024),
        mat_eye_glint, 16, 10
    )

# Small nostrils.
for side_sign in (-1, 1):
    ellipsoid(
        "Beak nostril",
        (side_sign * 0.105, -0.835, 3.62),
        (0.030, 0.012, 0.018),
        mat_beak_dark, 16, 10
    )

# Legs.
for side_sign in (-1, 1):
    x = side_sign * 0.35
    make_curve_object(
        "Orange red leg",
        [(x, -0.01, 1.05), (x * 1.04, -0.01, 0.61), (x, -0.05, 0.31)],
        0.085, mat_leg
    )
    # Knuckle.
    ellipsoid("Foot knuckle", (x, -0.07, 0.25), (0.13, 0.12, 0.095), mat_leg, 24, 16)

    toe_paths = [
        [(x, -0.08, 0.23), (x, -0.39, 0.13), (x, -0.67, 0.095)],
        [(x, -0.07, 0.22), (x + side_sign * 0.20, -0.31, 0.12), (x + side_sign * 0.34, -0.52, 0.085)],
        [(x, -0.05, 0.22), (x - side_sign * 0.18, -0.29, 0.12), (x - side_sign * 0.29, -0.47, 0.085)],
        [(x, 0.00, 0.22), (x - side_sign * 0.04, 0.25, 0.13), (x - side_sign * 0.08, 0.42, 0.10)]
    ]
    for toe_index, path in enumerate(toe_paths):
        make_curve_object("Clawed toe", path, 0.047 if toe_index == 0 else 0.043, mat_leg)
        p0 = Vector(path[-1])
        if toe_index == 3:
            p1 = p0 + Vector((-side_sign * 0.015, 0.14, -0.055))
        else:
            direction = (Vector(path[-1]) - Vector(path[-2])).normalized()
            p1 = p0 + direction * 0.14 + Vector((0.0, 0.0, -0.055))

        direction = p1 - p0
        midpoint = (p0 + p1) * 0.5
        bpy.ops.mesh.primitive_cone_add(
            vertices=16,
            radius1=0.045,
            radius2=0.006,
            depth=direction.length,
            location=midpoint
        )
        claw = bpy.context.object
        claw.name = "Tapered claw tip"
        claw.rotation_mode = 'QUATERNION'
        claw.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(direction.normalized())
        claw.data.materials.append(mat_claw)
        smooth_object(claw)

# Add subtle scale rings to the exposed legs.
for side_sign in (-1, 1):
    x = side_sign * 0.35
    for i in range(5):
        z = 0.40 + i * 0.11
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.086,
            minor_radius=0.010,
            major_segments=20,
            minor_segments=8,
            location=(x, -0.04, z)
        )
        ring = bpy.context.object
        ring.name = "Leg scale ring"
        ring.data.materials.append(mat_claw)
        smooth_object(ring)

# Keep the assembly centered and organize naming.
for obj in bpy.context.scene.objects:
    obj.select_set(False)