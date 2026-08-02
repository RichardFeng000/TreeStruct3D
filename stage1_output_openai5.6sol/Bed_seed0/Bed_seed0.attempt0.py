import bpy
import math
from mathutils import Vector

# Clear the default scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    pass

# Materials.
def make_material(name, color, roughness=0.48):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

wood = make_material("Warm Walnut Wood", (0.24, 0.075, 0.026), 0.34)
wood_dark = make_material("Dark Carved Wood", (0.105, 0.025, 0.012), 0.32)
wood_light = make_material("Wood Highlights", (0.38, 0.13, 0.045), 0.37)
mattress_mat = make_material("Deep Sage Green Mattress", (0.19, 0.39, 0.22), 0.72)
mattress_edge_mat = make_material("Mattress Edge Piping", (0.11, 0.25, 0.13), 0.62)
pink = make_material("Light Pink Blanket", (0.92, 0.57, 0.64), 0.8)
pink_edge = make_material("Pink Blanket Piping", (0.69, 0.31, 0.39), 0.72)
comforter_mat = make_material("Ivory Blush Comforter", (0.91, 0.81, 0.75), 0.82)
comforter_shadow = make_material("Comforter Fold Shadow", (0.74, 0.61, 0.57), 0.77)
pillow_cream = make_material("Cream Pillows", (0.96, 0.91, 0.83), 0.78)
pillow_rose = make_material("Rose Pillow", (0.77, 0.42, 0.46), 0.76)

def assign_material(obj, mat):
    obj.data.materials.append(mat)

def rounded_box(name, location, dimensions, material, bevel=0.08, segments=3, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign_material(obj, material)
    if bevel > 0:
        mod = obj.modifiers.new("Softened edges", 'BEVEL')
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = 'ANGLE'
    return obj

def tapered_prism(name, location, bottom_size, top_size, height, material):
    bx, by = bottom_size
    tx, ty = top_size
    z0 = location[2] - height * 0.5
    z1 = location[2] + height * 0.5
    verts = [
        (-bx/2, -by/2, z0), (bx/2, -by/2, z0),
        (bx/2, by/2, z0), (-bx/2, by/2, z0),
        (-tx/2, -ty/2, z1), (tx/2, -ty/2, z1),
        (tx/2, ty/2, z1), (-tx/2, ty/2, z1)
    ]
    verts = [(x + location[0], y + location[1], z) for x, y, z in verts]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5),
        (0, 4, 5, 1), (1, 5, 6, 2),
        (2, 6, 7, 3), (3, 7, 4, 0)
    ]
    mesh = bpy.data.meshes.new(name + " Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    assign_material(obj, material)
    bevel = obj.modifiers.new("Leg edge rounding", 'BEVEL')
    bevel.width = 0.045
    bevel.segments = 3
    return obj

def beam_xz(name, p1, p2, depth, thickness, material):
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    dx, dz = x2 - x1, z2 - z1
    length = math.sqrt(dx * dx + dz * dz)
    angle = -math.atan2(dz, dx)
    return rounded_box(
        name,
        ((x1 + x2) * 0.5, (y1 + y2) * 0.5, (z1 + z2) * 0.5),
        (length, depth, thickness),
        material,
        bevel=0.045,
        segments=3,
        rotation=(0, angle, 0)
    )

def curve_loop(name, points, bevel_depth, material, cyclic=True, resolution=2):
    curve_data = bpy.data.curves.new(name + " Curve", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = resolution
    curve_data.bevel_depth = bevel_depth
    curve_data.bevel_resolution = 3
    spline = curve_data.splines.new('NURBS')
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1.0)
    spline.use_cyclic_u = cyclic
    spline.order_u = min(3, len(points))
    spline.use_endpoint_u = not cyclic
    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    assign_material(obj, material)
    return obj

def ellipse_piping(name, center, radii, z_angle, material, thickness=0.018, count=48):
    cx, cy, cz = center
    rx, ry = radii
    ca, sa = math.cos(z_angle), math.sin(z_angle)
    points = []
    for i in range(count):
        a = math.tau * i / count
        lx, ly = rx * math.cos(a), ry * math.sin(a)
        x = cx + lx * ca - ly * sa
        y = cy + lx * sa + ly * ca
        points.append((x, y, cz))
    return curve_loop(name, points, thickness, material, True)

# Main tapered corner legs.
for x in (-1.96, 1.96):
    for y in (-3.18, 3.18):
        tapered_prism(
            "Tapered Walnut Leg",
            (x, y, 0.67),
            (0.28, 0.28),
            (0.42, 0.42),
            1.34,
            wood_dark
        )

# Bed-frame side and end rails.
rounded_box("Left Side Rail", (-1.94, 0, 1.25), (0.30, 6.28, 0.62), wood, 0.07)
rounded_box("Right Side Rail", (1.94, 0, 1.25), (0.30, 6.28, 0.62), wood, 0.07)
rounded_box("Head Frame Rail", (0, 3.17, 1.28), (3.72, 0.30, 0.66), wood, 0.07)
rounded_box("Foot Frame Rail", (0, -3.17, 1.28), (3.72, 0.30, 0.66), wood, 0.07)

# A few visible support slats beneath the mattress.
for y in (-2.45, -1.55, -0.65, 0.25, 1.15, 2.05):
    rounded_box("Mattress Support Slat", (0, y, 1.44), (3.62, 0.13, 0.10), wood_light, 0.025)

# Mattress and its contrasting edge piping.
rounded_box("Green Mattress", (0, 0.02, 1.80), (3.62, 5.78, 0.64), mattress_mat, 0.18, 5)
mattress_pipe_points = []
for x, y in [
    (-1.72, -2.76), (1.72, -2.76), (1.80, -2.68), (1.80, 2.72),
    (1.72, 2.80), (-1.72, 2.80), (-1.80, 2.72), (-1.80, -2.68)
]:
    mattress_pipe_points.append((x, y, 2.09))
curve_loop("Mattress Top Edge Piping", mattress_pipe_points, 0.025, mattress_edge_mat, True)

# Decorative headboard posts.
for x in (-1.98, 1.98):
    rounded_box("Tall Headboard Post", (x, 3.24, 2.73), (0.42, 0.42, 3.72), wood, 0.075, 4)
    rounded_box("Headboard Post Collar", (x, 3.24, 4.35), (0.53, 0.53, 0.18), wood_dark, 0.045)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=(x, 3.24, 4.64))
    finial = bpy.context.object
    finial.name = "Carved Headboard Finial"
    finial.scale = (0.25, 0.25, 0.34)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign_material(finial, wood_light)
    for poly in finial.data.polygons:
        poly.use_smooth = True
    rounded_box("Finial Base", (x, 3.24, 4.42), (0.36, 0.36, 0.24), wood_dark, 0.06)

# Headboard lower and middle rails.
rounded_box("Headboard Lower Rail", (0, 3.25, 2.20), (3.65, 0.32, 0.30), wood_dark, 0.065)
rounded_box("Headboard Middle Rail", (0, 3.25, 2.58), (3.50, 0.25, 0.20), wood_light, 0.045)

# Curved segmented crest.
crest_points = []
for i in range(17):
    x = -1.75 + 3.50 * i / 16
    z = 3.93 + 0.38 * (1.0 - (x / 1.75) ** 2)
    crest_points.append((x, 3.25, z))
for i in range(len(crest_points) - 1):
    beam_xz("Curved Headboard Crest", crest_points[i], crest_points[i + 1], 0.34, 0.24, wood)
for i in range(1, len(crest_points) - 1, 2):
    x, y, z = crest_points[i]
    rounded_box("Crest Carved Block", (x, y - 0.01, z + 0.015), (0.17, 0.39, 0.31), wood_light, 0.045)

# Vertical decorative headboard slats terminating at the crest.
for i, x in enumerate((-1.52, -1.18, -0.84, -0.50, 0.50, 0.84, 1.18, 1.52)):
    top = 3.83 + 0.35 * (1.0 - (x / 1.75) ** 2)
    height = top - 2.68
    rounded_box(
        "Headboard Vertical Slat",
        (x, 3.24, 2.68 + height * 0.5),
        (0.13, 0.18, height),
        wood_light if i % 2 else wood,
        0.038
    )
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, location=(x, 3.20, 2.83))
    accent = bpy.context.object
    accent.name = "Headboard Slat Bead"
    accent.scale = (0.10, 0.07, 0.13)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign_material(accent, wood_dark)

# Central carved medallion and spokes.
bpy.ops.mesh.primitive_torus_add(
    major_radius=0.40,
    minor_radius=0.065,
    major_segments=48,
    minor_segments=12,
    location=(0, 3.13, 3.27),
    rotation=(math.pi / 2, 0, 0)
)
medallion = bpy.context.object
medallion.name = "Headboard Carved Medallion Ring"
assign_material(medallion, wood_light)
for p1, p2 in [
    ((-0.27, 3.13, 3.00), (0.27, 3.13, 3.54)),
    ((-0.27, 3.13, 3.54), (0.27, 3.13, 3.00))
]:
    beam_xz("Medallion Cross Detail", p1, p2, 0.10, 0.07, wood_dark)
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=(0, 3.08, 3.27))
center_ornament = bpy.context.object
center_ornament.name = "Medallion Center"
center_ornament.scale = (0.14, 0.08, 0.14)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
assign_material(center_ornament, wood_dark)

# Footboard posts, rails, finials, and inset slats.
for x in (-1.98, 1.98):
    rounded_box("Footboard Post", (x, -3.24, 1.61), (0.42, 0.42, 2.42), wood, 0.075, 4)
    rounded_box("Footboard Post Collar", (x, -3.24, 2.58), (0.50, 0.50, 0.16), wood_dark, 0.045)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=14, location=(x, -3.24, 2.82))
    finial = bpy.context.object
    finial.name = "Footboard Finial"
    finial.scale = (0.22, 0.22, 0.28)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign_material(finial, wood_light)
    for poly in finial.data.polygons:
        poly.use_smooth = True

rounded_box("Footboard Lower Decorative Rail", (0, -3.25, 1.77), (3.64, 0.32, 0.27), wood_dark, 0.055)
rounded_box("Footboard Upper Rail", (0, -3.25, 2.55), (3.64, 0.34, 0.28), wood, 0.065)
for x in (-1.45, -1.08, -0.72, -0.36, 0, 0.36, 0.72, 1.08, 1.45):
    rounded_box("Footboard Inset Slat", (x, -3.23, 2.16), (0.12, 0.18, 0.63), wood_light, 0.035)

# Light pink blanket with softly draped sides and subtle rippling.
nx, ny = 32, 34
verts = []
faces = []
for j in range(ny):
    v = j / (ny - 1)
    y = -2.54 + 4.25 * v
    for i in range(nx):
        u = i / (nx - 1)
        x = -1.94 + 3.88 * u
        side = max(0.0, (abs(x) - 1.66) / 0.28)
        side = min(1.0, side)
        smooth_side = side * side * (3.0 - 2.0 * side)
        z = 2.135 - 0.46 * smooth_side
        z += 0.018 * math.sin(7.0 * y + 2.0 * x) * (0.25 + 0.75 * side)
        z += 0.010 * math.sin(13.0 * x + 1.2 * y)
        verts.append((x, y, z))
for j in range(ny - 1):
    for i in range(nx - 1):
        a = j * nx + i
        faces.append((a, a + 1, a + 1 + nx, a + nx))
mesh = bpy.data.meshes.new("Draped Pink Blanket Mesh")
mesh.from_pydata(verts, [], faces)
mesh.update()
blanket = bpy.data.objects.new("Draped Light Pink Blanket", mesh)
bpy.context.collection.objects.link(blanket)
assign_material(blanket, pink)
solidify = blanket.modifiers.new("Blanket Thickness", 'SOLIDIFY')
solidify.thickness = 0.035
solidify.offset = -0.35
bevel = blanket.modifiers.new("Blanket Soft Edges", 'BEVEL')
bevel.width = 0.025
bevel.segments = 3

# Blanket piping along both hanging sides and the lower edge.
left_pipe = []
right_pipe = []
for j in range(24):
    y = -2.52 + 4.21 * j / 23
    left_pipe.append((-1.94, y, 1.675 + 0.012 * math.sin(y * 7)))
    right_pipe.append((1.94, y, 1.675 + 0.012 * math.sin(y * 7)))
curve_loop("Left Blanket Bound Edge", left_pipe, 0.018, pink_edge, False)
curve_loop("Right Blanket Bound Edge", right_pipe, 0.018, pink_edge, False)
front_pipe = []
for i in range(36):
    x = -1.93 + 3.86 * i / 35
    side = max(0.0, min(1.0, (abs(x) - 1.66) / 0.28))
    z = 2.135 - 0.46 * side * side * (3 - 2 * side)
    front_pipe.append((x, -2.54, z))
curve_loop("Blanket Lower Bound Edge", front_pipe, 0.018, pink_edge, False)

# Folded comforter stacked across the foot of the bed.
rounded_box("Comforter Bottom Fold", (0, -1.92, 2.22), (3.34, 0.86, 0.18), comforter_shadow, 0.10, 5)
rounded_box("Comforter Middle Fold", (0.05, -1.86, 2.35), (3.42, 0.76, 0.20), comforter_mat, 0.11, 5)
rounded_box("Comforter Top Fold", (-0.02, -1.80, 2.49), (3.30, 0.63, 0.18), comforter_mat, 0.10, 5)

# Comforter fold ridges and sewn channels.
for y in (-2.02, -1.78, -1.55):
    points = []
    for i in range(30):
        x = -1.56 + 3.12 * i / 29
        points.append((x, y, 2.59 + 0.008 * math.cos(x * 7)))
    curve_loop("Comforter Quilted Seam", points, 0.012, comforter_shadow, False)
for x in (-1.12, -0.55, 0.03, 0.61, 1.18):
    points = [
        (x, -2.10, 2.52),
        (x, -1.95, 2.57),
        (x, -1.78, 2.59),
        (x, -1.52, 2.55)
    ]
    curve_loop("Comforter Lengthwise Seam", points, 0.010, comforter_shadow, False)

# Pillows arranged at the head.
pillow_specs = [
    ("Left Cream Pillow", (-0.84, 2.05, 2.32), (1.55, 0.86, 0.34), -0.10, pillow_cream),
    ("Right Cream Pillow", (0.83, 2.08, 2.34), (1.55, 0.86, 0.34), 0.09, pillow_cream),
    ("Center Rose Pillow", (0.05, 1.76, 2.53), (1.22, 0.67, 0.32), -0.02, pillow_rose)
]
for name, loc, dims, angle, mat in pillow_specs:
    pillow = rounded_box(name, loc, dims, mat, bevel=0.24, segments=7, rotation=(0.05, 0, angle))
    seam_mat = comforter_shadow if mat == pillow_cream else pink_edge
    ellipse_piping(
        name + " Corded Edge",
        (loc[0], loc[1], loc[2] + dims[2] * 0.42),
        (dims[0] * 0.46, dims[1] * 0.46),
        angle,
        seam_mat,
        thickness=0.016
    )

# Small pillow center dimples.
for x, y, z, mat in [
    (-0.84, 2.05, 2.50, comforter_shadow),
    (0.83, 2.08, 2.52, comforter_shadow),
    (0.05, 1.76, 2.70, pink_edge)
]:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, location=(x, y, z))
    dimple = bpy.context.object
    dimple.name = "Pillow Center Tuft"
    dimple.scale = (0.055, 0.055, 0.025)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign_material(dimple, mat)

# Smooth all curved mesh objects while retaining beveled hard-surface forms.
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH' and any(key in obj.name for key in ("Finial", "Sphere", "Mattress", "Pillow", "Comforter")):
        for poly in obj.data.polygons:
            poly.use_smooth = True

# Keep the assembly centered and make every generated object selectable.
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type in {'MESH', 'CURVE'}:
        obj.select_set(True)
if bpy.context.scene.objects:
    bpy.context.view_layer.objects.active = next(
        (o for o in bpy.context.scene.objects if o.type == 'MESH'),
        None
    )