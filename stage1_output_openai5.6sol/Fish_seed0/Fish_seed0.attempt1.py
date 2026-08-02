import bpy
import math
from mathutils import Vector

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for datablocks in (
    bpy.data.meshes,
    bpy.data.curves,
    bpy.data.materials,
    bpy.data.cameras,
    bpy.data.lights,
):
    for datablock in list(datablocks):
        if datablock.users == 0:
            datablocks.remove(datablock)


def material_principled(name, color, roughness=0.7, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return mat


def body_material():
    mat = bpy.data.materials.new("Clouded Periwinkle Blue Gray Skin")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    noise_large = nodes.new("ShaderNodeTexNoise")
    noise_fine = nodes.new("ShaderNodeTexNoise")
    mix = nodes.new("ShaderNodeMixRGB")
    ramp = nodes.new("ShaderNodeValToRGB")
    texcoord = nodes.new("ShaderNodeTexCoord")

    noise_large.inputs["Scale"].default_value = 1.45
    noise_large.inputs["Detail"].default_value = 3.2
    noise_large.inputs["Roughness"].default_value = 0.72
    noise_large.inputs["Distortion"].default_value = 0.22

    noise_fine.inputs["Scale"].default_value = 7.5
    noise_fine.inputs["Detail"].default_value = 2.0
    noise_fine.inputs["Roughness"].default_value = 0.55

    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 0.18

    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = (0.25, 0.31, 0.46, 1.0)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = (0.57, 0.64, 0.79, 1.0)
    middle = ramp.color_ramp.elements.new(0.5)
    middle.color = (0.40, 0.48, 0.65, 1.0)

    shader.inputs["Roughness"].default_value = 0.82
    shader.inputs["Metallic"].default_value = 0.0

    links.new(texcoord.outputs["Generated"], noise_large.inputs["Vector"])
    links.new(texcoord.outputs["Generated"], noise_fine.inputs["Vector"])
    links.new(noise_large.outputs["Fac"], mix.inputs[1])
    links.new(noise_fine.outputs["Fac"], mix.inputs[2])
    links.new(mix.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return mat


skin_mat = body_material()
fin_mat = material_principled(
    "Golden Brown Fin Membrane",
    (0.67, 0.43, 0.18, 1.0),
    0.72
)
fin_light_mat = material_principled(
    "Golden Fin Ray Highlight",
    (0.92, 0.66, 0.28, 1.0),
    0.58
)
ray_mat = material_principled(
    "Dark Golden Brown Fin Rays",
    (0.29, 0.13, 0.045, 1.0),
    0.67
)
eye_mat = material_principled(
    "Black Eye",
    (0.002, 0.003, 0.005, 1.0),
    0.25
)
glint_mat = material_principled(
    "Eye Glint",
    (0.95, 0.91, 0.72, 1.0),
    0.2
)
mouth_mat = material_principled(
    "Mouth Interior",
    (0.035, 0.008, 0.012, 1.0),
    0.8
)
gill_mat = material_principled(
    "Gill Crease",
    (0.12, 0.17, 0.28, 1.0),
    0.76
)


def smoothstep(value):
    return value * value * (3.0 - 2.0 * value)


def interpolate(x, controls):
    if x <= controls[0][0]:
        return controls[0][1]
    if x >= controls[-1][0]:
        return controls[-1][1]
    for index in range(len(controls) - 1):
        x0, value0 = controls[index]
        x1, value1 = controls[index + 1]
        if x0 <= x <= x1:
            t = smoothstep((x - x0) / (x1 - x0))
            return value0 * (1.0 - t) + value1 * t
    return controls[-1][1]


def cone_between(name, start, end, radius_start, radius_end, material, vertices=10):
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    length = direction.length
    if length < 0.0001:
        return None

    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius_start,
        radius2=radius_end,
        depth=length,
        end_fill_type='NGON',
        location=(start + end) * 0.5
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = direction.to_track_quat('Z', 'Y')
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def make_prism_fin(name, polygon, half_thickness, material):
    count = len(polygon)
    vertices = []
    for y in (-half_thickness, half_thickness):
        vertices.extend((x, y, z) for x, z in polygon)

    faces = [
        tuple(range(count - 1, -1, -1)),
        tuple(range(count, count * 2))
    ]
    for i in range(count):
        j = (i + 1) % count
        faces.append((i, j, count + j, count + i))

    mesh = bpy.data.meshes.new(name + " Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    bevel = obj.modifiers.new("Soft Fin Margin", 'BEVEL')
    bevel.width = 0.022
    bevel.segments = 3

    for polygon_face in mesh.polygons:
        polygon_face.use_smooth = True
    return obj


def make_surface_fin(name, vertices, faces, material, thickness=0.035):
    mesh = bpy.data.meshes.new(name + " Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    solidify = obj.modifiers.new("Fin Thickness", 'SOLIDIFY')
    solidify.thickness = thickness
    solidify.offset = 0.0

    bevel = obj.modifiers.new("Rounded Fin Edges", 'BEVEL')
    bevel.width = 0.018
    bevel.segments = 2

    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def make_curve(name, points, bevel_depth, material):
    curve_data = bpy.data.curves.new(name + " Curve", 'CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 3
    curve_data.bevel_depth = bevel_depth
    curve_data.bevel_resolution = 3

    spline = curve_data.splines.new('BEZIER')
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = 'AUTO'
        point.handle_right_type = 'AUTO'

    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


height_controls = [
    (-2.46, 0.20),
    (-2.30, 0.61),
    (-1.96, 0.92),
    (-1.40, 1.13),
    (-0.72, 1.23),
    (0.00, 1.20),
    (0.67, 1.03),
    (1.20, 0.77),
    (1.58, 0.48),
    (1.82, 0.27),
    (1.98, 0.12)
]

width_controls = [
    (-2.46, 0.10),
    (-2.27, 0.30),
    (-1.92, 0.46),
    (-1.35, 0.54),
    (-0.65, 0.56),
    (0.05, 0.52),
    (0.72, 0.43),
    (1.25, 0.31),
    (1.62, 0.20),
    (1.98, 0.12)
]

ring_count = 49
ring_segments = 48
body_vertices = []
body_faces = []

for i in range(ring_count):
    t = i / (ring_count - 1)
    x = -2.46 + t * 4.44
    height = interpolate(x, height_controls)
    width = interpolate(x, width_controls)

    for j in range(ring_segments):
        angle = 2.0 * math.pi * j / ring_segments
        z = height * math.cos(angle)
        y = width * math.sin(angle)

        if z < 0.0:
            z *= 0.93
        if x < -1.65 and z > 0.0:
            z *= 1.02

        body_vertices.append((x, y, z))

for i in range(ring_count - 1):
    for j in range(ring_segments):
        next_j = (j + 1) % ring_segments
        a = i * ring_segments + j
        b = i * ring_segments + next_j
        c = (i + 1) * ring_segments + next_j
        d = (i + 1) * ring_segments + j
        body_faces.append((a, b, c, d))

body_faces.append(tuple(range(ring_segments - 1, -1, -1)))
last_ring = (ring_count - 1) * ring_segments
body_faces.append(tuple(last_ring + j for j in range(ring_segments)))

body_mesh = bpy.data.meshes.new("Laterally Compressed Oval Body Mesh")
body_mesh.from_pydata(body_vertices, [], body_faces)
body_mesh.update()

body = bpy.data.objects.new("Periwinkle Oval Fish Body", body_mesh)
bpy.context.collection.objects.link(body)
body.data.materials.append(skin_mat)

for polygon in body_mesh.polygons:
    polygon.use_smooth = True

subdivision = body.modifiers.new("Smooth Body", 'SUBSURF')
subdivision.subdivision_type = 'CATMULL_CLARK'
subdivision.levels = 2
subdivision.render_levels = 2


dorsal_polygon = [
    (-1.48, 0.83),
    (-1.27, 1.38),
    (-0.97, 1.78),
    (-0.58, 2.06),
    (-0.12, 2.17),
    (0.35, 2.08),
    (0.79, 1.82),
    (1.19, 1.38),
    (1.51, 0.69),
    (1.15, 0.80),
    (0.63, 1.00),
    (0.04, 1.17),
    (-0.60, 1.21),
    (-1.12, 1.05)
]
make_prism_fin("Large Fan Dorsal Fin", dorsal_polygon, 0.05, fin_mat)

dorsal_bases = [
    (-1.34, 0.94),
    (-1.12, 1.06),
    (-0.87, 1.15),
    (-0.59, 1.20),
    (-0.29, 1.22),
    (0.02, 1.18),
    (0.34, 1.10),
    (0.65, 1.00),
    (0.94, 0.88),
    (1.22, 0.77)
]
dorsal_tips = [
    (-1.25, 1.39),
    (-1.04, 1.66),
    (-0.78, 1.90),
    (-0.50, 2.07),
    (-0.18, 2.15),
    (0.14, 2.13),
    (0.46, 2.02),
    (0.75, 1.83),
    (1.02, 1.57),
    (1.30, 1.15)
]

for side in (-1, 1):
    y = side * 0.067
    for index, (base, tip) in enumerate(zip(dorsal_bases, dorsal_tips)):
        cone_between(
            "Dorsal Fin Ray",
            (base[0], y, base[1]),
            (tip[0], y, tip[1]),
            0.025,
            0.011,
            ray_mat if index % 2 == 0 else fin_light_mat,
            8
        )


tail_polygon = [
    (1.72, 0.30),
    (2.18, 0.77),
    (2.73, 1.16),
    (3.24, 1.37),
    (3.55, 0.88),
    (3.66, 0.33),
    (3.68, 0.00),
    (3.66, -0.33),
    (3.55, -0.88),
    (3.24, -1.37),
    (2.73, -1.16),
    (2.18, -0.77),
    (1.72, -0.30)
]
make_prism_fin("Large Fan Caudal Fin", tail_polygon, 0.065, fin_mat)

tail_tips = [
    (3.23, 1.34),
    (3.44, 1.05),
    (3.58, 0.72),
    (3.64, 0.38),
    (3.68, 0.00),
    (3.64, -0.38),
    (3.58, -0.72),
    (3.44, -1.05),
    (3.23, -1.34)
]

for side in (-1, 1):
    y = side * 0.082
    for index, tip in enumerate(tail_tips):
        base_z = 0.19 - index * 0.0475
        cone_between(
            "Caudal Fin Ray",
            (1.76, y, base_z),
            (tip[0], y, tip[1]),
            0.029,
            0.013,
            ray_mat if index % 2 else fin_light_mat,
            9
        )


anal_polygon = [
    (0.30, -1.00),
    (0.52, -1.30),
    (0.78, -1.49),
    (1.09, -1.43),
    (1.43, -1.08),
    (1.63, -0.61),
    (1.30, -0.72),
    (0.91, -0.91),
    (0.55, -1.00)
]
make_prism_fin("Small Anal Fin", anal_polygon, 0.043, fin_mat)

anal_bases = [
    (0.42, -1.02),
    (0.65, -1.01),
    (0.88, -0.94),
    (1.12, -0.83),
    (1.35, -0.70)
]
anal_tips = [
    (0.57, -1.31),
    (0.77, -1.47),
    (0.98, -1.46),
    (1.23, -1.28),
    (1.48, -0.91)
]

for side in (-1, 1):
    y = side * 0.058
    for index, (base, tip) in enumerate(zip(anal_bases, anal_tips)):
        cone_between(
            "Anal Fin Ray",
            (base[0], y, base[1]),
            (tip[0], y, tip[1]),
            0.021,
            0.009,
            ray_mat if index % 2 == 0 else fin_light_mat,
            8
        )


for side in (-1, 1):
    s = float(side)
    pectoral_vertices = [
        (-1.30, s * 0.43, 0.35),
        (-1.03, s * 0.56, 0.48),
        (-0.45, s * 0.82, 0.29),
        (0.12, s * 1.04, -0.02),
        (0.48, s * 1.08, -0.36),
        (0.14, s * 0.93, -0.56),
        (-0.47, s * 0.70, -0.39),
        (-1.14, s * 0.46, -0.12)
    ]
    pectoral_faces = [
        (0, 1, 2),
        (0, 2, 7),
        (2, 3, 7),
        (3, 4, 6, 7),
        (4, 5, 6)
    ]
    make_surface_fin(
        "Left Pectoral Fin" if side > 0 else "Right Pectoral Fin",
        pectoral_vertices,
        pectoral_faces,
        fin_mat,
        0.04
    )

    base = (-1.16, s * 0.50, 0.16)
    tips = [
        (-0.94, s * 0.61, 0.43),
        (-0.57, s * 0.77, 0.30),
        (-0.17, s * 0.92, 0.10),
        (0.18, s * 1.05, -0.08),
        (0.43, s * 1.08, -0.34),
        (0.12, s * 0.93, -0.52)
    ]
    for index, tip in enumerate(tips):
        cone_between(
            "Pectoral Fin Ray",
            base,
            tip,
            0.021,
            0.008,
            ray_mat if index % 2 else fin_light_mat,
            8
        )


for side in (-1, 1):
    s = float(side)
    pelvic_vertices = [
        (-0.66, s * 0.12, -1.03),
        (-0.34, s * 0.30, -1.12),
        (0.04, s * 0.45, -1.50),
        (0.35, s * 0.48, -1.67),
        (0.10, s * 0.22, -1.72),
        (-0.36, s * 0.10, -1.36)
    ]
    pelvic_faces = [
        (0, 1, 2),
        (0, 2, 5),
        (2, 3, 4, 5)
    ]
    make_surface_fin(
        "Left Pelvic Fin" if side > 0 else "Right Pelvic Fin",
        pelvic_vertices,
        pelvic_faces,
        fin_mat,
        0.032
    )

    base = (-0.49, s * 0.18, -1.08)
    tips = [
        (-0.22, s * 0.25, -1.45),
        (0.03, s * 0.35, -1.61),
        (0.31, s * 0.47, -1.66)
    ]
    for index, tip in enumerate(tips):
        cone_between(
            "Pelvic Fin Ray",
            base,
            tip,
            0.019,
            0.007,
            ray_mat if index % 2 else fin_light_mat,
            8
        )


for side in (-1, 1):
    s = float(side)
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=28,
        ring_count=16,
        location=(-1.70, s * 0.475, 0.37)
    )
    eye = bpy.context.object
    eye.name = "Left Circular Black Eye" if side > 0 else "Right Circular Black Eye"
    eye.scale = (0.125, 0.052, 0.125)
    eye.data.materials.append(eye_mat)
    for polygon in eye.data.polygons:
        polygon.use_smooth = True

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=12,
        ring_count=8,
        location=(-1.735, s * 0.525, 0.415)
    )
    glint = bpy.context.object
    glint.name = "Eye Highlight"
    glint.scale = (0.027, 0.012, 0.027)
    glint.data.materials.append(glint_mat)


bpy.ops.mesh.primitive_uv_sphere_add(
    segments=20,
    ring_count=12,
    location=(-2.465, 0.0, -0.065)
)
mouth_opening = bpy.context.object
mouth_opening.name = "Small Open Mouth Interior"
mouth_opening.scale = (0.045, 0.105, 0.075)
mouth_opening.data.materials.append(mouth_mat)

cone_between(
    "Pointed Upper Lip",
    (-2.38, -0.085, -0.015),
    (-2.55, -0.018, -0.052),
    0.029,
    0.009,
    skin_mat,
    10
)
cone_between(
    "Pointed Upper Lip Opposite",
    (-2.38, 0.085, -0.015),
    (-2.55, 0.018, -0.052),
    0.029,
    0.009,
    skin_mat,
    10
)
cone_between(
    "Pointed Lower Lip",
    (-2.38, -0.082, -0.115),
    (-2.55, -0.018, -0.078),
    0.027,
    0.008,
    skin_mat,
    10
)
cone_between(
    "Pointed Lower Lip Opposite",
    (-2.38, 0.082, -0.115),
    (-2.55, 0.018, -0.078),
    0.027,
    0.008,
    skin_mat,
    10
)


for side in (-1, 1):
    s = float(side)
    gill_points = []
    for index in range(13):
        t = index / 12.0
        angle = math.radians(64.0 - 128.0 * t)
        x = -1.18 + 0.18 * math.cos(angle)
        z = 0.02 + 0.67 * math.sin(angle)
        y = s * (0.515 - 0.025 * abs(z))
        gill_points.append((x, y, z))
    make_curve("Gill Cover Crease", gill_points, 0.015, gill_mat)


for side in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=12,
        ring_count=8,
        location=(-2.19, side * 0.30, 0.16)
    )
    nostril = bpy.context.object
    nostril.name = "Nostril"
    nostril.scale = (0.035, 0.016, 0.035)
    nostril.data.materials.append(mouth_mat)


bpy.ops.object.select_all(action='DESELECT')