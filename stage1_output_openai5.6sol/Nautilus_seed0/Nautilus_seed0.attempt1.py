import bpy
import math
import random

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for collection in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    for datablock in list(collection):
        if datablock.users == 0:
            collection.remove(datablock)

random.seed(27)

RX = 3.40
RY = 3.18
DEPTH = 1.08
CENTER_X = -0.38
CENTER_Y = 0.03

def material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    if node:
        node.inputs["Base Color"].default_value = (*color, 1.0)
        node.inputs["Roughness"].default_value = roughness
        node.inputs["Metallic"].default_value = 0.0
    return mat

ivory = material("Warm cream shell", (0.82, 0.68, 0.45), 0.49)
pale_ivory = material("Pale whorl highlight", (0.96, 0.84, 0.62), 0.45)
center_ivory = material("Central chamber cream", (0.90, 0.75, 0.50), 0.47)
dark_brown = material("Deep umber seam", (0.13, 0.038, 0.012), 0.58)
brown = material("Chestnut markings", (0.35, 0.105, 0.030), 0.57)
warm_brown = material("Warm brown markings", (0.49, 0.185, 0.050), 0.56)
ochre = material("Ochre markings", (0.61, 0.31, 0.105), 0.54)

def surface_z(x, y, offset=0.0):
    q = (x / RX) ** 2 + (y / RY) ** 2
    return DEPTH * math.sqrt(max(0.0, 1.0 - q)) + offset

def boundary_radius(angle):
    dx = math.cos(angle)
    dy = math.sin(angle)
    a = dx * dx / (RX * RX) + dy * dy / (RY * RY)
    b = 2.0 * (
        CENTER_X * dx / (RX * RX) +
        CENTER_Y * dy / (RY * RY)
    )
    c = (
        CENTER_X * CENTER_X / (RX * RX) +
        CENTER_Y * CENTER_Y / (RY * RY) - 1.0
    )
    disc = max(0.0, b * b - 4.0 * a * c)
    return (-b + math.sqrt(disc)) / (2.0 * a)

def create_curve(name, points, bevel, mat, radii=None, cyclic=False, resolution=3):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 2
    data.bevel_depth = bevel
    data.bevel_resolution = resolution
    data.resolution_u = 2

    spline = data.splines.new('NURBS' if not cyclic and len(points) > 4 else 'POLY')
    spline.points.add(len(points) - 1)

    for i, point in enumerate(points):
        spline.points[i].co = (point[0], point[1], point[2], 1.0)
        if radii is not None:
            spline.points[i].radius = radii[i]

    if spline.type == 'NURBS':
        spline.order_u = min(4, len(points))
        spline.use_endpoint_u = True

    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj

# Rounded planispiral shell body
bpy.ops.mesh.primitive_uv_sphere_add(
    segments=160,
    ring_count=96,
    location=(0.0, 0.0, 0.0)
)
shell = bpy.context.object
shell.name = "Thick rounded nautilus shell"
shell.scale = (RX, RY, DEPTH)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
shell.data.materials.append(ivory)

for polygon in shell.data.polygons:
    polygon.use_smooth = True

# Irregular radiating surface bands
stripe_vertices = []
stripe_faces = []
stripe_indices = []
stripe_materials = [brown, warm_brown, ochre]
stripe_count = 31
steps = 52

for stripe_index in range(stripe_count):
    base_angle = 2.0 * math.pi * stripe_index / stripe_count
    base_angle += random.uniform(-0.035, 0.035)
    phase = random.uniform(0.0, 2.0 * math.pi)
    broad_wave = random.uniform(0.035, 0.085)
    curl = random.uniform(-0.12, 0.12)
    width = random.uniform(0.025, 0.046)

    for front in (True, False):
        start = len(stripe_vertices)

        for j in range(steps):
            t = j / (steps - 1)
            s = 0.12 + 0.855 * t

            angle = (
                base_angle
                + curl * (1.0 - s) ** 1.45
                + broad_wave * math.sin(3.5 * math.pi * s + phase)
                + 0.018 * math.sin(11.0 * math.pi * s + phase * 0.6)
            )

            flutter = 1.0 + 0.20 * math.sin(6.0 * math.pi * s + phase)
            half_width = width * flutter * (0.72 + 0.28 * s)

            side_order = (-1.0, 1.0) if front else (1.0, -1.0)
            for side in side_order:
                edge_angle = angle + side * half_width
                radius = boundary_radius(edge_angle) * s
                x = CENTER_X + radius * math.cos(edge_angle)
                y = CENTER_Y + radius * math.sin(edge_angle)
                z = surface_z(x, y, 0.012 + 0.012 * s)
                if not front:
                    z = -z
                stripe_vertices.append((x, y, z))

        for j in range(steps - 1):
            a = start + j * 2
            stripe_faces.append((a, a + 1, a + 3, a + 2))
            stripe_indices.append(stripe_index % len(stripe_materials))

stripe_mesh = bpy.data.meshes.new("Organic radiating stripe mesh")
stripe_mesh.from_pydata(stripe_vertices, [], stripe_faces)
stripe_mesh.update()

stripes = bpy.data.objects.new("Wavy brown radiating shell markings", stripe_mesh)
bpy.context.collection.objects.link(stripes)

for mat in stripe_materials:
    stripes.data.materials.append(mat)

for polygon, index in zip(stripes.data.polygons, stripe_indices):
    polygon.material_index = index
    polygon.use_smooth = True

# Logarithmic whorl boundary, kept low against the shell
theta_start = -5.25 * math.pi
theta_end = 0.02
radius_start = 0.09
radius_end = 3.45
growth = math.log(radius_end / radius_start)
spiral_points = []
spiral_radii = []

for i in range(330):
    u = i / 329.0
    theta = theta_start + (theta_end - theta_start) * u
    radius = radius_start * math.exp(growth * u)

    x = CENTER_X + radius * math.cos(theta)
    y = CENTER_Y + radius * math.sin(theta)
    q = (x / RX) ** 2 + (y / RY) ** 2

    if q >= 0.992:
        break

    z = surface_z(x, y, 0.027)
    spiral_points.append((x, y, z))

    outer_taper = max(0.15, min(1.0, (1.0 - u) / 0.10))
    inner_taper = max(0.25, min(1.0, u / 0.055))
    spiral_radii.append((0.72 + 0.42 * u) * outer_taper * inner_taper)

# Soft ivory shoulder makes the whorl feel layered but not tubular
create_curve(
    "Subtle raised whorl shoulder",
    spiral_points,
    0.070,
    pale_ivory,
    radii=[r * 1.25 for r in spiral_radii],
    resolution=4
)

# Fine dark groove centered on the shoulder
dark_points = [(x, y, z + 0.030) for x, y, z in spiral_points]
create_curve(
    "Integrated dark spiral groove",
    dark_points,
    0.025,
    dark_brown,
    radii=spiral_radii,
    resolution=3
)

# Broad central chamber, intersecting naturally with the shell surface
center_surface = surface_z(CENTER_X, CENTER_Y)

bpy.ops.mesh.primitive_uv_sphere_add(
    segments=96,
    ring_count=48,
    location=(CENTER_X, CENTER_Y, center_surface + 0.035)
)
chamber = bpy.context.object
chamber.name = "Rounded central nautilus chamber"
chamber.scale = (0.55, 0.53, 0.19)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
chamber.data.materials.append(center_ivory)

for polygon in chamber.data.polygons:
    polygon.use_smooth = True

# Organic dark arc near the center instead of mechanical concentric rings
inner_points = []
inner_radii = []
inner_count = 120

for i in range(inner_count):
    u = i / (inner_count - 1)
    angle = -1.85 * math.pi + 1.80 * math.pi * u
    radius = 0.12 * math.exp(math.log(0.43 / 0.12) * u)
    x = CENTER_X + radius * math.cos(angle)
    y = CENTER_Y + radius * math.sin(angle)

    normalized = min(0.998, radius / 0.55)
    z = (
        center_surface + 0.035
        + 0.19 * math.sqrt(max(0.0, 1.0 - normalized * normalized))
        + 0.012
    )

    inner_points.append((x, y, z))
    inner_radii.append(0.45 + 0.35 * u)

create_curve(
    "Central chamber spiral articulation",
    inner_points,
    0.022,
    dark_brown,
    radii=inner_radii,
    resolution=3
)

# Small smooth nucleus
bpy.ops.mesh.primitive_uv_sphere_add(
    segments=48,
    ring_count=24,
    location=(CENTER_X - 0.015, CENTER_Y + 0.005, center_surface + 0.225)
)
nucleus = bpy.context.object
nucleus.name = "Small central nucleus"
nucleus.scale = (0.12, 0.11, 0.055)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
nucleus.data.materials.append(dark_brown)

for polygon in nucleus.data.polygons:
    polygon.use_smooth = True

# Rounded outer lip, without distracting concentric growth rings
rim_points = []
rim_segments = 300

for i in range(rim_segments):
    angle = 2.0 * math.pi * i / rim_segments
    x = RX * 0.991 * math.cos(angle)
    y = RY * 0.991 * math.sin(angle)
    z = surface_z(x, y, 0.008)
    rim_points.append((x, y, z))

create_curve(
    "Smooth rounded outer shell lip",
    rim_points,
    0.037,
    pale_ivory,
    cyclic=True,
    resolution=4
)

# Convert curve ornament to mesh so all visible geometry is finalized
bpy.ops.object.select_all(action='DESELECT')
for obj in list(bpy.context.scene.objects):
    if obj.type == 'CURVE':
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target='MESH')
        obj.select_set(False)

bpy.ops.object.select_all(action='DESELECT')
shell.select_set(True)
bpy.context.view_layer.objects.active = shell