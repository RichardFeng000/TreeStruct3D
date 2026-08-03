import bpy
import math
from mathutils import Vector

# Clear the scene completely.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    if datablocks != bpy.data.materials:
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)

# Materials
def make_material(name, color, roughness=0.6):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Specular IOR Level"].default_value = 0.28
    return mat

cream = make_material("Warm Cream", (0.70, 0.49, 0.27), 0.68)
pale_cream = make_material("Pale Growth Bands", (0.88, 0.72, 0.48), 0.72)
tan = make_material("Golden Tan", (0.48, 0.27, 0.12), 0.72)
brown = make_material("Chestnut Growth Rings", (0.24, 0.105, 0.045), 0.76)
dark_brown = make_material("Dark Hinge Brown", (0.075, 0.028, 0.015), 0.82)
interior = make_material("Dark Interior", (0.18, 0.075, 0.035), 0.74)
interior_highlight = make_material("Interior Rib Highlight", (0.31, 0.14, 0.065), 0.76)

all_shell_materials = [
    cream, pale_cream, tan, brown, dark_brown, interior, interior_highlight
]

R_MIN = 0.30
R_BASE = 3.38
HALF_ANGLE = math.radians(57.0)
Y_SCALE = 1.22
Y_SHIFT = -1.22
RIB_COUNT = 13
NT = 105
NR = 61

def outer_radius(theta):
    q = (theta + HALF_ANGLE) / (2.0 * HALF_ANGLE)
    scallop = 1.0 + 0.026 * math.cos(2.0 * math.pi * RIB_COUNT * q)
    shoulder = 0.965 + 0.035 * math.cos(theta * 1.7)
    return R_BASE * scallop * shoulder

def shell_profile(theta, s, outer=True):
    q = (theta + HALF_ANGLE) / (2.0 * HALF_ANGLE)
    angular_taper = max(0.18, math.cos(theta * 0.72) ** 0.8)
    dome = math.sin(math.pi * s) ** 0.76
    rib_wave = 0.5 + 0.5 * math.cos(2.0 * math.pi * RIB_COUNT * q)
    rib_envelope = math.sin(math.pi * min(1.0, s * 1.08)) ** 0.60
    ring_wave = math.sin(2.0 * math.pi * (10.5 * s + 0.15 * math.sin(theta * 3.0)))
    fine_ring = math.sin(2.0 * math.pi * (21.0 * s + q * 0.35))
    if outer:
        return (
            0.075
            + 0.49 * dome * angular_taper
            + 0.085 * rib_wave * rib_envelope
            + 0.018 * ring_wave * (0.25 + 0.75 * s)
            + 0.008 * fine_ring * s
        )
    return (
        0.025
        + 0.315 * dome * angular_taper
        + 0.027 * rib_wave * rib_envelope
        + 0.006 * ring_wave * s
    )

def transform_point(x, y, z, angle):
    ca = math.cos(angle)
    sa = math.sin(angle)
    return Vector((x, y * ca - z * sa + Y_SHIFT, y * sa + z * ca))

def local_point(theta, s, sign, outer=True):
    rout = outer_radius(theta)
    r = R_MIN + s * (rout - R_MIN)
    x = r * math.sin(theta)
    y = Y_SCALE * (r * math.cos(theta) - R_MIN)
    h = shell_profile(theta, s, outer)
    z = sign * h
    return x, y, z

def outer_material_index(s, theta):
    q = (theta + HALF_ANGLE) / (2.0 * HALF_ANGLE)
    ring_signal = math.sin(
        2.0 * math.pi * (8.8 * s + 0.12 * math.sin(theta * 3.2) + 0.05 * math.sin(q * 17.0))
    )
    fine_signal = math.sin(2.0 * math.pi * (18.0 * s + q * 0.4))
    rib_signal = 0.5 + 0.5 * math.cos(2.0 * math.pi * RIB_COUNT * q)

    if ring_signal > 0.78 or fine_signal > 0.94:
        return 3
    if ring_signal < -0.70:
        return 1
    if rib_signal > 0.82:
        return 2
    return 0

def create_valve(name, sign, opening_angle):
    verts = []
    faces = []
    material_ids = []

    # Outer and inner gridded surfaces.
    for outer in (True, False):
        for ir in range(NR):
            s = ir / (NR - 1)
            for it in range(NT):
                theta = -HALF_ANGLE + (2.0 * HALF_ANGLE * it / (NT - 1))
                x, y, z = local_point(theta, s, sign, outer)
                verts.append(tuple(transform_point(x, y, z, opening_angle)))

    layer_size = NR * NT

    # Outer surface.
    for ir in range(NR - 1):
        s_mid = (ir + 0.5) / (NR - 1)
        for it in range(NT - 1):
            theta_mid = -HALF_ANGLE + 2.0 * HALF_ANGLE * (it + 0.5) / (NT - 1)
            a = ir * NT + it
            b = a + 1
            c = a + NT + 1
            d = a + NT
            if sign > 0:
                faces.append((a, b, c, d))
            else:
                faces.append((a, d, c, b))
            material_ids.append(outer_material_index(s_mid, theta_mid))

    # Inner surface, with reversed winding.
    for ir in range(NR - 1):
        s_mid = (ir + 0.5) / (NR - 1)
        for it in range(NT - 1):
            theta_mid = -HALF_ANGLE + 2.0 * HALF_ANGLE * (it + 0.5) / (NT - 1)
            a = layer_size + ir * NT + it
            b = a + 1
            c = a + NT + 1
            d = a + NT
            if sign > 0:
                faces.append((a, d, c, b))
            else:
                faces.append((a, b, c, d))
            q = (theta_mid + HALF_ANGLE) / (2.0 * HALF_ANGLE)
            rib = math.cos(2.0 * math.pi * RIB_COUNT * q)
            material_ids.append(6 if rib > 0.72 and s_mid > 0.14 else 5)

    # Broad outer rim.
    ir = NR - 1
    for it in range(NT - 1):
        oa = ir * NT + it
        ob = oa + 1
        ia = layer_size + ir * NT + it
        ib = ia + 1
        faces.append((oa, ia, ib, ob))
        material_ids.append(3 if (it // 4) % 3 == 0 else 2)

    # Narrow hinge edge.
    ir = 0
    for it in range(NT - 1):
        oa = ir * NT + it
        ob = oa + 1
        ia = layer_size + ir * NT + it
        ib = ia + 1
        faces.append((oa, ob, ib, ia))
        material_ids.append(4)

    # Side edges of the fan.
    for it in (0, NT - 1):
        for ir in range(NR - 1):
            oa = ir * NT + it
            ob = (ir + 1) * NT + it
            ia = layer_size + ir * NT + it
            ib = layer_size + (ir + 1) * NT + it
            if it == 0:
                faces.append((oa, ia, ib, ob))
            else:
                faces.append((oa, ob, ib, ia))
            material_ids.append(3 if ir % 8 < 2 else 2)

    mesh = bpy.data.meshes.new(name + " Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.clear()
    for mat in all_shell_materials:
        mesh.materials.append(mat)

    for poly, mat_id in zip(mesh.polygons, material_ids):
        poly.material_index = mat_id
        poly.use_smooth = True

    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bevel = obj.modifiers.new("Softened Shell Edges", 'BEVEL')
    bevel.width = 0.012
    bevel.segments = 2
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = math.radians(42.0)

    return obj

def create_curve(name, points, material, bevel_depth, bevel_resolution=2):
    curve_data = bpy.data.curves.new(name + " Curve", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 1
    curve_data.bevel_depth = bevel_depth
    curve_data.bevel_resolution = bevel_resolution
    curve_data.resolution_u = 1
    curve_data.materials.append(material)

    spline = curve_data.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (co.x, co.y, co.z, 1.0)

    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    return obj

def add_growth_rings(prefix, sign, opening_angle):
    ring_positions = (0.18, 0.265, 0.35, 0.44, 0.535, 0.63, 0.725, 0.82, 0.905)
    for idx, s in enumerate(ring_positions):
        points = []
        for i in range(79):
            theta = -HALF_ANGLE + 2.0 * HALF_ANGLE * i / 78.0
            x, y, z = local_point(theta, s, sign, True)
            z += sign * (0.014 + 0.006 * (idx % 2))
            points.append(transform_point(x, y, z, opening_angle))
        mat = brown if idx % 3 != 1 else pale_cream
        depth = 0.018 if idx < 7 else 0.025
        create_curve(prefix + " Growth Ring %02d" % idx, points, mat, depth, 2)

    # Raised outer lip following the scalloped margin.
    lip_points = []
    for i in range(101):
        theta = -HALF_ANGLE + 2.0 * HALF_ANGLE * i / 100.0
        x, y, z = local_point(theta, 1.0, sign, True)
        z += sign * 0.018
        lip_points.append(transform_point(x, y, z, opening_angle))
    create_curve(prefix + " Scalloped Outer Lip", lip_points, brown, 0.045, 3)

def add_radial_crest_accents(prefix, sign, opening_angle):
    for rib_index in range(1, RIB_COUNT - 1, 2):
        q = rib_index / (RIB_COUNT - 1)
        theta = -HALF_ANGLE + 2.0 * HALF_ANGLE * q
        points = []
        for i in range(35):
            s = 0.12 + 0.82 * i / 34.0
            x, y, z = local_point(theta, s, sign, True)
            z += sign * 0.011
            points.append(transform_point(x, y, z, opening_angle))
        create_curve(prefix + " Radial Rib Accent %02d" % rib_index, points, tan, 0.012, 1)

upper_angle = math.radians(31.0)
lower_angle = math.radians(-15.0)

upper = create_valve("Upper Fan Valve", 1.0, upper_angle)
lower = create_valve("Lower Fan Valve", -1.0, lower_angle)

add_growth_rings("Upper", 1.0, upper_angle)
add_growth_rings("Lower", -1.0, lower_angle)
add_radial_crest_accents("Upper", 1.0, upper_angle)
add_radial_crest_accents("Lower", -1.0, lower_angle)

# Central dark hinge ligament.
bpy.ops.mesh.primitive_cylinder_add(
    vertices=48,
    radius=0.115,
    depth=1.42,
    location=(0.0, Y_SHIFT - 0.025, 0.0),
    rotation=(0.0, math.pi / 2.0, 0.0)
)
hinge = bpy.context.object
hinge.name = "Dark Central Hinge Ligament"
hinge.data.materials.append(dark_brown)
for poly in hinge.data.polygons:
    poly.use_smooth = True

# Shell-colored hinge collars on either side.
for x, length, mat, name in (
    (-0.75, 0.34, brown, "Left Hinge Collar"),
    (0.75, 0.34, brown, "Right Hinge Collar"),
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=40,
        radius=0.145,
        depth=length,
        location=(x, Y_SHIFT - 0.022, 0.0),
        rotation=(0.0, math.pi / 2.0, 0.0)
    )
    collar = bpy.context.object
    collar.name = name
    collar.data.materials.append(mat)
    for poly in collar.data.polygons:
        poly.use_smooth = True

# Small paired hinge plates connecting the ligament visually to each valve.
for sign, angle, label in ((1.0, upper_angle, "Upper"), (-1.0, lower_angle, "Lower")):
    for x in (-0.47, 0.47):
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=32,
            ring_count=16,
            location=(x, Y_SHIFT + 0.015 * math.cos(angle), 0.015 * sign),
            scale=(0.29, 0.18, 0.105)
        )
        plate = bpy.context.object
        plate.name = label + " Hinge Knuckle"
        plate.rotation_euler.x = angle
        plate.data.materials.append(tan if sign > 0 else brown)
        for poly in plate.data.polygons:
            poly.use_smooth = True

# Set a coherent selection and active object without adding cameras, lights, or scenery.
bpy.ops.object.select_all(action='DESELECT')
upper.select_set(True)
lower.select_set(True)
bpy.context.view_layer.objects.active = upper
bpy.context.scene.world.color = (0.025, 0.018, 0.014)