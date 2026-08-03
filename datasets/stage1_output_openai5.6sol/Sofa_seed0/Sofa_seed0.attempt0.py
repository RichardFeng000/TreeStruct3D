import bpy
import math

from mathutils import Vector

# Clear the scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    for datablock in list(datablocks):
        if datablock.users == 0:
            datablocks.remove(datablock)


def make_material(name, color, roughness=0.7):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
    return material


upholstery = make_material("Warm Gray Upholstery", (0.42, 0.39, 0.35), 0.88)
upholstery_dark = make_material("Upholstery Seams", (0.25, 0.23, 0.21), 0.92)
shadow_fabric = make_material("Recessed Fabric", (0.31, 0.29, 0.26), 0.9)
feet_material = make_material("Dark Feet", (0.055, 0.045, 0.038), 0.55)


def add_rounded_box(name, location, dimensions, bevel, material,
                    rotation=(0.0, 0.0, 0.0), segments=5, smooth=True):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    modifier = obj.modifiers.new(name="Soft edge bevel", type='BEVEL')
    modifier.width = bevel
    modifier.segments = segments
    modifier.limit_method = 'ANGLE'
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    if smooth:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True

    if material:
        obj.data.materials.append(material)
    return obj


def rounded_rectangle_points(width, height, radius, steps=7):
    radius = min(radius, width * 0.5, height * 0.5)
    hx = width * 0.5
    hy = height * 0.5
    corners = (
        (hx - radius, hy - radius, 0.0),
        (-hx + radius, hy - radius, 90.0),
        (-hx + radius, -hy + radius, 180.0),
        (hx - radius, -hy + radius, 270.0),
    )
    points = []
    for cx, cy, start_angle in corners:
        for step in range(steps):
            angle = math.radians(start_angle + 90.0 * step / steps)
            points.append((cx + radius * math.cos(angle),
                           cy + radius * math.sin(angle)))
    return points


def add_xy_piping(name, location, width, depth, radius, tube_radius,
                  material, rotation=(0.0, 0.0, 0.0)):
    curve = bpy.data.curves.new(name + " Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_depth = tube_radius
    curve.bevel_resolution = 2
    curve.resolution_u = 2

    points = rounded_rectangle_points(width, depth, radius, 8)
    spline = curve.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for index, (x, y) in enumerate(points):
        spline.points[index].co = (x, y, 0.0, 1.0)
    spline.use_cyclic_u = True

    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    return obj


def add_xz_piping(name, location, width, height, radius, tube_radius,
                  front_offset, material, rotation=(0.0, 0.0, 0.0)):
    curve = bpy.data.curves.new(name + " Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_depth = tube_radius
    curve.bevel_resolution = 2

    points = rounded_rectangle_points(width, height, radius, 8)
    spline = curve.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for index, (x, z) in enumerate(points):
        spline.points[index].co = (x, front_offset, z, 1.0)
    spline.use_cyclic_u = True

    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    return obj


# Low structural bases forming the L-shaped sectional footprint.
add_rounded_box(
    "Main Sofa Base",
    (0.0, 0.35, 0.40),
    (7.20, 1.72, 0.48),
    0.12,
    upholstery,
    segments=6
)

add_rounded_box(
    "Chaise Extension Base",
    (2.45, -0.48, 0.40),
    (1.72, 3.38, 0.48),
    0.12,
    upholstery,
    segments=6
)

# Subtle recessed lower aprons.
add_rounded_box(
    "Main Front Recess",
    (-0.82, -0.485, 0.39),
    (4.88, 0.055, 0.25),
    0.025,
    shadow_fabric,
    segments=3
)

add_rounded_box(
    "Chaise Front Recess",
    (2.45, -2.145, 0.39),
    (1.42, 0.055, 0.25),
    0.025,
    shadow_fabric,
    segments=3
)

# Back support rail behind the padded back segments.
add_rounded_box(
    "Back Support Rail",
    (0.0, 1.125, 1.10),
    (6.85, 0.34, 1.14),
    0.12,
    upholstery,
    rotation=(math.radians(-3.0), 0.0, 0.0),
    segments=6
)

# Individual standard seat cushions.
seat_specs = (
    ("Left Seat Cushion", -2.45),
    ("Center Left Seat Cushion", -0.82),
    ("Center Right Seat Cushion", 0.82),
)

for name, x_position in seat_specs:
    cushion = add_rounded_box(
        name,
        (x_position, 0.245, 0.755),
        (1.50, 1.28, 0.34),
        0.14,
        upholstery,
        segments=7
    )
    add_xy_piping(
        name + " Top Piping",
        (x_position, 0.245, 0.934),
        1.34,
        1.12,
        0.13,
        0.017,
        upholstery_dark
    )

# Long chaise cushion extending toward the viewer.
add_rounded_box(
    "Chaise Lounge Cushion",
    (2.45, -0.49, 0.755),
    (1.50, 2.88, 0.34),
    0.15,
    upholstery,
    segments=7
)

add_xy_piping(
    "Chaise Cushion Top Piping",
    (2.45, -0.49, 0.934),
    1.34,
    2.70,
    0.14,
    0.018,
    upholstery_dark
)

# A transverse chaise seam gives the extension a tailored upholstered break.
add_rounded_box(
    "Chaise Transverse Seam",
    (2.45, -0.62, 0.935),
    (1.27, 0.026, 0.027),
    0.012,
    upholstery_dark,
    segments=3
)

# Back cushions with subtly varied heights.
back_specs = (
    ("Left Back Cushion", -2.45, 1.23, 0.00),
    ("Center Left Back Cushion", -0.82, 1.41, -0.015),
    ("Center Right Back Cushion", 0.82, 1.29, 0.01),
    ("Chaise Back Cushion", 2.45, 1.47, -0.01),
)

back_tilt = math.radians(-6.0)

for name, x_position, height, z_adjustment in back_specs:
    center_z = 0.91 + height * 0.5 + z_adjustment
    center_y = 1.015
    add_rounded_box(
        name,
        (x_position, center_y, center_z),
        (1.50, 0.39, height),
        0.16,
        upholstery,
        rotation=(back_tilt, 0.0, 0.0),
        segments=7
    )
    add_xz_piping(
        name + " Face Piping",
        (x_position, center_y, center_z),
        1.32,
        height - 0.18,
        0.13,
        0.016,
        -0.212,
        upholstery_dark,
        rotation=(back_tilt, 0.0, 0.0)
    )

# Solid arm at the conventional sofa end.
add_rounded_box(
    "Left Solid Armrest",
    (-3.53, 0.28, 0.89),
    (0.54, 1.78, 1.18),
    0.16,
    upholstery,
    segments=7
)

add_xy_piping(
    "Left Armrest Top Piping",
    (-3.53, 0.28, 1.492),
    0.39,
    1.56,
    0.11,
    0.017,
    upholstery_dark
)

# Solid arm running alongside the outside edge of the chaise.
add_rounded_box(
    "Right Chaise Armrest",
    (3.53, -0.46, 0.89),
    (0.54, 3.42, 1.18),
    0.16,
    upholstery,
    segments=7
)

add_xy_piping(
    "Right Chaise Armrest Top Piping",
    (3.53, -0.46, 1.492),
    0.39,
    3.18,
    0.11,
    0.017,
    upholstery_dark
)

# Small block feet, recessed beneath the upholstered bases.
foot_locations = (
    (-3.24, 1.00),
    (-3.24, -0.28),
    (1.55, 1.00),
    (3.24, 1.00),
    (3.24, -1.78),
    (1.72, -1.78),
    (-0.25, 1.00),
    (-0.25, -0.28),
)

for index, (x_position, y_position) in enumerate(foot_locations, 1):
    add_rounded_box(
        "Recessed Foot %02d" % index,
        (x_position, y_position, 0.10),
        (0.30, 0.30, 0.20),
        0.035,
        feet_material,
        segments=3,
        smooth=False
    )

# Add shallow cushion-bottom shadow gaps as physical inset strips.
for index, x_position in enumerate((-2.45, -0.82, 0.82), 1):
    add_rounded_box(
        "Seat Gap %02d" % index,
        (x_position, 0.90, 0.688),
        (1.32, 0.045, 0.065),
        0.018,
        shadow_fabric,
        segments=3
    )

add_rounded_box(
    "Chaise Cushion Rear Gap",
    (2.45, 0.91, 0.688),
    (1.31, 0.045, 0.065),
    0.018,
    shadow_fabric,
    segments=3
)

# Set every object selectable and leave the assembly centered near the origin.
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type in {'MESH', 'CURVE'}:
        obj.select_set(True)

bpy.context.view_layer.update()