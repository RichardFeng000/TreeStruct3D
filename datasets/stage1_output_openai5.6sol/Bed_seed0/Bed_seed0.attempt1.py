import bpy
import math

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Materials
def material(name, color, roughness=0.5):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

wood = material("Walnut", (0.28, 0.085, 0.025), 0.34)
dark_wood = material("Dark Walnut", (0.12, 0.025, 0.010), 0.32)
light_wood = material("Carved Walnut", (0.43, 0.16, 0.052), 0.38)
green = material("Sage Green Mattress", (0.18, 0.40, 0.23), 0.72)
green_edge = material("Dark Green Piping", (0.08, 0.22, 0.11), 0.66)
pink = material("Light Pink Blanket", (0.92, 0.59, 0.67), 0.8)
pink_edge = material("Pink Binding", (0.68, 0.30, 0.39), 0.74)
ivory = material("Ivory Comforter", (0.92, 0.86, 0.78), 0.82)
ivory_shadow = material("Comforter Seams", (0.70, 0.60, 0.54), 0.78)
cream = material("Cream Pillows", (0.97, 0.92, 0.83), 0.8)
rose = material("Rose Accent Pillow", (0.79, 0.43, 0.49), 0.78)

def add_mat(obj, mat):
    obj.data.materials.append(mat)

def box(name, location, dimensions, mat, bevel=0.05, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    add_mat(obj, mat)
    if bevel > 0:
        mod = obj.modifiers.new("Rounded edges", 'BEVEL')
        mod.width = bevel
        mod.segments = 4
        mod.limit_method = 'ANGLE'
    return obj

def tapered_leg(name, x, y, height, top_width, bottom_width, mat):
    z0 = 0.0
    z1 = height
    tw = top_width * 0.5
    bw = bottom_width * 0.5
    verts = [
        (x-bw, y-bw, z0), (x+bw, y-bw, z0),
        (x+bw, y+bw, z0), (x-bw, y+bw, z0),
        (x-tw, y-tw, z1), (x+tw, y-tw, z1),
        (x+tw, y+tw, z1), (x-tw, y+tw, z1)
    ]
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
    add_mat(obj, mat)
    bevel = obj.modifiers.new("Soft leg edges", 'BEVEL')
    bevel.width = 0.04
    bevel.segments = 3
    return obj

def sphere(name, location, scale, mat, segments=28):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=16,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    add_mat(obj, mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

def cylinder(name, location, radius, depth, mat, rotation=(0.0, 0.0, 0.0), vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    add_mat(obj, mat)
    bevel = obj.modifiers.new("Rounded cylinder edges", 'BEVEL')
    bevel.width = min(radius * 0.18, 0.04)
    bevel.segments = 3
    return obj

def beam_between(name, p1, p2, width, depth, mat):
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    dx = x2 - x1
    dz = z2 - z1
    length = math.sqrt(dx * dx + dz * dz)
    angle = -math.atan2(dz, dx)
    return box(
        name,
        ((x1+x2)*0.5, (y1+y2)*0.5, (z1+z2)*0.5),
        (length, depth, width),
        mat,
        width * 0.2,
        (0.0, angle, 0.0)
    )

# Frame legs
for x in (-1.98, 1.98):
    for y in (-3.18, 3.18):
        tapered_leg("Tapered Bed Leg", x, y, 1.35, 0.42, 0.25, dark_wood)

# Main frame rails
box("Left Side Rail", (-1.94, 0.0, 1.22), (0.30, 6.28, 0.62), wood, 0.07)
box("Right Side Rail", (1.94, 0.0, 1.22), (0.30, 6.28, 0.62), wood, 0.07)
box("Head End Rail", (0.0, 3.17, 1.24), (3.70, 0.31, 0.66), wood, 0.07)
box("Foot End Rail", (0.0, -3.17, 1.24), (3.70, 0.31, 0.66), wood, 0.07)

# Mattress supports
for y in (-2.45, -1.55, -0.65, 0.25, 1.15, 2.05):
    box("Wooden Mattress Slat", (0.0, y, 1.43), (3.58, 0.14, 0.10), light_wood, 0.02)

# Mattress
box("Green Mattress", (0.0, 0.0, 1.80), (3.60, 5.76, 0.65), green, 0.18)
box("Mattress Front Piping", (0.0, -2.82, 2.08), (3.34, 0.045, 0.045), green_edge, 0.022)
box("Mattress Left Piping", (-1.76, 0.0, 2.08), (0.045, 5.38, 0.045), green_edge, 0.022)
box("Mattress Right Piping", (1.76, 0.0, 2.08), (0.045, 5.38, 0.045), green_edge, 0.022)

# Headboard posts and finials
for x in (-1.98, 1.98):
    box("Headboard Post", (x, 3.22, 2.72), (0.43, 0.43, 3.74), wood, 0.075)
    box("Headboard Collar", (x, 3.22, 4.35), (0.54, 0.54, 0.18), dark_wood, 0.045)
    box("Headboard Finial Base", (x, 3.22, 4.48), (0.36, 0.36, 0.18), light_wood, 0.05)
    sphere("Headboard Finial", (x, 3.22, 4.72), (0.25, 0.25, 0.34), light_wood)

# Headboard rails
box("Headboard Lower Rail", (0.0, 3.22, 2.24), (3.62, 0.34, 0.30), dark_wood, 0.06)
box("Headboard Mid Rail", (0.0, 3.22, 2.60), (3.50, 0.26, 0.20), light_wood, 0.045)

# Headboard curved crest made from attached segments
crest = []
for i in range(13):
    x = -1.74 + i * (3.48 / 12.0)
    z = 3.92 + 0.42 * (1.0 - (x / 1.74) ** 2)
    crest.append((x, 3.22, z))

for i in range(len(crest) - 1):
    beam_between("Headboard Crest Segment", crest[i], crest[i+1], 0.24, 0.34, wood)

# Headboard slats extending exactly between rails and crest
for i, x in enumerate((-1.50, -1.20, -0.90, -0.60, -0.30, 0.30, 0.60, 0.90, 1.20, 1.50)):
    top = 3.90 + 0.42 * (1.0 - (x / 1.74) ** 2)
    bottom = 2.69
    box(
        "Decorative Headboard Slat",
        (x, 3.21, (top + bottom) * 0.5),
        (0.13, 0.18, top - bottom),
        light_wood if i % 2 else wood,
        0.035
    )
    sphere("Headboard Slat Bead", (x, 3.105, 2.87), (0.09, 0.055, 0.12), dark_wood, 20)

# Attached central medallion
bpy.ops.mesh.primitive_torus_add(
    major_radius=0.37,
    minor_radius=0.065,
    major_segments=40,
    minor_segments=12,
    location=(0.0, 3.08, 3.27),
    rotation=(math.pi / 2.0, 0.0, 0.0)
)
medallion = bpy.context.object
medallion.name = "Headboard Medallion Ring"
add_mat(medallion, light_wood)

beam_between(
    "Medallion Diagonal One",
    (-0.25, 3.07, 3.02),
    (0.25, 3.07, 3.52),
    0.07, 0.10, dark_wood
)
beam_between(
    "Medallion Diagonal Two",
    (-0.25, 3.07, 3.52),
    (0.25, 3.07, 3.02),
    0.07, 0.10, dark_wood
)
sphere("Medallion Center", (0.0, 3.00, 3.27), (0.13, 0.07, 0.13), dark_wood, 24)

# Footboard
for x in (-1.98, 1.98):
    box("Footboard Post", (x, -3.22, 1.62), (0.43, 0.43, 2.44), wood, 0.075)
    box("Footboard Collar", (x, -3.22, 2.58), (0.52, 0.52, 0.17), dark_wood, 0.045)
    box("Footboard Finial Base", (x, -3.22, 2.70), (0.34, 0.34, 0.16), light_wood, 0.045)
    sphere("Footboard Finial", (x, -3.22, 2.91), (0.22, 0.22, 0.29), light_wood)

box("Footboard Lower Decorative Rail", (0.0, -3.22, 1.78), (3.62, 0.33, 0.28), dark_wood, 0.055)
box("Footboard Upper Rail", (0.0, -3.22, 2.55), (3.62, 0.34, 0.29), wood, 0.065)

for x in (-1.47, -1.10, -0.73, -0.36, 0.0, 0.36, 0.73, 1.10, 1.47):
    box("Footboard Slat", (x, -3.21, 2.16), (0.13, 0.18, 0.63), light_wood, 0.035)

# Pink blanket with attached side drapes
nx = 31
ny = 35
verts = []
faces = []

for j in range(ny):
    v = j / (ny - 1)
    y = -2.52 + 4.18 * v
    for i in range(nx):
        u = i / (nx - 1)
        x = -1.93 + 3.86 * u
        edge = max(0.0, min(1.0, (abs(x) - 1.61) / 0.32))
        edge = edge * edge * (3.0 - 2.0 * edge)
        z = 2.145 - 0.47 * edge
        z += 0.012 * math.sin(x * 7.0 + y * 2.0)
        z += 0.012 * math.sin(y * 5.0) * edge
        verts.append((x, y, z))

for j in range(ny - 1):
    for i in range(nx - 1):
        a = j * nx + i
        faces.append((a, a + 1, a + 1 + nx, a + nx))

mesh = bpy.data.meshes.new("Pink Blanket Mesh")
mesh.from_pydata(verts, [], faces)
mesh.update()
blanket = bpy.data.objects.new("Draped Light Pink Blanket", mesh)
bpy.context.collection.objects.link(blanket)
add_mat(blanket, pink)

solid = blanket.modifiers.new("Blanket Thickness", 'SOLIDIFY')
solid.thickness = 0.035
solid.offset = -0.4
bev = blanket.modifiers.new("Soft Blanket Edge", 'BEVEL')
bev.width = 0.018
bev.segments = 3

# Binding fixed directly to blanket perimeter
box("Blanket Front Binding", (0.0, -2.53, 2.12), (3.25, 0.045, 0.045), pink_edge, 0.02)
box("Blanket Left Binding", (-1.925, -0.43, 1.68), (0.045, 4.15, 0.045), pink_edge, 0.02)
box("Blanket Right Binding", (1.925, -0.43, 1.68), (0.045, 4.15, 0.045), pink_edge, 0.02)

# Soft folded comforter across foot
box("Comforter Lower Fold", (0.0, -1.92, 2.23), (3.30, 0.92, 0.16), ivory_shadow, 0.08)
box("Comforter Main Fold", (0.0, -1.87, 2.36), (3.38, 0.84, 0.18), ivory, 0.09)
box("Comforter Top Fold", (0.0, -1.80, 2.49), (3.24, 0.68, 0.16), ivory, 0.08)

# Quilt channels attached to top surface
for x in (-1.20, -0.60, 0.0, 0.60, 1.20):
    box("Comforter Quilt Channel", (x, -1.80, 2.578), (0.025, 0.54, 0.018), ivory_shadow, 0.008)
for y in (-1.99, -1.77, -1.59):
    box("Comforter Cross Seam", (0.0, y, 2.578), (3.04, 0.022, 0.018), ivory_shadow, 0.008)

# Pillows at head, with fuller rounded forms
p1 = box(
    "Left Cream Pillow",
    (-0.82, 2.10, 2.37),
    (1.52, 0.82, 0.34),
    cream,
    0.22,
    (0.05, 0.0, -0.08)
)
p2 = box(
    "Right Cream Pillow",
    (0.82, 2.10, 2.38),
    (1.52, 0.82, 0.34),
    cream,
    0.22,
    (0.05, 0.0, 0.08)
)
p3 = box(
    "Rose Accent Pillow",
    (0.0, 1.72, 2.57),
    (1.12, 0.62, 0.31),
    rose,
    0.20,
    (-0.03, 0.0, 0.0)
)

# Attached pillow seam strips
box("Left Pillow Front Seam", (-0.82, 1.70, 2.38), (1.29, 0.025, 0.05), ivory_shadow, 0.018, (0.0, 0.0, -0.08))
box("Right Pillow Front Seam", (0.82, 1.70, 2.39), (1.29, 0.025, 0.05), ivory_shadow, 0.018, (0.0, 0.0, 0.08))
box("Rose Pillow Front Seam", (0.0, 1.42, 2.58), (0.94, 0.025, 0.045), pink_edge, 0.016)

# Small attached pillow tufts
sphere("Left Pillow Tuft", (-0.82, 2.02, 2.55), (0.055, 0.055, 0.025), ivory_shadow, 20)
sphere("Right Pillow Tuft", (0.82, 2.02, 2.56), (0.055, 0.055, 0.025), ivory_shadow, 20)
sphere("Rose Pillow Tuft", (0.0, 1.65, 2.73), (0.05, 0.05, 0.022), pink_edge, 20)

# Select the completed assembly
bpy.ops.object.select_all(action='DESELECT')
mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
for obj in mesh_objects:
    obj.select_set(True)
if mesh_objects:
    bpy.context.view_layer.objects.active = mesh_objects[0]