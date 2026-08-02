import bpy
import math
from mathutils import Vector

# Clear the default scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    if datablocks not in (bpy.data.materials,):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)

# Create a dedicated collection for the staircase assembly.
assembly = bpy.data.collections.new("U_Shaped_Staircase")
bpy.context.scene.collection.children.link(assembly)


def move_to_assembly(obj):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    assembly.objects.link(obj)


def make_material(name, color, metallic=0.0, roughness=0.4, transmission=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (color[0], color[1], color[2], alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], alpha)
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = transmission
        elif "Transmission" in bsdf.inputs:
            bsdf.inputs["Transmission"].default_value = transmission
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = 1.48
    if alpha < 1.0:
        try:
            mat.surface_render_method = 'DITHERED'
        except Exception:
            pass
        mat.use_transparency_overlap = False
    return mat


navy = make_material(
    "Dark Navy Purple Structure",
    (0.035, 0.025, 0.105),
    metallic=0.55,
    roughness=0.24
)
tread_mat = make_material(
    "Deep Purple Stair Treads",
    (0.075, 0.045, 0.145),
    metallic=0.32,
    roughness=0.30
)
edge_mat = make_material(
    "Rail Edge Highlights",
    (0.105, 0.060, 0.180),
    metallic=0.60,
    roughness=0.20
)
glass = make_material(
    "Brown Tinted Transparent Glass",
    (0.30, 0.145, 0.065),
    metallic=0.0,
    roughness=0.12,
    transmission=0.78,
    alpha=0.34
)


def add_box(name, location, dimensions, material, bevel=0.0, bevel_segments=2):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_assembly(obj)
    if material:
        obj.data.materials.append(material)
    if bevel > 0.0:
        mod = obj.modifiers.new("Softened Edges", 'BEVEL')
        mod.width = bevel
        mod.segments = bevel_segments
        mod.limit_method = 'ANGLE'
    return obj


def add_beam(name, start, end, width, depth, material, bevel=0.0):
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    length = direction.length
    midpoint = (start + end) * 0.5
    obj = add_box(name, midpoint, (width, depth, length), material, bevel, 2)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = direction.to_track_quat('Z', 'Y')
    return obj


def add_vertical_post(name, x, y, z_bottom, z_top, size=0.065):
    return add_box(
        name,
        (x, y, (z_bottom + z_top) * 0.5),
        (size, size, z_top - z_bottom),
        navy,
        bevel=0.008,
        bevel_segments=2
    )


def add_sloped_glass(name, x, y0, y1, bottom0, bottom1, panel_height, thickness=0.032):
    xa = x - thickness * 0.5
    xb = x + thickness * 0.5
    top0 = bottom0 + panel_height
    top1 = bottom1 + panel_height
    verts = [
        (xa, y0, bottom0), (xa, y1, bottom1),
        (xa, y1, top1), (xa, y0, top0),
        (xb, y0, bottom0), (xb, y1, bottom1),
        (xb, y1, top1), (xb, y0, top0)
    ]
    faces = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (3, 7, 6, 2),
        (1, 2, 6, 5),
        (0, 4, 7, 3)
    ]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    assembly.objects.link(obj)
    obj.data.materials.append(glass)
    bevel = obj.modifiers.new("Glass Edge Softening", 'BEVEL')
    bevel.width = 0.006
    bevel.segments = 2
    return obj


def add_horizontal_glass_x(name, x0, x1, y, z_bottom, height, thickness=0.032):
    return add_box(
        name,
        ((x0 + x1) * 0.5, y, z_bottom + height * 0.5),
        (x1 - x0, thickness, height),
        glass,
        bevel=0.008,
        bevel_segments=2
    )


def add_horizontal_glass_y(name, x, y0, y1, z_bottom, height, thickness=0.032):
    return add_box(
        name,
        (x, (y0 + y1) * 0.5, z_bottom + height * 0.5),
        (thickness, y1 - y0, height),
        glass,
        bevel=0.008,
        bevel_segments=2
    )


# Main staircase dimensions.
flight_width = 1.18
gap = 0.28
left_center = -(gap * 0.5 + flight_width * 0.5)
right_center = gap * 0.5 + flight_width * 0.5
left_outer = left_center - flight_width * 0.5
left_inner = left_center + flight_width * 0.5
right_inner = right_center - flight_width * 0.5
right_outer = right_center + flight_width * 0.5

front_y = -2.05
landing_front = 0.95
landing_back = 2.18
step_count = 11
tread_run = (landing_front - front_y) / step_count
rise = 0.18
landing_z = step_count * rise
slab_thickness = 0.14
tread_thickness = 0.095
nosing = 0.028

# First flight, rising toward the rear landing.
for i in range(step_count):
    y0 = front_y + i * tread_run
    y1 = front_y + (i + 1) * tread_run
    top_z = (i + 1) * rise
    add_box(
        "Lower Flight Tread %02d" % (i + 1),
        (left_center, (y0 + y1) * 0.5 - nosing * 0.5, top_z - tread_thickness * 0.5),
        (flight_width, tread_run + nosing, tread_thickness),
        tread_mat,
        bevel=0.015,
        bevel_segments=2
    )
    # Slim front fascia emphasizes each tread while retaining an open-riser appearance.
    add_box(
        "Lower Flight Nosing %02d" % (i + 1),
        (left_center, y0 - nosing * 0.45, top_z - 0.055),
        (flight_width + 0.025, 0.045, 0.11),
        edge_mat,
        bevel=0.01,
        bevel_segments=2
    )

# Second flight, rising from the landing back toward the front.
for i in range(step_count):
    y_high = landing_front - i * tread_run
    y_low = landing_front - (i + 1) * tread_run
    top_z = landing_z + (i + 1) * rise
    add_box(
        "Upper Flight Tread %02d" % (i + 1),
        (right_center, (y_low + y_high) * 0.5 + nosing * 0.5, top_z - tread_thickness * 0.5),
        (flight_width, tread_run + nosing, tread_thickness),
        tread_mat,
        bevel=0.015,
        bevel_segments=2
    )
    add_box(
        "Upper Flight Nosing %02d" % (i + 1),
        (right_center, y_high + nosing * 0.45, top_z - 0.055),
        (flight_width + 0.025, 0.045, 0.11),
        edge_mat,
        bevel=0.01,
        bevel_segments=2
    )

# Intermediate landing slab.
landing_center_x = (left_outer + right_outer) * 0.5
landing_width = right_outer - left_outer
add_box(
    "Intermediate Landing",
    (landing_center_x, (landing_front + landing_back) * 0.5, landing_z - slab_thickness * 0.5),
    (landing_width, landing_back - landing_front, slab_thickness),
    tread_mat,
    bevel=0.025,
    bevel_segments=3
)

# Landing perimeter frame beams.
beam_h = 0.20
add_box(
    "Landing Front Cross Beam",
    (landing_center_x, landing_front + 0.07, landing_z - slab_thickness - beam_h * 0.5),
    (landing_width + 0.10, 0.15, beam_h),
    navy,
    bevel=0.015
)
add_box(
    "Landing Rear Cross Beam",
    (landing_center_x, landing_back - 0.07, landing_z - slab_thickness - beam_h * 0.5),
    (landing_width + 0.10, 0.15, beam_h),
    navy,
    bevel=0.015
)
for x in (left_outer + 0.07, right_outer - 0.07):
    add_box(
        "Landing Side Beam",
        (x, (landing_front + landing_back) * 0.5, landing_z - slab_thickness - beam_h * 0.5),
        (0.15, landing_back - landing_front, beam_h),
        navy,
        bevel=0.015
    )

# Paired structural stringers under each flight.
stringer_x_positions_1 = (left_outer + 0.12, left_inner - 0.12)
for index, x in enumerate(stringer_x_positions_1):
    add_beam(
        "Lower Flight Stringer %d" % (index + 1),
        (x, front_y + 0.08, 0.01),
        (x, landing_front - 0.08, landing_z - 0.18),
        0.16,
        0.23,
        navy,
        bevel=0.018
    )

stringer_x_positions_2 = (right_inner + 0.12, right_outer - 0.12)
for index, x in enumerate(stringer_x_positions_2):
    add_beam(
        "Upper Flight Stringer %d" % (index + 1),
        (x, landing_front - 0.08, landing_z + 0.02),
        (x, front_y + 0.08, landing_z * 2.0 - 0.18),
        0.16,
        0.23,
        navy,
        bevel=0.018
    )

# Cross braces beneath selected treads.
for i in (1, 3, 5, 7, 9):
    y = front_y + (i + 0.65) * tread_run
    z = (i + 1) * rise - 0.17
    add_box(
        "Lower Cross Brace %02d" % i,
        (left_center, y, z),
        (flight_width - 0.12, 0.09, 0.10),
        navy,
        bevel=0.01
    )
    y2 = landing_front - (i + 0.65) * tread_run
    z2 = landing_z + (i + 1) * rise - 0.17
    add_box(
        "Upper Cross Brace %02d" % i,
        (right_center, y2, z2),
        (flight_width - 0.12, 0.09, 0.10),
        navy,
        bevel=0.01
    )

# Rear landing support columns and subtle diagonal knee braces.
column_top = landing_z - slab_thickness
for x in (left_outer + 0.08, right_outer - 0.08):
    add_vertical_post("Landing Support Column", x, landing_back - 0.10, 0.0, column_top, 0.15)
    add_beam(
        "Landing Knee Brace",
        (x, landing_back - 0.10, column_top - 0.76),
        (x, landing_back - 0.60, column_top - 0.08),
        0.10,
        0.10,
        navy,
        bevel=0.012
    )

# Balustrade parameters.
rail_height = 1.02
glass_bottom_offset = 0.15
glass_height = 0.77
rail_size = 0.075
post_size = 0.072
panel_count = 4

# Sloped glass and rails on both sides of the lower flight.
def lower_base(y):
    return rise + (landing_z - rise) * ((y - front_y) / (landing_front - front_y))


for side_index, x in enumerate((left_outer, left_inner)):
    side_name = "Outer" if side_index == 0 else "Inner"
    boundaries = [front_y + (landing_front - front_y) * j / panel_count for j in range(panel_count + 1)]
    for j in range(panel_count):
        y0 = boundaries[j] + 0.045
        y1 = boundaries[j + 1] - 0.045
        b0 = lower_base(y0) + glass_bottom_offset
        b1 = lower_base(y1) + glass_bottom_offset
        add_sloped_glass("Lower %s Glass Panel %d" % (side_name, j + 1), x, y0, y1, b0, b1, glass_height)
    for j, y in enumerate(boundaries):
        base = lower_base(y) + 0.02
        add_vertical_post(
            "Lower %s Post %d" % (side_name, j + 1),
            x, y, base, lower_base(y) + rail_height, post_size
        )
    add_beam(
        "Lower %s Top Rail" % side_name,
        (x, front_y, lower_base(front_y) + rail_height),
        (x, landing_front, lower_base(landing_front) + rail_height),
        rail_size, rail_size, edge_mat, bevel=0.012
    )
    add_beam(
        "Lower %s Bottom Rail" % side_name,
        (x, front_y, lower_base(front_y) + glass_bottom_offset - 0.025),
        (x, landing_front, lower_base(landing_front) + glass_bottom_offset - 0.025),
        0.055, 0.055, navy, bevel=0.008
    )

# Sloped glass and rails on both sides of the upper flight.
def upper_base(y):
    return landing_z + rise + (landing_z - rise) * ((landing_front - y) / (landing_front - front_y))


for side_index, x in enumerate((right_inner, right_outer)):
    side_name = "Inner" if side_index == 0 else "Outer"
    boundaries = [front_y + (landing_front - front_y) * j / panel_count for j in range(panel_count + 1)]
    for j in range(panel_count):
        y0 = boundaries[j] + 0.045
        y1 = boundaries[j + 1] - 0.045
        b0 = upper_base(y0) + glass_bottom_offset
        b1 = upper_base(y1) + glass_bottom_offset
        add_sloped_glass("Upper %s Glass Panel %d" % (side_name, j + 1), x, y0, y1, b0, b1, glass_height)
    for j, y in enumerate(boundaries):
        base = upper_base(y) + 0.02
        add_vertical_post(
            "Upper %s Post %d" % (side_name, j + 1),
            x, y, base, upper_base(y) + rail_height, post_size
        )
    add_beam(
        "Upper %s Top Rail" % side_name,
        (x, front_y, upper_base(front_y) + rail_height),
        (x, landing_front, upper_base(landing_front) + rail_height),
        rail_size, rail_size, edge_mat, bevel=0.012
    )
    add_beam(
        "Upper %s Bottom Rail" % side_name,
        (x, front_y, upper_base(front_y) + glass_bottom_offset - 0.025),
        (x, landing_front, upper_base(landing_front) + glass_bottom_offset - 0.025),
        0.055, 0.055, navy, bevel=0.008
    )

# Landing side balustrades.
landing_glass_bottom = landing_z + glass_bottom_offset
landing_top = landing_z + rail_height
landing_side_panel_count = 2

for x, label in ((left_outer, "Left"), (right_outer, "Right")):
    for j in range(landing_side_panel_count):
        y0 = landing_front + (landing_back - landing_front) * j / landing_side_panel_count
        y1 = landing_front + (landing_back - landing_front) * (j + 1) / landing_side_panel_count
        add_horizontal_glass_y(
            "Landing %s Glass Panel %d" % (label, j + 1),
            x, y0 + 0.045, y1 - 0.045,
            landing_glass_bottom, glass_height
        )
    for j in range(landing_side_panel_count + 1):
        y = landing_front + (landing_back - landing_front) * j / landing_side_panel_count
        add_vertical_post("Landing %s Post %d" % (label, j + 1), x, y, landing_z + 0.02, landing_top, post_size)
    add_beam(
        "Landing %s Top Rail" % label,
        (x, landing_front, landing_top),
        (x, landing_back, landing_top),
        rail_size, rail_size, edge_mat, bevel=0.012
    )
    add_beam(
        "Landing %s Bottom Rail" % label,
        (x, landing_front, landing_glass_bottom - 0.025),
        (x, landing_back, landing_glass_bottom - 0.025),
        0.055, 0.055, navy, bevel=0.008
    )

# Rear landing glass enclosure, divided into four framed panels.
rear_panel_count = 4
for j in range(rear_panel_count):
    x0 = left_outer + landing_width * j / rear_panel_count
    x1 = left_outer + landing_width * (j + 1) / rear_panel_count
    add_horizontal_glass_x(
        "Landing Rear Glass Panel %d" % (j + 1),
        x0 + 0.045, x1 - 0.045, landing_back,
        landing_glass_bottom, glass_height
    )

for j in range(rear_panel_count + 1):
    x = left_outer + landing_width * j / rear_panel_count
    add_vertical_post("Landing Rear Post %d" % (j + 1), x, landing_back, landing_z + 0.02, landing_top, post_size)

add_beam(
    "Landing Rear Top Rail",
    (left_outer, landing_back, landing_top),
    (right_outer, landing_back, landing_top),
    rail_size, rail_size, edge_mat, bevel=0.012
)
add_beam(
    "Landing Rear Bottom Rail",
    (left_outer, landing_back, landing_glass_bottom - 0.025),
    (right_outer, landing_back, landing_glass_bottom - 0.025),
    0.055, 0.055, navy, bevel=0.008
)

# Small base plates anchor the landing columns.
for x in (left_outer + 0.08, right_outer - 0.08):
    add_box(
        "Column Base Plate",
        (x, landing_back - 0.10, 0.025),
        (0.25, 0.25, 0.05),
        navy,
        bevel=0.018,
        bevel_segments=3
    )

# Set smooth shading where appropriate without smoothing the planar glass faces.
for obj in assembly.objects:
    if obj.type == 'MESH' and "Glass" not in obj.name:
        for polygon in obj.data.polygons:
            polygon.use_smooth = False

# Make the staircase assembly active and selected.
bpy.ops.object.select_all(action='DESELECT')
for obj in assembly.objects:
    obj.select_set(True)
if assembly.objects:
    bpy.context.view_layer.objects.active = assembly.objects[0]