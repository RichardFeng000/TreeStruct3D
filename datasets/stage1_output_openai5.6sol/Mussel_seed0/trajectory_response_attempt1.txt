import bpy
import math

from mathutils import Vector

# Clear the scene completely.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                   bpy.data.cameras, bpy.data.lights):
    if datablocks != bpy.data.materials:
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)

# Materials.
def make_material(name, color, roughness=0.42):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat

materials = [
    make_material("Deep umber", (0.055, 0.018, 0.008), 0.38),
    make_material("Dark brown", (0.120, 0.038, 0.014), 0.40),
    make_material("Chestnut", (0.245, 0.090, 0.032), 0.42),
    make_material("Warm ochre", (0.460, 0.245, 0.095), 0.46),
    make_material("Cream growth rings", (0.760, 0.590, 0.340), 0.48),
    make_material("Dark interior", (0.022, 0.015, 0.014), 0.50),
    make_material("Shell rim", (0.090, 0.032, 0.016), 0.42),
    make_material("Hinge ligament", (0.035, 0.018, 0.012), 0.56),
]

HINGE_Y = -2.8
SHELL_LENGTH = 5.6
SHELL_HALF_WIDTH = 1.16
OPEN_ANGLE = math.radians(8.5)
RING_COUNT = 52
ANGULAR_COUNT = 112
GROWTH_COUNT = 16.0

def boundary_point(theta, scale=1.0):
    # A cardioid-like, elongated teardrop outline with a pointed hinge.
    progress = 0.5 * (1.0 - math.cos(theta))
    asymmetry = 0.93 if math.sin(theta) >= 0.0 else 1.04
    width_factor = 0.78 + 0.22 * progress
    x = scale * SHELL_HALF_WIDTH * math.sin(theta) * width_factor * asymmetry
    y = HINGE_Y + scale * SHELL_LENGTH * progress
    return x, y

def shell_heights(s, theta):
    envelope = math.sin(math.pi * s)
    envelope = max(envelope, 0.0)
    longitudinal_bias = 1.0 + 0.07 * math.cos(theta - math.pi)
    smooth_dome = 0.91 * (envelope ** 0.70) * longitudinal_bias

    phase = (GROWTH_COUNT * s) % 1.0
    ridge_profile = max(math.cos(2.0 * math.pi * phase), 0.0) ** 8
    raised_growth_ring = 0.048 * ridge_profile * (envelope ** 0.42)

    # A small outer edge thickness remains at the lip.
    outer = smooth_dome + raised_growth_ring + 0.055 * s
    # The inside follows the outer curvature at reduced depth, making a cavity.
    inner_groove = 0.012 * math.sin(2.0 * math.pi * GROWTH_COUNT * s)
    inner = 0.70 * smooth_dome - inner_groove * (envelope ** 0.7)
    return outer, inner

def transform_shell_point(x, y, z_unsigned, side):
    # side = +1 upper valve, -1 lower valve.
    z = side * z_unsigned
    angle = side * OPEN_ANGLE
    dy = y - HINGE_Y
    ca = math.cos(angle)
    sa = math.sin(angle)
    wy = HINGE_Y + dy * ca - z * sa
    wz = dy * sa + z * ca
    return (x, wy, wz)

def growth_material(s, angular_index=0):
    cycle = s * GROWTH_COUNT
    phase = cycle - math.floor(cycle)
    growth_number = int(math.floor(cycle))

    if phase < 0.16:
        return 4 if growth_number % 3 != 1 else 3
    if phase < 0.31:
        return 3
    pattern = (growth_number * 5 + angular_index // 28) % 4
    return (1, 2, 2, 0)[pattern]

def create_valve(name, side):
    verts = []
    faces = []
    face_materials = []

    def add_face(indices, material_index, reverse=False):
        if reverse:
            indices = tuple(reversed(indices))
        faces.append(tuple(indices))
        face_materials.append(material_index)

    # Two coincident-at-the-hinge cap vertices allow correct independent normals.
    outer_center = len(verts)
    verts.append(transform_shell_point(0.0, HINGE_Y, 0.0, side))
    inner_center = len(verts)
    verts.append(transform_shell_point(0.0, HINGE_Y, 0.0, side))

    outer_rings = []
    inner_rings = []

    for ring in range(1, RING_COUNT + 1):
        s = ring / RING_COUNT
        outer_indices = []
        inner_indices = []

        for j in range(ANGULAR_COUNT):
            theta = 2.0 * math.pi * j / ANGULAR_COUNT
            x, y = boundary_point(theta, s)
            outer_h, inner_h = shell_heights(s, theta)

            outer_indices.append(len(verts))
            verts.append(transform_shell_point(x, y, outer_h, side))

            inner_indices.append(len(verts))
            verts.append(transform_shell_point(x, y, inner_h, side))

        outer_rings.append(outer_indices)
        inner_rings.append(inner_indices)

    # Central fans.
    first_outer = outer_rings[0]
    first_inner = inner_rings[0]
    center_mat = growth_material(0.01)
    for j in range(ANGULAR_COUNT):
        jn = (j + 1) % ANGULAR_COUNT
        add_face(
            (outer_center, first_outer[j], first_outer[jn]),
            center_mat,
            reverse=(side < 0)
        )
        add_face(
            (inner_center, first_inner[jn], first_inner[j]),
            5,
            reverse=(side < 0)
        )

    # Radial shell bands.
    for ring in range(1, RING_COUNT):
        previous_outer = outer_rings[ring - 1]
        current_outer = outer_rings[ring]
        previous_inner = inner_rings[ring - 1]
        current_inner = inner_rings[ring]
        s_mid = (ring + 0.5) / RING_COUNT

        for j in range(ANGULAR_COUNT):
            jn = (j + 1) % ANGULAR_COUNT
            outer_mat = growth_material(s_mid, j)

            add_face(
                (previous_outer[j], current_outer[j],
                 current_outer[jn], previous_outer[jn]),
                outer_mat,
                reverse=(side < 0)
            )
            add_face(
                (previous_inner[jn], current_inner[jn],
                 current_inner[j], previous_inner[j]),
                5,
                reverse=(side < 0)
            )

    # Thick dark rim joining the outer and inner skins.
    last_outer = outer_rings[-1]
    last_inner = inner_rings[-1]
    for j in range(ANGULAR_COUNT):
        jn = (j + 1) % ANGULAR_COUNT
        add_face(
            (last_outer[j], last_inner[j], last_inner[jn], last_outer[jn]),
            6,
            reverse=(side < 0)
        )

    mesh = bpy.data.meshes.new(name + " Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.clear()
    for mat in materials:
        mesh.materials.append(mat)

    for polygon, mat_index in zip(mesh.polygons, face_materials):
        polygon.material_index = mat_index
        polygon.use_smooth = mat_index != 6

    mesh.validate(verbose=False)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_rim_curve(name, side):
    curve_data = bpy.data.curves.new(name + " Geometry", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 1
    curve_data.bevel_depth = 0.030
    curve_data.bevel_resolution = 3
    curve_data.resolution_u = 1
    curve_data.materials.append(materials[6])

    spline = curve_data.splines.new('POLY')
    spline.points.add(ANGULAR_COUNT - 1)
    spline.use_cyclic_u = True

    for j in range(ANGULAR_COUNT):
        theta = 2.0 * math.pi * j / ANGULAR_COUNT
        x, y = boundary_point(theta, 1.0)
        point = transform_shell_point(x, y, 0.028, side)
        spline.points[j].co = (*point, 1.0)

    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    return obj

upper_valve = create_valve("Upper mussel valve", 1)
lower_valve = create_valve("Lower mussel valve", -1)
upper_rim = create_rim_curve("Upper valve lip", 1)
lower_rim = create_rim_curve("Lower valve lip", -1)

# Compact ligament at the pointed end where both valves meet.
bpy.ops.mesh.primitive_uv_sphere_add(
    segments=32,
    ring_count=16,
    location=(0.0, HINGE_Y + 0.015, 0.0)
)
hinge = bpy.context.object
hinge.name = "Pointed hinge ligament"
hinge.scale = (0.28, 0.15, 0.115)
hinge.data.materials.append(materials[7])
for polygon in hinge.data.polygons:
    polygon.use_smooth = True

# A subtle pair of small hinge lobes reinforces the joined pointed end.
for side in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=24,
        ring_count=12,
        location=(side * 0.16, HINGE_Y + 0.075, side * 0.018)
    )
    lobe = bpy.context.object
    lobe.name = "Hinge lobe"
    lobe.scale = (0.13, 0.19, 0.085)
    lobe.data.materials.append(materials[0])
    for polygon in lobe.data.polygons:
        polygon.use_smooth = True

# Keep the assembly selected and active without adding cameras, lights, or context.
bpy.ops.object.select_all(action='DESELECT')
upper_valve.select_set(True)
lower_valve.select_set(True)
upper_rim.select_set(True)
lower_rim.select_set(True)
hinge.select_set(True)
bpy.context.view_layer.objects.active = upper_valve
