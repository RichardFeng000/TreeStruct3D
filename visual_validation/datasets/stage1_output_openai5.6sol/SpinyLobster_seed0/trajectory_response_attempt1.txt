import bpy
import math
from mathutils import Vector

# Clear the default scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    pass

# Materials.
def make_material(name, color, roughness=0.3, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.18
    if "Coat Roughness" in bsdf.inputs:
        bsdf.inputs["Coat Roughness"].default_value = 0.22
    return mat

shell_mat = make_material("Warm orange-red shell", (0.72, 0.115, 0.035), 0.25)
shell_light = make_material("Highlighted orange shell", (0.93, 0.22, 0.055), 0.22)
shell_dark = make_material("Dark red joints", (0.32, 0.035, 0.018), 0.32)
underside_mat = make_material("Warm underside", (0.76, 0.24, 0.085), 0.38)
antenna_mat = make_material("Antenna orange", (0.67, 0.075, 0.022), 0.25)
eye_mat = make_material("Glossy black eyes", (0.008, 0.006, 0.004), 0.12)
eye_stalk_mat = make_material("Eye stalks", (0.40, 0.045, 0.018), 0.28)

def smooth_object(obj):
    if obj.type == 'MESH':
        for poly in obj.data.polygons:
            poly.use_smooth = True

def uv_ellipsoid(name, location, scale, material, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_object(obj)
    obj.data.materials.append(material)
    return obj

def cone_between(name, start, end, radius1, radius2, material, vertices=16):
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    length = direction.length
    midpoint = (start + end) * 0.5
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius1,
        radius2=radius2,
        depth=length,
        location=midpoint
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(direction.normalized())
    smooth_object(obj)
    obj.data.materials.append(material)
    return obj

def make_bezier_tube(name, points, radii, bevel_depth, material, resolution=5):
    curve = bpy.data.curves.new(name + "_Curve", 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = resolution
    curve.render_resolution_u = resolution
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 4
    curve.resolution_u = 12
    curve.use_fill_caps = True

    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(points) - 1)
    for bp, co, radius in zip(spline.bezier_points, points, radii):
        bp.co = co
        bp.radius = radius
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'

    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

def add_torus_ring(name, location, tangent, major_radius, minor_radius, material):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=20,
        minor_segments=6,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(Vector(tangent).normalized())
    smooth_object(obj)
    obj.data.materials.append(material)
    return obj

# Broad, articulated abdomen.
abdomen_data = [
    (0.16, 1.00, 0.46, 0.76),
    (-0.30, 1.12, 0.48, 0.73),
    (-0.76, 1.10, 0.47, 0.70),
    (-1.20, 1.02, 0.44, 0.67),
    (-1.61, 0.91, 0.40, 0.63),
    (-1.98, 0.76, 0.34, 0.59),
]
for i, (x, width, height, z) in enumerate(abdomen_data):
    mat = shell_light if i % 2 == 0 else shell_mat
    uv_ellipsoid(
        "Rounded abdominal segment %02d" % (i + 1),
        (x, 0.0, z),
        (0.34, width, height),
        mat
    )

    # Rounded lateral pleura give each segment its characteristic skirt.
    for side in (-1, 1):
        uv_ellipsoid(
            "Segment %02d side plate %s" % (i + 1, "L" if side > 0 else "R"),
            (x - 0.025, side * width * 0.84, z - 0.10),
            (0.27, width * 0.27, height * 0.37),
            shell_mat,
            24,
            14
        )

# Narrow dark joint bands visible between the convex abdominal plates.
for i in range(len(abdomen_data) - 1):
    x = (abdomen_data[i][0] + abdomen_data[i + 1][0]) * 0.5
    width = min(abdomen_data[i][1], abdomen_data[i + 1][1]) * 0.96
    z = (abdomen_data[i][3] + abdomen_data[i + 1][3]) * 0.5
    uv_ellipsoid(
        "Abdominal joint %02d" % (i + 1),
        (x, 0.0, z - 0.025),
        (0.075, width, 0.34),
        shell_dark,
        24,
        14
    )

# Re-create the plates after joint bands so they visually overlap the joints.
# Compact cephalothorax and head.
uv_ellipsoid("Compact cephalothorax", (0.86, 0.0, 0.88), (0.86, 0.95, 0.58), shell_mat, 36, 22)
uv_ellipsoid("Front head shield", (1.48, 0.0, 0.94), (0.48, 0.76, 0.48), shell_light, 32, 20)
uv_ellipsoid("Ventral thorax", (0.72, 0.0, 0.47), (0.70, 0.72, 0.30), underside_mat, 30, 18)

# Short pointed rostrum, without front claws.
cone_between("Central rostrum", (1.58, 0.0, 1.18), (2.12, 0.0, 1.28), 0.18, 0.018, shell_mat, 20)
for side in (-1, 1):
    cone_between(
        "Lateral rostral point",
        (1.52, side * 0.31, 1.12),
        (1.96, side * 0.42, 1.24),
        0.10,
        0.012,
        shell_mat,
        16
    )

# Dorsal and lateral carapace spines.
dorsal_spines = [
    ((0.50, -0.50, 1.28), (0.44, -0.58, 1.63), 0.085),
    ((0.50, 0.50, 1.28), (0.44, 0.58, 1.63), 0.085),
    ((0.92, -0.44, 1.34), (0.89, -0.51, 1.68), 0.075),
    ((0.92, 0.44, 1.34), (0.89, 0.51, 1.68), 0.075),
    ((1.26, -0.36, 1.28), (1.30, -0.42, 1.57), 0.065),
    ((1.26, 0.36, 1.28), (1.30, 0.42, 1.57), 0.065),
    ((0.35, -0.82, 0.91), (0.21, -1.12, 1.03), 0.065),
    ((0.35, 0.82, 0.91), (0.21, 1.12, 1.03), 0.065),
]
for idx, (start, end, radius) in enumerate(dorsal_spines):
    cone_between("Carapace spine %02d" % idx, start, end, radius, 0.008, shell_dark, 14)

# Eyes and short stalks.
for side in (-1, 1):
    cone_between(
        "Eye stalk",
        (1.53, side * 0.39, 1.13),
        (1.78, side * 0.53, 1.31),
        0.095,
        0.075,
        eye_stalk_mat,
        18
    )
    uv_ellipsoid(
        "Black eye",
        (1.80, side * 0.55, 1.33),
        (0.13, 0.12, 0.12),
        eye_mat,
        24,
        16
    )

# Five pairs of slender, jointed, pointed walking legs.
leg_xs = [1.27, 0.90, 0.51, 0.10, -0.32]
for pair_index, x in enumerate(leg_xs):
    for side in (-1, 1):
        s = float(side)
        backward = 0.10 + pair_index * 0.055
        points = [
            (x, s * 0.57, 0.62),
            (x - 0.10, s * 0.96, 0.43),
            (x - backward, s * (1.31 + 0.05 * pair_index), 0.18),
            (x - 0.34 - backward, s * (1.56 + 0.055 * pair_index), 0.035),
        ]
        make_bezier_tube(
            "Walking leg %02d %s" % (pair_index + 1, "L" if side > 0 else "R"),
            points,
            (1.0, 0.80, 0.50, 0.08),
            0.105,
            underside_mat,
            4
        )
        # Small real-geometry joint collars.
        for joint_index in (1, 2):
            p = Vector(points[joint_index])
            tangent = Vector(points[joint_index + 1]) - Vector(points[joint_index - 1])
            add_torus_ring(
                "Leg joint collar",
                p,
                tangent,
                0.075 if joint_index == 1 else 0.055,
                0.017,
                shell_dark
            )

# Small abdominal swimmerets beneath the tailward segments.
for i, x in enumerate((-0.48, -0.88, -1.27, -1.62)):
    for side in (-1, 1):
        points = [
            (x, side * 0.43, 0.45),
            (x - 0.12, side * 0.68, 0.29),
            (x - 0.25, side * 0.79, 0.18)
        ]
        make_bezier_tube(
            "Swimmeret %02d" % (i * 2 + (1 if side < 0 else 2)),
            points,
            (0.85, 0.55, 0.10),
            0.055,
            underside_mat,
            3
        )

# Extremely long, stout, upward-curving antennae.
antenna_paths = {}
for side in (-1, 1):
    s = float(side)
    points = [
        (1.58, s * 0.48, 1.27),
        (2.05, s * 0.69, 1.72),
        (2.86, s * 0.86, 2.55),
        (3.85, s * 1.00, 3.34),
        (4.92, s * 0.95, 3.72),
        (5.82, s * 0.78, 3.53),
        (6.48, s * 0.58, 3.02)
    ]
    radii = (1.0, 0.96, 0.82, 0.66, 0.51, 0.36, 0.12)
    make_bezier_tube(
        "Long upward-curving antenna %s" % ("L" if side > 0 else "R"),
        points,
        radii,
        0.16,
        antenna_mat,
        8
    )
    antenna_paths[side] = points

    # Contrasting raised annular segmentation along each antenna.
    for j in range(1, len(points) - 1):
        p0 = Vector(points[j - 1])
        p1 = Vector(points[j])
        p2 = Vector(points[j + 1])
        tangent = (p2 - p0).normalized()
        local_radius = 0.16 * radii[j]
        add_torus_ring(
            "Antenna segment ring %s %02d" % ("L" if side > 0 else "R", j),
            p1,
            tangent,
            local_radius * 0.98,
            max(0.012, local_radius * 0.14),
            shell_dark
        )

    # Thorny basal antenna spines.
    for j in range(3):
        base = Vector(points[0]).lerp(Vector(points[1]), 0.20 + j * 0.22)
        outward = Vector((0.0, s, 0.35)).normalized()
        cone_between(
            "Basal antenna spine",
            base,
            base + outward * (0.24 - j * 0.035),
            0.045,
            0.004,
            shell_dark,
            12
        )

# Tail fan blades, made as beveled solid polygonal geometry.
def make_tail_blade(name, base, angle, length, width, material):
    forward = Vector((-math.cos(angle), math.sin(angle), 0.0))
    lateral = Vector((-math.sin(angle), -math.cos(angle), 0.0))
    base = Vector(base)

    outline = [
        (0.00, 0.00),
        (0.20, width * 0.55),
        (0.58, width),
        (0.94, width * 0.86),
        (1.00, 0.00),
        (0.94, -width * 0.86),
        (0.58, -width),
        (0.20, -width * 0.55),
    ]
    thickness = 0.075
    verts = []
    for zoff in (-thickness, thickness):
        for u, v in outline:
            p = base + forward * (u * length) + lateral * v + Vector((0.0, 0.0, zoff))
            verts.append(tuple(p))

    n = len(outline)
    faces = []
    faces.append(tuple(range(n)))
    faces.append(tuple(range(n, n * 2))[::-1])
    for i in range(n):
        ni = (i + 1) % n
        faces.append((i, ni, n + ni, n + i))

    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    bevel = obj.modifiers.new("Rounded fan edges", 'BEVEL')
    bevel.width = 0.07
    bevel.segments = 3
    smooth_object(obj)
    return obj

tail_base_x = -2.18
make_tail_blade("Central tail fan", (tail_base_x, 0.0, 0.57), 0.0, 1.22, 0.30, shell_light)
make_tail_blade("Inner left tail fan", (tail_base_x, 0.18, 0.57), 0.22, 1.18, 0.34, shell_mat)
make_tail_blade("Inner right tail fan", (tail_base_x, -0.18, 0.57), -0.22, 1.18, 0.34, shell_mat)
make_tail_blade("Outer left tail fan", (tail_base_x + 0.02, 0.39, 0.56), 0.48, 1.05, 0.31, shell_light)
make_tail_blade("Outer right tail fan", (tail_base_x + 0.02, -0.39, 0.56), -0.48, 1.05, 0.31, shell_light)

# Raised ribs on the tail fan.
tail_ribs = [
    ((-2.24, 0.00, 0.66), (-3.25, 0.00, 0.67)),
    ((-2.25, 0.22, 0.66), (-3.19, 0.43, 0.67)),
    ((-2.25, -0.22, 0.66), (-3.19, -0.43, 0.67)),
    ((-2.23, 0.44, 0.65), (-3.03, 0.87, 0.66)),
    ((-2.23, -0.44, 0.65), (-3.03, -0.87, 0.66)),
]
for i, (start, end) in enumerate(tail_ribs):
    make_bezier_tube(
        "Tail fan rib %02d" % i,
        [start, end],
        (0.8, 0.18),
        0.035,
        shell_dark,
        2
    )

# Subtle dorsal knobs on abdominal segments.
for i, (x, width, height, z) in enumerate(abdomen_data[1:-1], start=1):
    for side in (-1, 1):
        uv_ellipsoid(
            "Abdominal dorsal knob",
            (x + 0.03, side * width * 0.33, z + height * 0.84),
            (0.105, 0.095, 0.075),
            shell_light,
            18,
            10
        )

# Organize the assembly without adding non-geometry scene objects.
for obj in bpy.context.scene.objects:
    obj.select_set(False)