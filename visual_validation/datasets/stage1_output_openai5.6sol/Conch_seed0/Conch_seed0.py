import bpy
import bmesh
import math
from mathutils import Vector

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for collection in (
    bpy.data.meshes,
    bpy.data.curves,
    bpy.data.materials,
    bpy.data.cameras,
    bpy.data.lights,
):
    for datablock in list(collection):
        if datablock.users == 0:
            collection.remove(datablock)


def smooth_mesh(obj):
    if obj.type == 'MESH':
        for polygon in obj.data.polygons:
            polygon.use_smooth = True


def make_shell_material():
    material = bpy.data.materials.new("Irregular brown and cream conch pattern")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    noise = nodes.new("ShaderNodeTexNoise")
    wave = nodes.new("ShaderNodeTexWave")
    mix = nodes.new("ShaderNodeMixRGB")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump_noise = nodes.new("ShaderNodeTexNoise")
    bump = nodes.new("ShaderNodeBump")

    output.location = (760, 60)
    bsdf.location = (520, 60)
    ramp.location = (280, 80)
    mix.location = (40, 100)
    wave.location = (-210, -40)
    noise.location = (-210, 190)
    mapping.location = (-440, 80)
    texcoord.location = (-650, 80)
    bump_noise.location = (-180, -260)
    bump.location = (280, -170)

    mapping.inputs["Rotation"].default_value = (
        math.radians(9.0),
        math.radians(18.0),
        math.radians(-13.0),
    )
    mapping.inputs["Scale"].default_value = (0.88, 1.08, 0.72)

    noise.noise_dimensions = '3D'
    noise.inputs["Scale"].default_value = 2.0
    noise.inputs["Detail"].default_value = 7.0
    noise.inputs["Roughness"].default_value = 0.72
    noise.inputs["Distortion"].default_value = 2.6

    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Z'
    wave.inputs["Scale"].default_value = 4.0
    wave.inputs["Distortion"].default_value = 7.0
    wave.inputs["Detail"].default_value = 5.0
    wave.inputs["Detail Scale"].default_value = 1.8

    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 0.72

    color_ramp = ramp.color_ramp
    color_ramp.interpolation = 'EASE'
    color_ramp.elements.remove(color_ramp.elements[1])
    color_ramp.elements[0].position = 0.16
    color_ramp.elements[0].color = (0.10, 0.025, 0.008, 1.0)

    element = color_ramp.elements.new(0.31)
    element.color = (0.31, 0.09, 0.025, 1.0)
    element = color_ramp.elements.new(0.43)
    element.color = (0.70, 0.40, 0.16, 1.0)
    element = color_ramp.elements.new(0.56)
    element.color = (0.96, 0.79, 0.53, 1.0)
    element = color_ramp.elements.new(0.68)
    element.color = (0.43, 0.16, 0.045, 1.0)
    element = color_ramp.elements.new(0.82)
    element.color = (0.91, 0.70, 0.42, 1.0)
    element = color_ramp.elements.new(0.92)
    element.color = (0.25, 0.065, 0.018, 1.0)

    bump_noise.noise_dimensions = '3D'
    bump_noise.inputs["Scale"].default_value = 18.0
    bump_noise.inputs["Detail"].default_value = 5.0
    bump_noise.inputs["Roughness"].default_value = 0.68

    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.07

    bsdf.inputs["Roughness"].default_value = 0.48
    bsdf.inputs["IOR"].default_value = 1.43

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    links.new(noise.outputs["Fac"], mix.inputs[1])
    links.new(wave.outputs["Fac"], mix.inputs[2])
    links.new(mix.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(mapping.outputs["Vector"], bump_noise.inputs["Vector"])
    links.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def make_simple_material(name, color, roughness):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["IOR"].default_value = 1.42
    return material


shell_material = make_shell_material()
lip_material = make_simple_material(
    "Warm cream aperture lip",
    (0.82, 0.47, 0.20, 1.0),
    0.42
)
interior_material = make_simple_material(
    "Deep reddish brown aperture",
    (0.16, 0.035, 0.018, 1.0),
    0.58
)
inner_fold_material = make_simple_material(
    "Pale inner folds",
    (0.88, 0.54, 0.27, 1.0),
    0.44
)


BODY_RX = 1.62
BODY_RY = 1.31
BODY_RZ = 1.78
BODY_Z = -0.12

AP_CX = 0.48
AP_CZ = -0.35
AP_RX = 0.82
AP_RZ = 1.20


def body_position(latitude, longitude, extra=0.0):
    cl = math.cos(latitude)
    horizontal_ridges = 1.0
    horizontal_ridges += 0.035 * math.sin(
        15.0 * latitude + 0.52 * math.sin(4.0 * longitude)
    )
    horizontal_ridges += 0.014 * math.sin(
        29.0 * latitude - 0.8 * math.sin(3.0 * longitude)
    )
    broad_undulation = 1.0 + 0.025 * math.sin(
        5.0 * longitude + 2.2 * latitude
    )
    radius = horizontal_ridges * broad_undulation + extra

    x = BODY_RX * cl * math.cos(longitude) * radius
    y = BODY_RY * cl * math.sin(longitude) * radius
    z = BODY_Z + BODY_RZ * math.sin(latitude)
    z += 0.05 * math.sin(5.0 * longitude) * cl
    return Vector((x, y, z))


def aperture_mask(x, z, margin=1.0):
    value = ((x - AP_CX) / (AP_RX * margin)) ** 2
    value += ((z - AP_CZ) / (AP_RZ * margin)) ** 2
    return value < 1.0


bpy.ops.mesh.primitive_uv_sphere_add(
    segments=144,
    ring_count=96,
    location=(0.0, 0.0, 0.0)
)
body = bpy.context.object
body.name = "Broad rounded conch body whorl"

for vertex in body.data.vertices:
    original = vertex.co.normalized()
    latitude = math.asin(max(-1.0, min(1.0, original.z)))
    longitude = math.atan2(original.y, original.x)
    vertex.co = body_position(latitude, longitude)

body.data.materials.append(shell_material)
smooth_mesh(body)

bm = bmesh.new()
bm.from_mesh(body.data)
faces_to_remove = []
for face in bm.faces:
    center = face.calc_center_median()
    if center.y < -0.46 and aperture_mask(center.x, center.z, 1.03):
        faces_to_remove.append(face)
bmesh.ops.delete(bm, geom=faces_to_remove, context='FACES')
bm.to_mesh(body.data)
bm.free()
body.data.update()


def make_deformed_whorl(name, location, scale, phase):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=96,
        ring_count=56,
        location=location
    )
    obj = bpy.context.object
    obj.name = name

    for vertex in obj.data.vertices:
        p = vertex.co.copy()
        longitude = math.atan2(p.y, p.x)
        latitude = math.asin(max(-1.0, min(1.0, p.z)))
        relief = 1.0
        relief += 0.045 * math.sin(
            11.0 * latitude + phase + 0.55 * math.sin(4.0 * longitude)
        )
        relief += 0.016 * math.sin(7.0 * longitude - 3.0 * latitude + phase)
        p.x *= scale[0] * relief
        p.y *= scale[1] * relief
        p.z *= scale[2]
        vertex.co = p

    obj.data.materials.append(shell_material)
    smooth_mesh(obj)
    return obj


whorl_specs = [
    ((-0.06, 0.02, 1.40), (1.15, 0.97, 0.62), 0.2),
    ((0.03, 0.01, 1.88), (0.89, 0.74, 0.54), 1.0),
    ((-0.03, 0.02, 2.31), (0.66, 0.57, 0.47), 1.8),
    ((0.02, 0.01, 2.68), (0.46, 0.41, 0.39), 2.7),
    ((-0.01, 0.0, 2.98), (0.31, 0.28, 0.31), 3.5),
]

for index, specification in enumerate(whorl_specs):
    make_deformed_whorl(
        "Integrated spiral whorl %02d" % index,
        specification[0],
        specification[1],
        specification[2]
    )

bpy.ops.mesh.primitive_cone_add(
    vertices=72,
    radius1=0.25,
    radius2=0.018,
    depth=0.72,
    location=(0.0, 0.0, 3.38)
)
spire_tip = bpy.context.object
spire_tip.name = "Continuous pointed spire"
spire_tip.data.materials.append(shell_material)
smooth_mesh(spire_tip)


def make_poly_curve(name, points, bevel_depth, material, cyclic=False):
    if len(points) < 2:
        return None

    curve_data = bpy.data.curves.new(name, 'CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 1
    curve_data.bevel_depth = bevel_depth
    curve_data.bevel_resolution = 3
    curve_data.resolution_u = 2

    spline = curve_data.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for index, point in enumerate(points):
        spline.points[index].co = (point.x, point.y, point.z, 1.0)
    spline.use_cyclic_u = cyclic

    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


ridge_latitudes = [-0.70, -0.53, -0.35, -0.16, 0.04, 0.24, 0.45, 0.64]
for ridge_index, latitude in enumerate(ridge_latitudes):
    visible_segments = []
    current_segment = []

    for index in range(181):
        longitude = -math.pi + math.tau * index / 180.0
        waviness = 0.018 * math.sin(5.0 * longitude + ridge_index * 0.7)
        waviness += 0.008 * math.sin(11.0 * longitude - ridge_index)
        point = body_position(
            latitude + waviness,
            longitude,
            extra=0.022
        )

        hidden_by_opening = (
            point.y < -0.30 and aperture_mask(point.x, point.z, 1.20)
        )

        if hidden_by_opening:
            if len(current_segment) > 2:
                visible_segments.append(current_segment)
            current_segment = []
        else:
            current_segment.append(point)

    if len(current_segment) > 2:
        visible_segments.append(current_segment)

    for segment_index, points in enumerate(visible_segments):
        make_poly_curve(
            "Attached wavy growth ridge %02d_%02d" % (
                ridge_index,
                segment_index
            ),
            points,
            0.042,
            shell_material,
            False
        )


spire_ridge_specs = [
    ((-0.06, 0.02, 1.52), 1.09, 0.91),
    ((0.03, 0.01, 2.00), 0.82, 0.68),
    ((-0.03, 0.02, 2.43), 0.59, 0.50),
    ((0.02, 0.01, 2.78), 0.40, 0.35),
    ((-0.01, 0.0, 3.07), 0.26, 0.23),
]

for ridge_index, (center, radius_x, radius_y) in enumerate(spire_ridge_specs):
    points = []
    for index in range(112):
        angle = math.tau * index / 112.0
        wobble = 1.0 + 0.025 * math.sin(
            6.0 * angle + ridge_index * 0.8
        )
        points.append(Vector((
            center[0] + radius_x * wobble * math.cos(angle),
            center[1] + radius_y * wobble * math.sin(angle),
            center[2] + 0.022 * math.sin(4.0 * angle + ridge_index)
        )))
    make_poly_curve(
        "Snug spire growth ridge %02d" % ridge_index,
        points,
        0.035,
        shell_material,
        True
    )


def shell_front_y(x, z):
    normalized = 1.0
    normalized -= (x / BODY_RX) ** 2
    normalized -= ((z - BODY_Z) / BODY_RZ) ** 2
    return -BODY_RY * math.sqrt(max(0.035, normalized))


def aperture_edge(angle, scale=1.0):
    ripple = 1.0
    ripple += 0.022 * math.sin(7.0 * angle)
    ripple += 0.010 * math.sin(13.0 * angle + 0.4)

    upper_taper = 1.0 - 0.12 * max(0.0, math.sin(angle))
    lower_flare = 1.0 + 0.10 * max(0.0, -math.sin(angle))

    x = AP_CX + AP_RX * scale * ripple * upper_taper * lower_flare * math.cos(angle)
    z = AP_CZ + AP_RZ * scale * ripple * math.sin(angle)
    y = shell_front_y(x, z) - 0.025
    return Vector((x, y, z))


segments = 144
radial_rings = 32
aperture_vertices = []
aperture_faces = []

center_y = -0.18
aperture_vertices.append((AP_CX - 0.06, center_y, AP_CZ - 0.06))

for ring_index in range(1, radial_rings + 1):
    radius = ring_index / radial_rings
    for index in range(segments):
        angle = math.tau * index / segments
        edge = aperture_edge(angle, 0.95)
        x = AP_CX + (edge.x - AP_CX) * radius
        z = AP_CZ + (edge.z - AP_CZ) * radius
        y = edge.y + (center_y - edge.y) * ((1.0 - radius) ** 1.55)
        y += 0.018 * math.sin(4.0 * angle + radius * 5.0) * radius
        aperture_vertices.append((x, y, z))

for index in range(segments):
    aperture_faces.append((
        0,
        1 + (index + 1) % segments,
        1 + index
    ))

for ring_index in range(radial_rings - 1):
    first = 1 + ring_index * segments
    second = first + segments
    for index in range(segments):
        next_index = (index + 1) % segments
        aperture_faces.append((
            first + index,
            first + next_index,
            second + next_index,
            second + index
        ))

mesh = bpy.data.meshes.new("Recessed aperture mesh")
mesh.from_pydata(aperture_vertices, [], aperture_faces)
mesh.update()

aperture = bpy.data.objects.new("Deep recessed wide aperture", mesh)
bpy.context.collection.objects.link(aperture)
aperture.data.materials.append(interior_material)
smooth_mesh(aperture)


lip_vertices = []
lip_faces = []
lip_scales = (0.88, 1.00, 1.14)

for ring_index, scale in enumerate(lip_scales):
    for index in range(segments):
        angle = math.tau * index / segments
        point = aperture_edge(angle, scale)
        if ring_index == 0:
            point.y += 0.035
        elif ring_index == 1:
            point.y -= 0.04
        else:
            point.y += 0.015
        lip_vertices.append(tuple(point))

for ring_index in range(2):
    first = ring_index * segments
    second = first + segments
    for index in range(segments):
        next_index = (index + 1) % segments
        lip_faces.append((
            first + index,
            first + next_index,
            second + next_index,
            second + index
        ))

mesh = bpy.data.meshes.new("Contiguous flared aperture lip mesh")
mesh.from_pydata(lip_vertices, [], lip_faces)
mesh.update()

lip = bpy.data.objects.new("Broad contiguous flared aperture lip", mesh)
bpy.context.collection.objects.link(lip)
lip.data.materials.append(lip_material)
smooth_mesh(lip)

solidify = lip.modifiers.new("Thick shell lip", 'SOLIDIFY')
solidify.thickness = 0.075
solidify.offset = 0.0

bevel = lip.modifiers.new("Rounded lip edges", 'BEVEL')
bevel.width = 0.035
bevel.segments = 3


rim_vertices = []
rim_faces = []
tube_sides = 14

for index in range(segments):
    angle = math.tau * index / segments
    point = aperture_edge(angle, 1.025)
    previous = aperture_edge(angle - 0.008, 1.025)
    following = aperture_edge(angle + 0.008, 1.025)
    tangent = (following - previous).normalized()

    front = Vector((0.0, -1.0, 0.0))
    outward = tangent.cross(front).normalized()
    radial = Vector((point.x - AP_CX, 0.0, point.z - AP_CZ))
    if outward.dot(radial) < 0.0:
        outward.negate()

    radius = 0.095
    radius *= 1.0 + 0.10 * math.sin(5.0 * angle + 0.5)
    radius *= 1.0 + 0.14 * max(0.0, -math.sin(angle))

    for side in range(tube_sides):
        tube_angle = math.tau * side / tube_sides
        vertex = point
        vertex += outward * (radius * math.cos(tube_angle))
        vertex += front * (radius * math.sin(tube_angle))
        rim_vertices.append(tuple(vertex))

for index in range(segments):
    next_index = (index + 1) % segments
    for side in range(tube_sides):
        next_side = (side + 1) % tube_sides
        rim_faces.append((
            index * tube_sides + side,
            next_index * tube_sides + side,
            next_index * tube_sides + next_side,
            index * tube_sides + next_side
        ))

mesh = bpy.data.meshes.new("Rolled aperture rim mesh")
mesh.from_pydata(rim_vertices, [], rim_faces)
mesh.update()

rim = bpy.data.objects.new("Thick integrated rolled aperture rim", mesh)
bpy.context.collection.objects.link(rim)
rim.data.materials.append(lip_material)
smooth_mesh(rim)


columella_points = []
for index in range(64):
    factor = index / 63.0
    z = AP_CZ - 0.86 + 1.68 * factor
    x = AP_CX - 0.28 - 0.10 * math.sin(math.pi * factor)
    x += 0.025 * math.sin(5.0 * math.pi * factor)
    y = -0.70 + 0.42 * math.sin(math.pi * factor) ** 2
    columella_points.append(Vector((x, y, z)))

make_poly_curve(
    "Attached inner columella",
    columella_points,
    0.095,
    inner_fold_material,
    False
)

for fold_index in range(4):
    points = []
    radius = 0.28 + fold_index * 0.10
    for index in range(48):
        angle = math.radians(208.0) + math.radians(104.0) * index / 47.0
        x = AP_CX + radius * 1.30 * math.cos(angle)
        z = AP_CZ - 0.12 + radius * 0.95 * math.sin(angle)
        y = -0.72 + 0.24 * (1.0 - radius)
        points.append(Vector((x, y, z)))
    make_poly_curve(
        "Inner aperture fold %02d" % fold_index,
        points,
        0.025 + fold_index * 0.004,
        inner_fold_material,
        False
    )


for obj in list(bpy.context.scene.objects):
    if obj.type == 'CURVE':
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.convert(target='MESH')
        obj.select_set(False)

bpy.context.view_layer.update()

mesh_objects = [
    obj for obj in bpy.context.scene.objects
    if obj.type == 'MESH'
]

bpy.ops.object.select_all(action='DESELECT')
for obj in mesh_objects:
    obj.select_set(True)

bpy.context.view_layer.objects.active = body
bpy.ops.object.join()

shell = bpy.context.object
shell.name = "Complete textured conch shell"
shell.rotation_euler[2] = math.radians(-8.0)

for polygon in shell.data.polygons:
    polygon.use_smooth = True

bpy.context.view_layer.update()