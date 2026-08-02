import bpy
import math
import random
from mathutils import Vector

random.seed(41)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def make_material(name, color, roughness=0.85):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat

charcoal = make_material("Charcoal plumage", (0.045, 0.052, 0.060), 0.93)
dark_gray = make_material("Dark gray plumage", (0.11, 0.125, 0.14), 0.94)
slate = make_material("Slate gray plumage", (0.25, 0.28, 0.31), 0.95)
mid_gray = make_material("Mid gray plumage", (0.44, 0.47, 0.49), 0.95)
pale_gray = make_material("Pale gray plumage", (0.73, 0.75, 0.75), 0.96)
white = make_material("White feather highlights", (0.94, 0.95, 0.93), 0.92)
black = make_material("Glossy black eyes", (0.003, 0.004, 0.005), 0.12)
eye_white = make_material("Eye highlights", (1.0, 1.0, 1.0), 0.08)
salmon = make_material("Salmon pink beak", (0.88, 0.40, 0.31), 0.72)
beak_dark = make_material("Beak details", (0.31, 0.075, 0.052), 0.78)
orange = make_material("Orange red feet", (0.88, 0.235, 0.065), 0.78)
claw_mat = make_material("Dark claw tips", (0.27, 0.065, 0.025), 0.86)

def smooth(obj):
    if obj.type == 'MESH':
        for poly in obj.data.polygons:
            poly.use_smooth = True

def ellipsoid(name, location, scale, material, segments=36, rings=24, rotation=(0, 0, 0)):
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
    smooth(obj)
    return obj

def tube(name, points, radius, material, bevel_resolution=3):
    curve = bpy.data.curves.new(name + " Curve", 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = bevel_resolution
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(points) - 1)
    for bp, point in zip(spline.bezier_points, points):
        bp.co = point
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

def cone_between(name, start, end, radius1, radius2, material, vertices=12):
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius1,
        radius2=radius2,
        depth=direction.length,
        location=(start + end) * 0.5
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    obj.data.materials.append(material)
    smooth(obj)
    return obj

body = ellipsoid(
    "Plump tapered body",
    (0.0, 0.02, 2.02),
    (0.87, 0.69, 1.18),
    dark_gray,
    48,
    32
)

belly = ellipsoid(
    "Pale rounded breast and belly",
    (0.0, -0.565, 1.99),
    (0.65, 0.255, 0.94),
    pale_gray,
    44,
    30
)

lower_belly = ellipsoid(
    "Lower gray belly transition",
    (0.0, -0.40, 1.39),
    (0.59, 0.27, 0.44),
    mid_gray,
    38,
    24
)

neck = ellipsoid(
    "Soft neck transition",
    (0.0, -0.19, 2.91),
    (0.62, 0.52, 0.54),
    pale_gray,
    42,
    28
)

head = ellipsoid(
    "Rounded feathered head",
    (0.0, -0.22, 3.39),
    (0.64, 0.58, 0.60),
    pale_gray,
    48,
    32
)

for side in (-1, 1):
    ellipsoid(
        "Attached tapered folded wing",
        (side * 0.72, 0.055, 2.10),
        (0.235, 0.53, 0.94),
        charcoal,
        38,
        26,
        rotation=(math.radians(-4), side * math.radians(7), 0)
    )

for i in range(5):
    x = (i - 2) * 0.115
    ellipsoid(
        "Tucked tail feather",
        (x, 0.29 + abs(i - 2) * 0.014, 1.09),
        (0.095, 0.12, 0.47 - abs(i - 2) * 0.025),
        charcoal if i % 2 else dark_gray,
        24,
        16,
        rotation=(math.radians(8), -x * 0.15, 0)
    )

feather_materials = [charcoal, dark_gray, slate, mid_gray, pale_gray, white]
feather_vertices = []
feather_faces = []
feather_material_indices = []

def add_feather(center, normal, downward, width, length, material_index, lift=0.012):
    center = Vector(center)
    normal = Vector(normal).normalized()
    down = Vector(downward)
    down -= normal * down.dot(normal)
    if down.length < 0.001:
        down = Vector((0, 0, -1))
        down -= normal * down.dot(normal)
    down.normalize()
    across = down.cross(normal).normalized()

    outline = [
        (-0.38, -0.44),
        (-0.55, -0.18),
        (-0.48, 0.12),
        (-0.25, 0.34),
        (0.0, 0.56),
        (0.25, 0.34),
        (0.48, 0.12),
        (0.55, -0.18),
        (0.38, -0.44),
        (0.0, -0.55)
    ]

    base = len(feather_vertices)
    for x, y in outline:
        arch = lift * (1.0 - min(1.0, abs(x) * 1.7))
        point = center + across * (x * width) + down * (y * length) + normal * arch
        feather_vertices.append(tuple(point))

    feather_faces.append(tuple(base + i for i in range(len(outline))))
    feather_material_indices.append(material_index)

body_center = Vector((0.0, 0.02, 2.02))
body_axes = Vector((0.87, 0.69, 1.18))

for ring in range(13):
    theta = 0.34 + ring * (2.35 / 12)
    z_fraction = math.cos(theta)
    count = max(12, int(21 * math.sin(theta)))
    for j in range(count):
        phi = 2 * math.pi * (j + 0.45 * (ring % 2)) / count
        local = Vector((
            body_axes.x * math.sin(theta) * math.cos(phi),
            body_axes.y * math.sin(theta) * math.sin(phi),
            body_axes.z * math.cos(theta)
        ))
        normal = Vector((
            local.x / (body_axes.x * body_axes.x),
            local.y / (body_axes.y * body_axes.y),
            local.z / (body_axes.z * body_axes.z)
        )).normalized()

        frontness = -normal.y
        if frontness > 0.43:
            continue
        if abs(normal.x) > 0.66 and -0.25 < normal.y < 0.48:
            continue

        center = body_center + local + normal * 0.018
        if normal.y > 0.30:
            mat_index = random.choices([0, 1, 2], [0.38, 0.48, 0.14])[0]
        else:
            mat_index = random.choices([1, 2, 3], [0.45, 0.38, 0.17])[0]

        length = random.uniform(0.14, 0.18)
        add_feather(
            center,
            normal,
            (0, 0, -1),
            length * random.uniform(0.62, 0.73),
            length,
            mat_index,
            0.009
        )

head_center = Vector((0.0, -0.22, 3.39))
head_axes = Vector((0.64, 0.58, 0.60))

for ring in range(8):
    theta = 0.28 + ring * (2.45 / 7)
    count = max(10, int(17 * math.sin(theta)))
    for j in range(count):
        phi = 2 * math.pi * (j + 0.5 * (ring % 2)) / count
        local = Vector((
            head_axes.x * math.sin(theta) * math.cos(phi),
            head_axes.y * math.sin(theta) * math.sin(phi),
            head_axes.z * math.cos(theta)
        ))
        normal = Vector((
            local.x / (head_axes.x * head_axes.x),
            local.y / (head_axes.y * head_axes.y),
            local.z / (head_axes.z * head_axes.z)
        )).normalized()

        if local.y < -0.45 and abs(local.x) < 0.27:
            continue

        center = head_center + local + normal * 0.014
        if local.z > 0.16 or normal.y > 0.42:
            mat_index = random.choices([3, 2, 4], [0.52, 0.20, 0.28])[0]
        else:
            mat_index = random.choices([4, 3, 5], [0.78, 0.18, 0.04])[0]

        length = random.uniform(0.085, 0.115)
        add_feather(center, normal, (0, 0, -1), length * 0.66, length, mat_index, 0.006)

for side in (-1, 1):
    outward = Vector((side, 0.03, 0.0)).normalized()
    for row in range(7):
        z = 2.82 - row * 0.245
        count = 4 + min(3, row)
        for col in range(count):
            fraction = (col + 0.5) / count
            y = -0.30 + fraction * 0.58
            x = side * (0.947 + 0.012 * math.sin(fraction * math.pi))
            center = Vector((x, y, z - 0.04 * abs(fraction - 0.5)))
            if random.random() < 0.10:
                mat_index = 5
            else:
                mat_index = random.choices([0, 1, 2], [0.50, 0.38, 0.12])[0]
            add_feather(
                center,
                outward,
                (0, 0.04, -1),
                random.uniform(0.135, 0.17),
                random.uniform(0.24, 0.31),
                mat_index,
                0.015
            )

    for col in range(6):
        fraction = col / 5
        center = Vector((
            side * 0.925,
            -0.26 + fraction * 0.49,
            2.98 - 0.06 * abs(fraction - 0.5)
        ))
        add_feather(
            center,
            Vector((side, -0.08, 0.16)),
            (0, 0, -1),
            0.125,
            0.20,
            random.choice([2, 3, 3, 4]),
            0.012
        )

feather_mesh = bpy.data.meshes.new("Layered pointed feather mesh")
feather_mesh.from_pydata(feather_vertices, [], feather_faces)
feather_mesh.update()
for mat in feather_materials:
    feather_mesh.materials.append(mat)

for poly, mat_index in zip(feather_mesh.polygons, feather_material_indices):
    poly.material_index = mat_index
    poly.use_smooth = True

feather_object = bpy.data.objects.new("Dense layered plumage", feather_mesh)
bpy.context.collection.objects.link(feather_object)

def create_beak():
    sections = [
        ((0.0, -0.73, 3.42), 0.205, 0.125),
        ((0.0, -0.88, 3.41), 0.145, 0.090),
        ((0.0, -1.02, 3.37), 0.072, 0.052),
        ((0.0, -1.095, 3.31), 0.012, 0.012)
    ]
    sides = 14
    verts = []
    faces = []

    for center, rx, rz in sections:
        for i in range(sides):
            angle = 2 * math.pi * i / sides
            verts.append((
                center[0] + rx * math.cos(angle),
                center[1],
                center[2] + rz * math.sin(angle)
            ))

    for section in range(len(sections) - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((
                section * sides + i,
                (section + 1) * sides + i,
                (section + 1) * sides + j,
                section * sides + j
            ))

    faces.append(tuple(reversed(range(sides))))
    last = (len(sections) - 1) * sides
    faces.append(tuple(last + i for i in range(sides)))

    mesh = bpy.data.meshes.new("Curved beak mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(salmon)
    mesh.update()

    obj = bpy.data.objects.new("Short curved salmon beak", mesh)
    bpy.context.collection.objects.link(obj)
    smooth(obj)

create_beak()

tube(
    "Beak mouth seam",
    [(-0.18, -0.78, 3.385), (0.0, -0.91, 3.375), (0.055, -1.04, 3.34)],
    0.007,
    beak_dark,
    2
)

for side in (-1, 1):
    ellipsoid(
        "Black eye",
        (side * 0.485, -0.575, 3.54),
        (0.075, 0.042, 0.078),
        black,
        26,
        16
    )
    ellipsoid(
        "Eye catchlight",
        (side * 0.505, -0.613, 3.568),
        (0.018, 0.009, 0.018),
        eye_white,
        12,
        8
    )
    ellipsoid(
        "Beak nostril",
        (side * 0.083, -0.805, 3.475),
        (0.021, 0.009, 0.012),
        beak_dark,
        14,
        8
    )

for side in (-1, 1):
    x = side * 0.29
    tube(
        "Orange red leg",
        [(x, -0.01, 1.03), (x, -0.025, 0.66), (x, -0.065, 0.35)],
        0.061,
        orange
    )

    ellipsoid(
        "Foot joint",
        (x, -0.07, 0.30),
        (0.092, 0.082, 0.068),
        orange,
        20,
        12
    )

    toe_paths = [
        [(x, -0.08, 0.30), (x, -0.35, 0.17), (x, -0.61, 0.10)],
        [(x, -0.07, 0.29), (x + side * 0.17, -0.30, 0.16), (x + side * 0.31, -0.49, 0.095)],
        [(x, -0.07, 0.29), (x - side * 0.16, -0.28, 0.16), (x - side * 0.29, -0.46, 0.095)],
        [(x, -0.02, 0.29), (x - side * 0.025, 0.17, 0.17), (x - side * 0.055, 0.33, 0.11)]
    ]

    for index, path in enumerate(toe_paths):
        tube(
            "Orange clawed toe",
            path,
            0.034 if index == 0 else 0.031,
            orange,
            2
        )
        tip = Vector(path[-1])
        previous = Vector(path[-2])
        direction = (tip - previous).normalized()
        if index == 3:
            claw_end = tip + Vector((-side * 0.01, 0.09, -0.055))
        else:
            claw_end = tip + direction * 0.085 + Vector((0, 0, -0.04))
        cone_between(
            "Tapered dark claw",
            tip,
            claw_end,
            0.027,
            0.003,
            claw_mat
        )

    for ring_index in range(4):
        z = 0.45 + ring_index * 0.105
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.061,
            minor_radius=0.0055,
            major_segments=16,
            minor_segments=6,
            location=(x, -0.035, z)
        )
        ring = bpy.context.object
        ring.name = "Leg scale ring"
        ring.data.materials.append(claw_mat)
        smooth(ring)

for obj in list(bpy.context.scene.objects):
    if obj.type == 'CURVE':
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.convert(target='MESH')
        obj.select_set(False)

for obj in bpy.context.scene.objects:
    obj.select_set(False)