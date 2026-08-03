import bpy
import math
from mathutils import Vector

# Clear the default scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    pass

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

def set_principled_input(node, name, value):
    socket = node.inputs.get(name)
    if socket is not None:
        socket.default_value = value

def make_marble_material():
    mat = bpy.data.materials.new("Forest_Green_Marble")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    noise = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    texcoord.location = (-850, 50)
    mapping.location = (-670, 50)
    noise.location = (-470, 50)
    ramp.location = (-250, 80)
    bump.location = (-240, -150)
    principled.location = (20, 50)
    output.location = (270, 50)

    mapping.inputs["Scale"].default_value = (1.1, 4.8, 1.7)
    noise.noise_dimensions = '3D'
    noise.inputs["Scale"].default_value = 2.3
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.72
    noise.inputs["Lacunarity"].default_value = 2.1
    noise.inputs["Distortion"].default_value = 2.8

    color_ramp = ramp.color_ramp
    while len(color_ramp.elements) > 2:
        color_ramp.elements.remove(color_ramp.elements[-1])
    color_ramp.elements[0].position = 0.28
    color_ramp.elements[0].color = (0.004, 0.028, 0.016, 1.0)
    color_ramp.elements[1].position = 0.72
    color_ramp.elements[1].color = (0.018, 0.115, 0.055, 1.0)

    e = color_ramp.elements.new(0.46)
    e.color = (0.01, 0.065, 0.031, 1.0)
    e = color_ramp.elements.new(0.535)
    e.color = (0.12, 0.27, 0.17, 1.0)
    e = color_ramp.elements.new(0.575)
    e.color = (0.62, 0.69, 0.57, 1.0)
    e = color_ramp.elements.new(0.605)
    e.color = (0.025, 0.10, 0.047, 1.0)

    set_principled_input(principled, "Roughness", 0.16)
    set_principled_input(principled, "Metallic", 0.0)
    set_principled_input(principled, "IOR", 1.47)
    set_principled_input(principled, "Coat Weight", 0.32)
    set_principled_input(principled, "Coat Roughness", 0.08)

    bump.inputs["Strength"].default_value = 0.055
    bump.inputs["Distance"].default_value = 0.035

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], principled.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], principled.inputs["Normal"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    return mat

def make_chrome_material():
    mat = bpy.data.materials.new("Polished_Chrome")
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get("Principled BSDF")
    set_principled_input(principled, "Base Color", (0.72, 0.76, 0.79, 1.0))
    set_principled_input(principled, "Metallic", 1.0)
    set_principled_input(principled, "Roughness", 0.075)
    set_principled_input(principled, "Coat Weight", 0.2)
    return mat

marble = make_marble_material()
chrome = make_chrome_material()

def superellipse_ring(hx, hy, z, count=96, exponent=5.2):
    points = []
    p = 2.0 / exponent
    for i in range(count):
        angle = 2.0 * math.pi * i / count
        c = math.cos(angle)
        s = math.sin(angle)
        x = hx * math.copysign(abs(c) ** p, c)
        y = hy * math.copysign(abs(s) ** p, s)
        points.append((x, y, z))
    return points

def create_profile_mesh(name, profiles, material, count=96, exponent=5.2, cap_bottom=True, cap_top=True):
    verts = []
    faces = []
    rings = []
    for z, hx, hy in profiles:
        ring = []
        for co in superellipse_ring(hx, hy, z, count, exponent):
            ring.append(len(verts))
            verts.append(co)
        rings.append(ring)

    for r in range(len(rings) - 1):
        for i in range(count):
            j = (i + 1) % count
            faces.append((rings[r][i], rings[r][j], rings[r + 1][j], rings[r + 1][i]))

    if cap_bottom:
        center = len(verts)
        verts.append((0.0, 0.0, profiles[0][0]))
        for i in range(count):
            j = (i + 1) % count
            faces.append((rings[0][j], rings[0][i], center))

    if cap_top:
        center = len(verts)
        verts.append((0.0, 0.0, profiles[-1][0]))
        for i in range(count):
            j = (i + 1) % count
            faces.append((rings[-1][i], rings[-1][j], center))

    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj

def create_rounded_box(name, dimensions, location, bevel, material):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)

    modifier = obj.modifiers.new("Rounded_Edges", 'BEVEL')
    modifier.width = bevel
    modifier.segments = 6
    modifier.limit_method = 'ANGLE'
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj

# Broad, rounded square foot.
create_rounded_box(
    "Pedestal_Base",
    (1.72, 1.42, 0.32),
    (0.0, 0.0, 0.16),
    0.14,
    marble
)

# Classical tapered pedestal with a narrow waist and broad shoulder.
pedestal_profiles = [
    (0.25, 0.72, 0.57),
    (0.39, 0.76, 0.61),
    (0.52, 0.63, 0.50),
    (0.72, 0.50, 0.40),
    (1.15, 0.42, 0.34),
    (1.55, 0.44, 0.35),
    (1.82, 0.54, 0.43),
    (2.04, 0.77, 0.61),
    (2.16, 0.98, 0.72),
]
create_profile_mesh("Tapered_Pedestal", pedestal_profiles, marble, count=80, exponent=5.0)

# Basin outer shell, top rim, and smoothly descending inner bowl.
count = 112
verts = []
faces = []

outer_profiles = [
    (2.04, 1.17, 0.80),
    (2.16, 1.30, 0.90),
    (2.38, 1.55, 1.08),
    (2.58, 1.68, 1.19),
    (2.68, 1.72, 1.23),
]
outer_rings = []
for z, hx, hy in outer_profiles:
    ring = []
    for co in superellipse_ring(hx, hy, z, count, 5.4):
        ring.append(len(verts))
        verts.append(co)
    outer_rings.append(ring)

for r in range(len(outer_rings) - 1):
    for i in range(count):
        j = (i + 1) % count
        faces.append((
            outer_rings[r][i],
            outer_rings[r][j],
            outer_rings[r + 1][j],
            outer_rings[r + 1][i]
        ))

# Basin underside cap, mostly concealed by the pedestal shoulder.
bottom_center = len(verts)
verts.append((0.0, 0.0, outer_profiles[0][0]))
for i in range(count):
    j = (i + 1) % count
    faces.append((outer_rings[0][j], outer_rings[0][i], bottom_center))

inner_profiles = [
    (2.655, 1.48, 0.93),
    (2.56, 1.40, 0.85),
    (2.43, 1.24, 0.73),
    (2.29, 0.94, 0.55),
    (2.19, 0.58, 0.35),
    (2.135, 0.20, 0.15),
]
inner_rings = []
for z, hx, hy in inner_profiles:
    ring = []
    for co in superellipse_ring(hx, hy, z, count, 4.4):
        ring.append(len(verts))
        verts.append(co)
    inner_rings.append(ring)

# Wide rolled-looking rim.
for i in range(count):
    j = (i + 1) % count
    faces.append((
        outer_rings[-1][i],
        outer_rings[-1][j],
        inner_rings[0][j],
        inner_rings[0][i]
    ))

# Concave bowl.
for r in range(len(inner_rings) - 1):
    for i in range(count):
        j = (i + 1) % count
        faces.append((
            inner_rings[r][i],
            inner_rings[r][j],
            inner_rings[r + 1][j],
            inner_rings[r + 1][i]
        ))

bowl_center = len(verts)
verts.append((0.0, 0.0, 2.125))
for i in range(count):
    j = (i + 1) % count
    faces.append((inner_rings[-1][i], inner_rings[-1][j], bowl_center))

mesh = bpy.data.meshes.new("Flared_Basin_Mesh")
mesh.from_pydata(verts, [], faces)
mesh.update()
basin = bpy.data.objects.new("Wide_Flared_Basin", mesh)
bpy.context.collection.objects.link(basin)
basin.data.materials.append(marble)
for poly in mesh.polygons:
    poly.use_smooth = True

# Chrome drain trim and plug.
bpy.ops.mesh.primitive_torus_add(
    major_radius=0.145,
    minor_radius=0.025,
    major_segments=48,
    minor_segments=10,
    location=(0.0, 0.0, 2.145)
)
drain_ring = bpy.context.object
drain_ring.name = "Drain_Trim"
drain_ring.data.materials.append(chrome)

bpy.ops.mesh.primitive_cylinder_add(
    vertices=48,
    radius=0.12,
    depth=0.025,
    location=(0.0, 0.0, 2.143)
)
drain = bpy.context.object
drain.name = "Drain_Plug"
drain.data.materials.append(chrome)
for poly in drain.data.polygons:
    poly.use_smooth = True

def create_curve_tube(name, points, radius, material, resolution=5):
    curve_data = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 2
    curve_data.bevel_depth = radius
    curve_data.bevel_resolution = resolution
    curve_data.resolution_u = 12

    spline = curve_data.splines.new('NURBS')
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (co[0], co[1], co[2], 1.0)
    spline.order_u = min(4, len(points))
    spline.use_endpoint_u = True

    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

# Faucet escutcheon.
bpy.ops.mesh.primitive_cylinder_add(
    vertices=64,
    radius=0.18,
    depth=0.08,
    location=(0.0, 1.075, 2.72)
)
faucet_base = bpy.context.object
faucet_base.name = "Faucet_Escutcheon"
faucet_base.data.materials.append(chrome)
bevel = faucet_base.modifiers.new("Soft_Rim", 'BEVEL')
bevel.width = 0.025
bevel.segments = 3

# Gooseneck: vertical rear rise, rounded crown, forward/downward outlet.
faucet_points = []
for i in range(9):
    t = i / 8.0
    faucet_points.append((0.0, 1.075, 2.73 + 0.72 * t))
for i in range(1, 19):
    theta = math.pi * i / 18.0
    y = 0.665 + 0.410 * math.cos(theta)
    z = 3.45 + 0.410 * math.sin(theta)
    faucet_points.append((0.0, y, z))
for i in range(1, 7):
    t = i / 6.0
    faucet_points.append((0.0, 0.255, 3.45 - 0.30 * t))
create_curve_tube("Chrome_Gooseneck_Faucet", faucet_points, 0.075, chrome, 5)

# Outlet collar.
bpy.ops.mesh.primitive_cylinder_add(
    vertices=48,
    radius=0.105,
    depth=0.18,
    location=(0.0, 0.255, 3.09)
)
outlet = bpy.context.object
outlet.name = "Faucet_Outlet"
outlet.data.materials.append(chrome)
for poly in outlet.data.polygons:
    poly.use_smooth = True

def create_cylinder_between(name, start, end, radius, material, vertices=32):
    start_v = Vector(start)
    end_v = Vector(end)
    vector = end_v - start_v
    midpoint = (start_v + end_v) * 0.5
    length = vector.length
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=length,
        location=midpoint
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(vector.normalized())
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

def create_handle(x, label):
    # Flared mounting collar.
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48,
        radius=0.17,
        depth=0.075,
        location=(x, 1.075, 2.715)
    )
    collar = bpy.context.object
    collar.name = label + "_Escutcheon"
    collar.data.materials.append(chrome)
    bevel = collar.modifiers.new("Rounded_Collar", 'BEVEL')
    bevel.width = 0.025
    bevel.segments = 3

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=36,
        radius=0.065,
        depth=0.24,
        location=(x, 1.075, 2.86)
    )
    stem = bpy.context.object
    stem.name = label + "_Stem"
    stem.data.materials.append(chrome)
    for poly in stem.data.polygons:
        poly.use_smooth = True

    center_z = 3.005
    create_cylinder_between(
        label + "_Cross_X",
        (x - 0.22, 1.075, center_z),
        (x + 0.22, 1.075, center_z),
        0.045,
        chrome,
        24
    )
    create_cylinder_between(
        label + "_Cross_Y",
        (x, 0.855, center_z),
        (x, 1.295, center_z),
        0.045,
        chrome,
        24
    )

    for index, point in enumerate([
        (x - 0.23, 1.075, center_z),
        (x + 0.23, 1.075, center_z),
        (x, 0.845, center_z),
        (x, 1.305, center_z)
    ]):
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=24,
            ring_count=12,
            radius=0.071,
            location=point
        )
        knob = bpy.context.object
        knob.name = label + "_Cross_End_" + str(index + 1)
        knob.data.materials.append(chrome)
        for poly in knob.data.polygons:
            poly.use_smooth = True

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=28,
        ring_count=14,
        radius=0.085,
        location=(x, 1.075, center_z)
    )
    hub = bpy.context.object
    hub.name = label + "_Hub"
    hub.scale.z = 0.72
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    hub.data.materials.append(chrome)
    for poly in hub.data.polygons:
        poly.use_smooth = True

create_handle(-0.58, "Cold_Handle")
create_handle(0.58, "Hot_Handle")

# Organize the assembly while retaining all detailed component geometry.
for obj in bpy.context.scene.objects:
    obj.select_set(False)

# Set a neutral world without adding environmental objects.
scene.world.color = (0.035, 0.035, 0.035)
scene.render.engine = 'BLENDER_EEVEE_NEXT'