import bpy
import math
from mathutils import Vector

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'


def set_input(node, name, value):
    socket = node.inputs.get(name)
    if socket:
        socket.default_value = value


def forest_marble_material():
    mat = bpy.data.materials.new("Dark_Forest_Green_Marble")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    noise_large = nodes.new("ShaderNodeTexNoise")
    noise_fine = nodes.new("ShaderNodeTexNoise")
    mix = nodes.new("ShaderNodeMixRGB")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    texcoord.location = (-900, 0)
    mapping.location = (-740, 0)
    noise_large.location = (-560, 80)
    noise_fine.location = (-560, -130)
    mix.location = (-350, 20)
    ramp.location = (-160, 70)
    bump.location = (-150, -150)
    shader.location = (70, 50)
    output.location = (320, 50)

    mapping.inputs["Scale"].default_value = (0.8, 2.4, 1.15)

    noise_large.noise_dimensions = '3D'
    noise_large.inputs["Scale"].default_value = 2.1
    noise_large.inputs["Detail"].default_value = 5.0
    noise_large.inputs["Roughness"].default_value = 0.68
    noise_large.inputs["Distortion"].default_value = 3.6

    noise_fine.noise_dimensions = '3D'
    noise_fine.inputs["Scale"].default_value = 7.0
    noise_fine.inputs["Detail"].default_value = 3.0
    noise_fine.inputs["Roughness"].default_value = 0.55
    noise_fine.inputs["Distortion"].default_value = 1.8

    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 0.82

    cr = ramp.color_ramp
    cr.interpolation = 'EASE'
    cr.elements[0].position = 0.20
    cr.elements[0].color = (0.003, 0.022, 0.010, 1.0)
    cr.elements[1].position = 0.54
    cr.elements[1].color = (0.008, 0.075, 0.030, 1.0)

    e = cr.elements.new(0.67)
    e.color = (0.018, 0.145, 0.060, 1.0)
    e = cr.elements.new(0.735)
    e.color = (0.12, 0.27, 0.16, 1.0)
    e = cr.elements.new(0.765)
    e.color = (0.58, 0.66, 0.55, 1.0)
    e = cr.elements.new(0.79)
    e.color = (0.025, 0.11, 0.045, 1.0)

    set_input(shader, "Roughness", 0.18)
    set_input(shader, "IOR", 1.48)
    set_input(shader, "Coat Weight", 0.38)
    set_input(shader, "Coat Roughness", 0.07)

    bump.inputs["Strength"].default_value = 0.025
    bump.inputs["Distance"].default_value = 0.015

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_large.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_fine.inputs["Vector"])
    links.new(noise_large.outputs["Fac"], mix.inputs[1])
    links.new(noise_fine.outputs["Fac"], mix.inputs[2])
    links.new(mix.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(noise_large.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return mat


def chrome_material():
    mat = bpy.data.materials.new("Polished_Chrome")
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    set_input(shader, "Base Color", (0.72, 0.77, 0.82, 1.0))
    set_input(shader, "Metallic", 1.0)
    set_input(shader, "Roughness", 0.08)
    set_input(shader, "Coat Weight", 0.25)
    return mat


marble = forest_marble_material()
chrome = chrome_material()


def superellipse(hx, hy, z, count=96, exponent=4.5):
    result = []
    power = 2.0 / exponent
    for i in range(count):
        a = 2.0 * math.pi * i / count
        c = math.cos(a)
        s = math.sin(a)
        x = hx * math.copysign(abs(c) ** power, c)
        y = hy * math.copysign(abs(s) ** power, s)
        result.append((x, y, z))
    return result


def profile_object(name, profiles, material, count=96, exponent=4.5):
    verts = []
    faces = []
    rings = []

    for z, hx, hy in profiles:
        ring = []
        for co in superellipse(hx, hy, z, count, exponent):
            ring.append(len(verts))
            verts.append(co)
        rings.append(ring)

    for r in range(len(rings) - 1):
        for i in range(count):
            j = (i + 1) % count
            faces.append((rings[r][i], rings[r][j],
                          rings[r + 1][j], rings[r + 1][i]))

    bottom = len(verts)
    verts.append((0, 0, profiles[0][0]))
    top = len(verts)
    verts.append((0, 0, profiles[-1][0]))

    for i in range(count):
        j = (i + 1) % count
        faces.append((rings[0][j], rings[0][i], bottom))
        faces.append((rings[-1][i], rings[-1][j], top))

    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj


def rounded_box(name, dimensions, location, bevel, material):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)

    mod = obj.modifiers.new("Rounded_Edges", 'BEVEL')
    mod.width = bevel
    mod.segments = 6
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


rounded_box(
    "Square_Pedestal_Foot",
    (1.42, 1.22, 0.28),
    (0, 0, 0.14),
    0.12,
    marble
)

profile_object(
    "Tapered_Pedestal",
    [
        (0.24, 0.64, 0.53),
        (0.38, 0.69, 0.57),
        (0.54, 0.53, 0.43),
        (0.78, 0.42, 0.34),
        (1.25, 0.36, 0.29),
        (1.62, 0.39, 0.31),
        (1.86, 0.52, 0.40),
        (2.02, 0.78, 0.57),
        (2.10, 1.02, 0.70)
    ],
    marble,
    80,
    4.6
)

count = 112
verts = []
faces = []
outer_rings = []
inner_rings = []

outer_profiles = [
    (2.03, 1.05, 0.72),
    (2.12, 1.27, 0.86),
    (2.29, 1.47, 1.00),
    (2.45, 1.57, 1.08),
    (2.52, 1.59, 1.10)
]

for profile in outer_profiles:
    ring = []
    for co in superellipse(profile[1], profile[2], profile[0], count, 5.0):
        ring.append(len(verts))
        verts.append(co)
    outer_rings.append(ring)

for r in range(len(outer_rings) - 1):
    for i in range(count):
        j = (i + 1) % count
        faces.append((outer_rings[r][i], outer_rings[r][j],
                      outer_rings[r + 1][j], outer_rings[r + 1][i]))

bottom_center = len(verts)
verts.append((0, 0, outer_profiles[0][0]))
for i in range(count):
    j = (i + 1) % count
    faces.append((outer_rings[0][j], outer_rings[0][i], bottom_center))

inner_profiles = [
    (2.50, 1.39, 0.88),
    (2.44, 1.31, 0.80),
    (2.34, 1.17, 0.68),
    (2.23, 0.91, 0.50),
    (2.15, 0.55, 0.29),
    (2.11, 0.20, 0.13)
]

for profile in inner_profiles:
    ring = []
    for co in superellipse(profile[1], profile[2], profile[0], count, 4.2):
        ring.append(len(verts))
        verts.append(co)
    inner_rings.append(ring)

for i in range(count):
    j = (i + 1) % count
    faces.append((outer_rings[-1][i], outer_rings[-1][j],
                  inner_rings[0][j], inner_rings[0][i]))

for r in range(len(inner_rings) - 1):
    for i in range(count):
        j = (i + 1) % count
        faces.append((inner_rings[r][i], inner_rings[r][j],
                      inner_rings[r + 1][j], inner_rings[r + 1][i]))

bowl_center = len(verts)
verts.append((0, 0, 2.095))
for i in range(count):
    j = (i + 1) % count
    faces.append((inner_rings[-1][i], inner_rings[-1][j], bowl_center))

mesh = bpy.data.meshes.new("Deep_Square_Basin_Mesh")
mesh.from_pydata(verts, [], faces)
mesh.update()
basin = bpy.data.objects.new("Wide_Rounded_Square_Basin", mesh)
bpy.context.collection.objects.link(basin)
basin.data.materials.append(marble)

for poly in mesh.polygons:
    poly.use_smooth = True

bpy.ops.mesh.primitive_torus_add(
    major_radius=0.12,
    minor_radius=0.022,
    major_segments=48,
    minor_segments=10,
    location=(0, 0, 2.115)
)
bpy.context.object.name = "Drain_Ring"
bpy.context.object.data.materials.append(chrome)

bpy.ops.mesh.primitive_cylinder_add(
    vertices=48,
    radius=0.097,
    depth=0.025,
    location=(0, 0, 2.11)
)
bpy.context.object.name = "Drain_Stopper"
bpy.context.object.data.materials.append(chrome)


def tube_curve(name, points, radius, material):
    curve = bpy.data.curves.new(name + "_Curve", 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 12
    curve.bevel_depth = radius
    curve.bevel_resolution = 5

    spline = curve.splines.new('NURBS')
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (co[0], co[1], co[2], 1.0)
    spline.order_u = min(4, len(points))
    spline.use_endpoint_u = True

    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.object
    obj.name = name
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.select_set(False)
    return obj


def chrome_cylinder(name, radius, depth, location, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48,
        radius=radius,
        depth=depth,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(chrome)
    for poly in obj.data.polygons:
        poly.use_smooth = True

    if bevel:
        mod = obj.modifiers.new("Edge_Bevel", 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


mount_y = 0.91
chrome_cylinder("Faucet_Base", 0.16, 0.075, (0, mount_y, 2.555), 0.018)

faucet_points = []
for i in range(8):
    t = i / 7
    faucet_points.append((0, mount_y, 2.58 + 0.60 * t))

for i in range(1, 17):
    a = math.pi * i / 16
    faucet_points.append((
        0,
        0.53 + 0.38 * math.cos(a),
        3.18 + 0.38 * math.sin(a)
    ))

for i in range(1, 7):
    t = i / 6
    faucet_points.append((0, 0.15, 3.18 - 0.29 * t))

tube_curve("Chrome_Gooseneck", faucet_points, 0.065, chrome)
chrome_cylinder("Faucet_Aerator", 0.092, 0.15, (0, 0.15, 2.82), 0.012)


def cylinder_between(name, start, end, radius):
    a = Vector(start)
    b = Vector(end)
    direction = b - a
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=28,
        radius=radius,
        depth=direction.length,
        location=(a + b) * 0.5
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(
        direction.normalized()
    )
    obj.data.materials.append(chrome)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def make_handle(x, name):
    chrome_cylinder(name + "_Base", 0.145, 0.07, (x, mount_y, 2.55), 0.018)
    chrome_cylinder(name + "_Stem", 0.055, 0.22, (x, mount_y, 2.68), 0.01)

    z = 2.82
    cylinder_between(
        name + "_Bar",
        (x - 0.20, mount_y, z),
        (x + 0.20, mount_y, z),
        0.04
    )

    for index, px in enumerate((x - 0.22, x + 0.22)):
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=24,
            ring_count=12,
            radius=0.064,
            location=(px, mount_y, z)
        )
        knob = bpy.context.object
        knob.name = name + "_End_" + str(index)
        knob.data.materials.append(chrome)

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=28,
        ring_count=14,
        radius=0.074,
        location=(x, mount_y, z)
    )
    hub = bpy.context.object
    hub.name = name + "_Hub"
    hub.data.materials.append(chrome)


make_handle(-0.56, "Cold_Handle")
make_handle(0.56, "Hot_Handle")

for obj in bpy.context.selected_objects:
    obj.select_set(False)

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        break

scene.world.color = (0.025, 0.025, 0.025)

engines = {
    item.identifier
    for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
}
if 'BLENDER_EEVEE' in engines:
    scene.render.engine = 'BLENDER_EEVEE'