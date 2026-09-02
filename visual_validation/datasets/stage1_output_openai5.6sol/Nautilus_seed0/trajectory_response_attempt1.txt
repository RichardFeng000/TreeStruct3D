import bpy
import math
import random
from mathutils import Vector

# Clear the scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    for datablock in list(datablocks):
        if datablock.users == 0:
            datablocks.remove(datablock)

random.seed(12)

# Shell dimensions and coil center.
RX = 3.50
RY = 3.18
THICKNESS = 0.76
COIL_X = -0.46
COIL_Y = 0.0

def make_material(name, color, roughness=0.55):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = 0.0
    return mat

cream = make_material("Warm ivory shell", (0.79, 0.64, 0.39), 0.48)
cream_light = make_material("Raised cream highlights", (0.96, 0.83, 0.57), 0.43)
cream_pale = make_material("Central chamber ivory", (0.91, 0.75, 0.48), 0.46)
brown_dark = make_material("Deep brown spiral", (0.16, 0.055, 0.020), 0.58)
brown = make_material("Chestnut stripes", (0.34, 0.105, 0.035), 0.59)
brown_mid = make_material("Warm brown stripes", (0.47, 0.175, 0.055), 0.57)
brown_light = make_material("Ochre brown stripes", (0.57, 0.265, 0.085), 0.55)

def shell_z(x, y, offset=0.0):
    q = (x / RX) ** 2 + (y / RY) ** 2
    return THICKNESS * math.sqrt(max(0.0, 1.0 - q)) + offset

def ray_boundary_distance(angle):
    dx = math.cos(angle)
    dy = math.sin(angle)
    a = (dx * dx) / (RX * RX) + (dy * dy) / (RY * RY)
    b = 2.0 * ((COIL_X * dx) / (RX * RX) + (COIL_Y * dy) / (RY * RY))
    c = (COIL_X * COIL_X) / (RX * RX) + (COIL_Y * COIL_Y) / (RY * RY) - 1.0
    return (-b + math.sqrt(max(0.0, b * b - 4.0 * a * c))) / (2.0 * a)

def add_poly_curve(name, points, bevel_depth, material, cyclic=False, radii=None, bevel_resolution=3):
    curve_data = bpy.data.curves.new(name, 'CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 2
    curve_data.bevel_depth = bevel_depth
    curve_data.bevel_resolution = bevel_resolution
    curve_data.resolution_u = 2
    spline = curve_data.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for i, point in enumerate(points):
        spline.points[i].co = (point[0], point[1], point[2], 1.0)
        if radii is not None:
            spline.points[i].radius = radii[i]
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

# Main smooth, flattened shell body.
bpy.ops.mesh.primitive_uv_sphere_add(
    segments=144,
    ring_count=72,
    location=(0.0, 0.0, 0.0)
)
shell = bpy.context.object
shell.name = "Rounded planispiral shell body"
shell.scale = (RX, RY, THICKNESS)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
shell.data.materials.append(cream)
for poly in shell.data.polygons:
    poly.use_smooth = True

# Wavy radial brown bands laid directly over the front and back shell surfaces.
stripe_vertices = []
stripe_faces = []
stripe_material_indices = []
stripe_count = 29
steps = 42
stripe_materials = [brown, brown_mid, brown_light]

for stripe_index in range(stripe_count):
    base_angle = (2.0 * math.pi * stripe_index / stripe_count) + 0.018 * math.sin(stripe_index * 2.7)
    phase = random.uniform(0.0, 2.0 * math.pi)
    curl = random.uniform(-0.14, 0.14)
    wave_amp = random.uniform(0.028, 0.075)
    width_scale = random.uniform(0.82, 1.22)
    front_start = len(stripe_vertices)

    for j in range(steps):
        s = 0.095 + (0.892 * j / (steps - 1))
        center_angle = (
            base_angle
            + curl * (1.0 - s) ** 1.55
            + wave_amp * math.sin(3.2 * math.pi * s + phase) * (0.40 + 0.60 * s)
            + 0.015 * math.sin(9.0 * math.pi * s + phase * 0.7)
        )
        edge_flutter = 1.0 + 0.18 * math.sin(5.0 * math.pi * s + phase)
        half_width = 0.034 * width_scale * edge_flutter * (0.72 + 0.28 * s)

        for side in (-1.0, 1.0):
            edge_angle = center_angle + side * half_width
            radius = ray_boundary_distance(edge_angle) * s
            x = COIL_X + radius * math.cos(edge_angle)
            y = COIL_Y + radius * math.sin(edge_angle)
            z = shell_z(x, y, 0.018 + 0.010 * s)
            stripe_vertices.append((x, y, z))

    for j in range(steps - 1):
        a = front_start + j * 2
        stripe_faces.append((a, a + 1, a + 3, a + 2))
        stripe_material_indices.append(stripe_index % len(stripe_materials))

    # Matching markings on the reverse face make the shell coherent from all sides.
    back_start = len(stripe_vertices)
    for j in range(steps):
        s = 0.095 + (0.892 * j / (steps - 1))
        center_angle = (
            base_angle
            + curl * (1.0 - s) ** 1.55
            + wave_amp * math.sin(3.2 * math.pi * s + phase) * (0.40 + 0.60 * s)
            + 0.015 * math.sin(9.0 * math.pi * s + phase * 0.7)
        )
        edge_flutter = 1.0 + 0.18 * math.sin(5.0 * math.pi * s + phase)
        half_width = 0.034 * width_scale * edge_flutter * (0.72 + 0.28 * s)
        for side in (1.0, -1.0):
            edge_angle = center_angle + side * half_width
            radius = ray_boundary_distance(edge_angle) * s
            x = COIL_X + radius * math.cos(edge_angle)
            y = COIL_Y + radius * math.sin(edge_angle)
            z = -shell_z(x, y, 0.018 + 0.010 * s)
            stripe_vertices.append((x, y, z))

    for j in range(steps - 1):
        a = back_start + j * 2
        stripe_faces.append((a, a + 1, a + 3, a + 2))
        stripe_material_indices.append(stripe_index % len(stripe_materials))

stripe_mesh = bpy.data.meshes.new("Wavy radiating stripe geometry")
stripe_mesh.from_pydata(stripe_vertices, [], stripe_faces)
stripe_mesh.update()
stripes = bpy.data.objects.new("Wavy brown and cream radiating pattern", stripe_mesh)
bpy.context.collection.objects.link(stripes)
for material in stripe_materials:
    stripes.data.materials.append(material)
for polygon, material_index in zip(stripes.data.polygons, stripe_material_indices):
    polygon.material_index = material_index
    polygon.use_smooth = True

# Main logarithmic spiral seam, emphasizing the inward-curving whorls.
spiral_points = []
spiral_radii = []
spiral_steps = 260
theta_start = -5.0 * math.pi
theta_end = 0.0
r_start = 0.105
r_end = 3.72
growth = math.log(r_end / r_start)

for i in range(spiral_steps):
    u = i / (spiral_steps - 1)
    theta = theta_start + (theta_end - theta_start) * u
    radius = r_start * math.exp(growth * u)
    x = COIL_X + radius * math.cos(theta)
    y = COIL_Y + radius * math.sin(theta)
    q = (x / RX) ** 2 + (y / RY) ** 2
    if q >= 0.997:
        break
    z = shell_z(x, y, 0.043)
    spiral_points.append((x, y, z))
    spiral_radii.append(0.55 + 1.20 * u)

spiral = add_poly_curve(
    "Deep continuous planispiral seam",
    spiral_points,
    0.040,
    brown_dark,
    cyclic=False,
    radii=spiral_radii,
    bevel_resolution=4
)

# Pale ridge beside the dark spiral gives the coil a rounded, layered edge.
highlight_points = []
highlight_radii = []
for i, point in enumerate(spiral_points):
    u = i / max(1, len(spiral_points) - 1)
    theta = theta_start + (theta_end - theta_start) * u
    radius = r_start * math.exp(growth * u)
    offset_angle = 0.018 + 0.010 * u
    x = COIL_X + radius * math.cos(theta + offset_angle)
    y = COIL_Y + radius * math.sin(theta + offset_angle)
    if (x / RX) ** 2 + (y / RY) ** 2 >= 0.995:
        break
    z = shell_z(x, y, 0.074)
    highlight_points.append((x, y, z))
    highlight_radii.append(0.45 + 0.75 * u)

add_poly_curve(
    "Cream highlight along spiral whorl",
    highlight_points,
    0.018,
    cream_light,
    radii=highlight_radii,
    bevel_resolution=3
)

# Rounded central chamber boss.
central_surface_z = shell_z(COIL_X, COIL_Y)
bpy.ops.mesh.primitive_uv_sphere_add(
    segments=72,
    ring_count=36,
    location=(COIL_X, COIL_Y, central_surface_z + 0.030)
)
chamber = bpy.context.object
chamber.name = "Rounded central chamber"
chamber.scale = (0.455, 0.455, 0.145)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
chamber.data.materials.append(cream_pale)
for poly in chamber.data.polygons:
    poly.use_smooth = True

# Concentric brown articulation around the central chamber.
for ring_radius, ring_depth, ring_material in (
    (0.370, 0.026, brown_dark),
    (0.215, 0.018, brown_mid),
):
    ring_points = []
    ring_segments = 96
    dome_z = central_surface_z + 0.030
    dome_rx = 0.455
    dome_rz = 0.145
    normalized = min(0.999, ring_radius / dome_rx)
    z = dome_z + dome_rz * math.sqrt(max(0.0, 1.0 - normalized * normalized)) + 0.012
    for i in range(ring_segments):
        angle = 2.0 * math.pi * i / ring_segments
        ring_points.append((
            COIL_X + ring_radius * math.cos(angle),
            COIL_Y + ring_radius * math.sin(angle),
            z
        ))
    add_poly_curve(
        "Central chamber ring",
        ring_points,
        ring_depth,
        ring_material,
        cyclic=True,
        bevel_resolution=3
    )

# Small domed nucleus at the exact spiral center.
bpy.ops.mesh.primitive_uv_sphere_add(
    segments=48,
    ring_count=24,
    location=(COIL_X, COIL_Y, central_surface_z + 0.183)
)
nucleus = bpy.context.object
nucleus.name = "Central spiral nucleus"
nucleus.scale = (0.105, 0.105, 0.045)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
nucleus.data.materials.append(brown_dark)
for poly in nucleus.data.polygons:
    poly.use_smooth = True

# A subtle rounded ivory rim near the outer boundary.
rim_points = []
rim_segments = 240
rim_fraction = 0.988
for i in range(rim_segments):
    angle = 2.0 * math.pi * i / rim_segments
    x = RX * rim_fraction * math.cos(angle)
    y = RY * rim_fraction * math.sin(angle)
    z = shell_z(x, y, 0.018)
    rim_points.append((x, y, z))
add_poly_curve(
    "Rounded outer shell lip",
    rim_points,
    0.030,
    cream_light,
    cyclic=True,
    bevel_resolution=4
)

# A few delicate growth ridges provide physical shell texture without obscuring the stripes.
for fraction in (0.79, 0.86, 0.925):
    ridge_points = []
    segments = 220
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        x = RX * fraction * math.cos(angle)
        y = RY * fraction * math.sin(angle)
        z = shell_z(x, y, 0.031)
        ridge_points.append((x, y, z))
    add_poly_curve(
        "Subtle concentric growth ridge",
        ridge_points,
        0.009,
        cream_light,
        cyclic=True,
        bevel_resolution=2
    )

# Keep the assembly centered at the origin and select the primary shell.
bpy.ops.object.select_all(action='DESELECT')
shell.select_set(True)
bpy.context.view_layer.objects.active = shell
