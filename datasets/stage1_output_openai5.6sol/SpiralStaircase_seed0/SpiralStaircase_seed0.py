import bpy
import math
from mathutils import Vector

# Clear the entire scene.
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

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'METERS'

# Staircase proportions.
step_count = 28
step_rise = 0.21
step_angle = math.radians(24.0)
tread_angle = math.radians(28.0)
tread_inner_radius = 0.13
tread_outer_radius = 1.55
tread_thickness = 0.11
first_tread_top = 0.20
post_radius = 0.18
rail_radius = 1.48
rail_height = 0.98
rail_tube_radius = 0.052

last_tread_top = first_tread_top + (step_count - 1) * step_rise
post_height = last_tread_top + rail_height + 0.10

def add_bevel(obj, width, segments=3):
    modifier = obj.modifiers.new(name="Edge Bevel", type='BEVEL')
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = 'ANGLE'

def smooth_cylindrical_sides(obj):
    for polygon in obj.data.polygons:
        if abs(polygon.normal.z) < 0.5:
            polygon.use_smooth = True

def create_cylinder(name, radius, depth, z, vertices=48, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        end_fill_type='NGON',
        location=(0.0, 0.0, z)
    )
    obj = bpy.context.object
    obj.name = name
    smooth_cylindrical_sides(obj)
    if bevel > 0.0:
        add_bevel(obj, bevel, 3)
    return obj

def create_vertical_cylinder(name, radius, z_bottom, z_top, x, y, vertices=16):
    depth = z_top - z_bottom
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        end_fill_type='NGON',
        location=(x, y, (z_bottom + z_top) * 0.5)
    )
    obj = bpy.context.object
    obj.name = name
    smooth_cylindrical_sides(obj)
    add_bevel(obj, min(radius * 0.35, 0.008), 2)
    return obj

def create_tread(index, center_angle, top_z):
    half_angle = tread_angle * 0.5
    start_angle = center_angle - half_angle
    end_angle = center_angle + half_angle
    arc_segments = 10

    boundary = []
    for j in range(arc_segments + 1):
        t = j / arc_segments
        angle = start_angle + (end_angle - start_angle) * t
        boundary.append((
            tread_outer_radius * math.cos(angle),
            tread_outer_radius * math.sin(angle)
        ))

    for j in range(arc_segments + 1):
        t = j / arc_segments
        angle = end_angle - (end_angle - start_angle) * t
        boundary.append((
            tread_inner_radius * math.cos(angle),
            tread_inner_radius * math.sin(angle)
        ))

    bottom_z = top_z - tread_thickness
    boundary_count = len(boundary)
    vertices = [(x, y, bottom_z) for x, y in boundary]
    vertices.extend((x, y, top_z) for x, y in boundary)

    faces = []
    faces.append(tuple(reversed(range(boundary_count))))
    faces.append(tuple(range(boundary_count, boundary_count * 2)))

    for j in range(boundary_count):
        nxt = (j + 1) % boundary_count
        faces.append((j, nxt, boundary_count + nxt, boundary_count + j))

    mesh = bpy.data.meshes.new(f"Spiral_Tread_{index + 1:02d}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(f"Spiral_Tread_{index + 1:02d}", mesh)
    bpy.context.collection.objects.link(obj)
    add_bevel(obj, 0.018, 3)
    return obj

def create_poly_tube(name, points, radius, resolution=4):
    curve_data = bpy.data.curves.new(name=f"{name}_Curve", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 2
    curve_data.bevel_depth = radius
    curve_data.bevel_resolution = resolution
    curve_data.resolution_u = 2
    curve_data.use_fill_caps = True

    spline = curve_data.splines.new(type='POLY')
    spline.points.add(len(points) - 1)
    for point, coordinate in zip(spline.points, points):
        point.co = (coordinate[0], coordinate[1], coordinate[2], 1.0)

    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    return obj

# Central cylindrical post and structural end details.
create_cylinder(
    "Central_Post",
    post_radius,
    post_height,
    post_height * 0.5,
    vertices=64,
    bevel=0.012
)

create_cylinder(
    "Post_Base_Flange",
    0.30,
    0.10,
    0.05,
    vertices=64,
    bevel=0.018
)

create_cylinder(
    "Post_Base_Collar",
    0.235,
    0.16,
    0.13,
    vertices=64,
    bevel=0.012
)

create_cylinder(
    "Post_Top_Collar",
    0.235,
    0.09,
    post_height - 0.045,
    vertices=64,
    bevel=0.012
)

bpy.ops.mesh.primitive_uv_sphere_add(
    segments=40,
    ring_count=20,
    radius=0.235,
    location=(0.0, 0.0, post_height + 0.16)
)
finial = bpy.context.object
finial.name = "Central_Post_Finial"
for polygon in finial.data.polygons:
    polygon.use_smooth = True

# Wedge-shaped treads and their collars.
for i in range(step_count):
    angle = i * step_angle
    tread_top = first_tread_top + i * step_rise
    create_tread(i, angle, tread_top)

    collar_top = tread_top - tread_thickness + 0.025
    create_cylinder(
        f"Tread_Collar_{i + 1:02d}",
        0.235,
        0.055,
        collar_top - 0.0275,
        vertices=40,
        bevel=0.007
    )

# Continuous outer helical support just beneath the tread edges.
helix_samples = (step_count - 1) * 10 + 1
outer_stringer_points = []
for j in range(helix_samples):
    t = j / (helix_samples - 1)
    angle = t * (step_count - 1) * step_angle
    tread_top = first_tread_top + t * (step_count - 1) * step_rise
    z = tread_top - tread_thickness + 0.025
    outer_stringer_points.append((
        1.45 * math.cos(angle),
        1.45 * math.sin(angle),
        z
    ))

create_poly_tube(
    "Outer_Helical_Stringer",
    outer_stringer_points,
    0.055,
    resolution=3
)

# Outer handrail following the staircase pitch.
handrail_points = []
for j in range(helix_samples):
    t = j / (helix_samples - 1)
    angle = t * (step_count - 1) * step_angle
    tread_top = first_tread_top + t * (step_count - 1) * step_rise
    handrail_points.append((
        rail_radius * math.cos(angle),
        rail_radius * math.sin(angle),
        tread_top + rail_height
    ))

create_poly_tube(
    "Outer_Helical_Handrail",
    handrail_points,
    rail_tube_radius,
    resolution=5
)

# Vertical balusters anchored to every tread.
for i in range(step_count):
    angle = i * step_angle
    tread_top = first_tread_top + i * step_rise
    x = rail_radius * math.cos(angle)
    y = rail_radius * math.sin(angle)
    create_vertical_cylinder(
        f"Baluster_{i + 1:02d}",
        0.024,
        tread_top - 0.012,
        tread_top + rail_height,
        x,
        y,
        vertices=16
    )

    # Small lower and upper collars add a refined mechanical connection.
    create_vertical_cylinder(
        f"Baluster_Lower_Collar_{i + 1:02d}",
        0.038,
        tread_top - 0.018,
        tread_top + 0.055,
        x,
        y,
        vertices=20
    )
    create_vertical_cylinder(
        f"Baluster_Upper_Collar_{i + 1:02d}",
        0.034,
        tread_top + rail_height - 0.065,
        tread_top + rail_height + 0.012,
        x,
        y,
        vertices=20
    )

# Rounded handrail terminals.
for endpoint_index, point in enumerate((handrail_points[0], handrail_points[-1])):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=28,
        ring_count=14,
        radius=rail_tube_radius * 1.16,
        location=point
    )
    terminal = bpy.context.object
    terminal.name = "Handrail_Terminal_Lower" if endpoint_index == 0 else "Handrail_Terminal_Upper"
    for polygon in terminal.data.polygons:
        polygon.use_smooth = True

# Keep the complete coherent assembly selected.
bpy.ops.object.select_all(action='SELECT')