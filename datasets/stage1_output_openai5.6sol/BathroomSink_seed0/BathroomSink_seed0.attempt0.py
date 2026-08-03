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

# -------------------------------------------------------------------
# Materials
# -------------------------------------------------------------------

def set_principled_input(shader, name, value):
    socket = shader.inputs.get(name)
    if socket is not None:
        socket.default_value = value

def make_marble_material(name, roughness, coat_weight):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    wave = nodes.new("ShaderNodeTexWave")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    output.location = (650, 0)
    shader.location = (390, 0)
    ramp.location = (80, 80)
    wave.location = (-190, 80)
    mapping.location = (-410, 80)
    texcoord.location = (-620, 80)
    bump.location = (180, -180)

    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs["Scale"].default_value = 2.15
    wave.inputs["Distortion"].default_value = 8.0
    wave.inputs["Detail"].default_value = 6.0
    wave.inputs["Detail Scale"].default_value = 1.7
    wave.inputs["Detail Roughness"].default_value = 0.7

    mapping.inputs["Rotation"].default_value[2] = math.radians(28.0)
    mapping.inputs["Scale"].default_value = (0.85, 1.25, 1.8)

    cr = ramp.color_ramp
    cr.interpolation = 'B_SPLINE'
    cr.elements.remove(cr.elements[1])
    elements = [
        (0.00, (0.006, 0.030, 0.020, 1.0)),
        (0.37, (0.012, 0.070, 0.043, 1.0)),
        (0.455, (0.025, 0.120, 0.073, 1.0)),
        (0.495, (0.28, 0.48, 0.34, 1.0)),
        (0.525, (0.075, 0.22, 0.135, 1.0)),
        (0.62, (0.010, 0.060, 0.037, 1.0)),
        (1.00, (0.003, 0.022, 0.014, 1.0)),
    ]
    first = cr.elements[0]
    first.position = elements[0][0]
    first.color = elements[0][1]
    for position, color in elements[1:]:
        element = cr.elements.new(position)
        element.color = color

    set_principled_input(shader, "Metallic", 0.03)
    set_principled_input(shader, "Roughness", roughness)
    set_principled_input(shader, "IOR", 1.48)
    set_principled_input(shader, "Coat Weight", coat_weight)
    set_principled_input(shader, "Coat Roughness", max(0.025, roughness * 0.45))

    bump.inputs["Strength"].default_value = 0.045
    bump.inputs["Distance"].default_value = 0.025

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    links.new(wave.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(wave.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return mat

def make_simple_material(name, color, metallic=0.0, roughness=0.3):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    set_principled_input(shader, "Base Color", color)
    set_principled_input(shader, "Metallic", metallic)
    set_principled_input(shader, "Roughness", roughness)
    if metallic > 0.8:
        set_principled_input(shader, "Coat Weight", 0.35)
        set_principled_input(shader, "Coat Roughness", 0.025)
    return mat

stone_mat = make_marble_material("Dark Green Stone", 0.22, 0.30)
bowl_mat = make_marble_material("Glossy Green Marble Interior", 0.065, 0.62)
chrome_mat = make_simple_material("Polished Chrome", (0.62, 0.66, 0.70, 1.0), 1.0, 0.055)
dark_mat = make_simple_material("Dark Openings", (0.004, 0.006, 0.005, 1.0), 0.0, 0.22)

# -------------------------------------------------------------------
# Basin block and carved bowl
# -------------------------------------------------------------------

SEGMENTS = 96

def superellipse_loop(a, b, exponent, z):
    points = []
    power = 2.0 / exponent
    for i in range(SEGMENTS):
        t = 2.0 * math.pi * i / SEGMENTS
        c = math.cos(t)
        s = math.sin(t)
        x = a * math.copysign(abs(c) ** power, c)
        y = b * math.copysign(abs(s) ** power, s)
        points.append((x, y, z))
    return points

vertices = []
faces = []
face_materials = []
face_smooth = []

def add_loop(points):
    start = len(vertices)
    vertices.extend(points)
    return list(range(start, start + len(points)))

def bridge_loops(loop_a, loop_b, material_index, smooth):
    for i in range(SEGMENTS):
        j = (i + 1) % SEGMENTS
        faces.append((loop_a[i], loop_a[j], loop_b[j], loop_b[i]))
        face_materials.append(material_index)
        face_smooth.append(smooth)

outer_top = add_loop(superellipse_loop(2.02, 1.72, 5.6, 0.58))
outer_shoulder = add_loop(superellipse_loop(2.095, 1.795, 5.6, 0.505))
outer_bottom = add_loop(superellipse_loop(2.095, 1.795, 5.6, -0.64))

opening = add_loop(superellipse_loop(1.52, 1.15, 4.8, 0.58))
lip = add_loop(superellipse_loop(1.49, 1.125, 4.7, 0.46))
bowl_mid_a = add_loop(superellipse_loop(1.32, 0.99, 4.15, 0.10))
bowl_mid_b = add_loop(superellipse_loop(0.98, 0.72, 3.55, -0.25))
bowl_floor = add_loop(superellipse_loop(0.55, 0.39, 2.8, -0.47))
drain_opening = add_loop(superellipse_loop(0.255, 0.255, 2.0, -0.505))

# Top stone rim, rounded outer shoulder, exterior wall, and bowl.
bridge_loops(outer_top, opening, 0, False)
bridge_loops(outer_top, outer_shoulder, 0, True)
bridge_loops(outer_shoulder, outer_bottom, 0, False)
bridge_loops(opening, lip, 1, True)
bridge_loops(lip, bowl_mid_a, 1, True)
bridge_loops(bowl_mid_a, bowl_mid_b, 1, True)
bridge_loops(bowl_mid_b, bowl_floor, 1, True)
bridge_loops(bowl_floor, drain_opening, 1, True)

# Flat underside.
faces.append(tuple(reversed(outer_bottom)))
face_materials.append(0)
face_smooth.append(False)

mesh = bpy.data.meshes.new("Carved Stone Basin Mesh")
mesh.from_pydata(vertices, [], faces)
mesh.materials.append(stone_mat)
mesh.materials.append(bowl_mat)
mesh.update()

basin = bpy.data.objects.new("Carved Dark Green Stone Basin", mesh)
bpy.context.collection.objects.link(basin)

for polygon, mat_index, smooth in zip(mesh.polygons, face_materials, face_smooth):
    polygon.material_index = mat_index
    polygon.use_smooth = smooth

# Weighted bevel around exposed stone edges.
bevel = basin.modifiers.new("Subtle Stone Edge Bevel", 'BEVEL')
bevel.width = 0.022
bevel.segments = 2
bevel.limit_method = 'ANGLE'
bevel.angle_limit = math.radians(38.0)

# -------------------------------------------------------------------
# Mesh primitive helpers
# -------------------------------------------------------------------

def add_cylinder(name, radius, depth, location, material, vertices_count=48):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices_count,
        radius=radius,
        depth=depth,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    bevel_mod = obj.modifiers.new("Edge Softening", 'BEVEL')
    bevel_mod.width = min(radius * 0.12, depth * 0.12)
    bevel_mod.segments = 2
    return obj

def add_cylinder_between(name, start, end, radius, material, vertices_count=40):
    a = Vector(start)
    b = Vector(end)
    direction = b - a
    obj = add_cylinder(
        name,
        radius,
        direction.length,
        (a + b) * 0.5,
        material,
        vertices_count
    )
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = direction.to_track_quat('Z', 'Y')
    return obj

def add_sphere(name, location, radius, material, scale=(1.0, 1.0, 1.0)):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=40,
        ring_count=20,
        radius=radius,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

# -------------------------------------------------------------------
# Drain assembly
# -------------------------------------------------------------------

add_cylinder(
    "Chrome Drain Stopper",
    0.215,
    0.035,
    (0.0, 0.0, -0.500),
    chrome_mat,
    64
)

bpy.ops.mesh.primitive_torus_add(
    major_radius=0.235,
    minor_radius=0.025,
    major_segments=64,
    minor_segments=16,
    location=(0.0, 0.0, -0.482)
)
drain_ring = bpy.context.object
drain_ring.name = "Chrome Drain Rim"
drain_ring.data.materials.append(chrome_mat)
for poly in drain_ring.data.polygons:
    poly.use_smooth = True

# Fine central stopper detail.
add_cylinder(
    "Drain Stopper Center",
    0.052,
    0.012,
    (0.0, 0.0, -0.477),
    dark_mat,
    40
)

# -------------------------------------------------------------------
# Faucet mounting hardware
# -------------------------------------------------------------------

faucet_x = -1.24
faucet_y = 1.40

add_cylinder(
    "Faucet Mounting Escutcheon",
    0.245,
    0.075,
    (faucet_x, faucet_y, 0.617),
    chrome_mat,
    64
)
add_cylinder(
    "Faucet Base Body",
    0.155,
    0.40,
    (faucet_x, faucet_y, 0.79),
    chrome_mat,
    56
)
add_cylinder(
    "Faucet Body Collar",
    0.178,
    0.065,
    (faucet_x, faucet_y, 0.975),
    chrome_mat,
    56
)

# -------------------------------------------------------------------
# Chrome gooseneck
# -------------------------------------------------------------------

curve_data = bpy.data.curves.new("Gooseneck Faucet Curve", type='CURVE')
curve_data.dimensions = '3D'
curve_data.resolution_u = 16
curve_data.bevel_depth = 0.115
curve_data.bevel_resolution = 6
curve_data.resolution_u = 20
curve_data.materials.append(chrome_mat)

spline = curve_data.splines.new('BEZIER')
path_points = [
    (-1.24, 1.40, 0.90),
    (-1.24, 1.40, 1.55),
    (-1.23, 1.27, 1.98),
    (-1.21, 0.92, 2.18),
    (-1.19, 0.52, 2.12),
    (-1.18, 0.30, 1.82),
    (-1.18, 0.29, 1.53),
]
spline.bezier_points.add(len(path_points) - 1)
for point, coordinate in zip(spline.bezier_points, path_points):
    point.co = coordinate
    point.handle_left_type = 'AUTO'
    point.handle_right_type = 'AUTO'

gooseneck = bpy.data.objects.new("Chrome Gooseneck Faucet", curve_data)
bpy.context.collection.objects.link(gooseneck)

# Slightly enlarged nozzle at the downward-facing outlet.
add_cylinder(
    "Faucet Outlet Nozzle",
    0.135,
    0.17,
    (-1.18, 0.29, 1.46),
    chrome_mat,
    56
)
add_cylinder(
    "Faucet Outlet Aerator",
    0.108,
    0.018,
    (-1.18, 0.29, 1.368),
    dark_mat,
    48
)

bpy.ops.mesh.primitive_torus_add(
    major_radius=0.109,
    minor_radius=0.014,
    major_segments=48,
    minor_segments=12,
    location=(-1.18, 0.29, 1.376)
)
aerator_ring = bpy.context.object
aerator_ring.name = "Aerator Chrome Ring"
aerator_ring.data.materials.append(chrome_mat)
for poly in aerator_ring.data.polygons:
    poly.use_smooth = True

# -------------------------------------------------------------------
# Single lever handle
# -------------------------------------------------------------------

pivot = (-1.055, 1.40, 0.94)
add_sphere("Faucet Handle Pivot", pivot, 0.13, chrome_mat, (1.0, 0.92, 1.0))

lever_start = (-0.985, 1.395, 1.00)
lever_end = (-0.73, 1.30, 1.30)
add_cylinder_between(
    "Single Lever Handle",
    lever_start,
    lever_end,
    0.052,
    chrome_mat,
    40
)
add_sphere(
    "Single Lever Handle Tip",
    lever_end,
    0.073,
    chrome_mat,
    (1.05, 0.88, 1.15)
)

# Small decorative seam at the faucet body.
bpy.ops.mesh.primitive_torus_add(
    major_radius=0.159,
    minor_radius=0.012,
    major_segments=48,
    minor_segments=10,
    location=(faucet_x, faucet_y, 0.99)
)
body_seam = bpy.context.object
body_seam.name = "Faucet Body Trim Ring"
body_seam.data.materials.append(chrome_mat)
for poly in body_seam.data.polygons:
    poly.use_smooth = True

# Keep transforms and normals clean.
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.select_set(False)

bpy.context.view_layer.objects.active = basin
basin.select_set(True)