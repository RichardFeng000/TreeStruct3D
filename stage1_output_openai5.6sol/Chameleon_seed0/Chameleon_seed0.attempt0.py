import bpy
import math
import random
from mathutils import Vector

random.seed(23)

# Clear the scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    pass

# ---------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------

def make_skin_material():
    mat = bpy.data.materials.new("Deep Olive Speckled Skin")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    vor = nodes.new("ShaderNodeTexVoronoi")
    ramp = nodes.new("ShaderNodeValToRGB")
    noise = nodes.new("ShaderNodeTexNoise")
    bump = nodes.new("ShaderNodeBump")

    vor.voronoi_dimensions = '3D'
    vor.feature = 'F1'
    vor.distance = 'EUCLIDEAN'
    vor.inputs["Scale"].default_value = 13.0
    vor.inputs["Randomness"].default_value = 1.0

    ramp.color_ramp.interpolation = 'EASE'
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    e0 = ramp.color_ramp.elements[0]
    e0.position = 0.075
    e0.color = (0.012, 0.018, 0.006, 1.0)
    e1 = ramp.color_ramp.elements.new(0.145)
    e1.color = (0.095, 0.145, 0.025, 1.0)
    e2 = ramp.color_ramp.elements.new(0.22)
    e2.color = (0.20, 0.27, 0.055, 1.0)
    e3 = ramp.color_ramp.elements.new(0.62)
    e3.color = (0.16, 0.22, 0.04, 1.0)

    noise.noise_dimensions = '3D'
    noise.inputs["Scale"].default_value = 38.0
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.78

    bump.inputs["Strength"].default_value = 0.32
    bump.inputs["Distance"].default_value = 0.065
    bsdf.inputs["Roughness"].default_value = 0.78
    bsdf.inputs["Specular IOR Level"].default_value = 0.28

    links.new(texcoord.outputs["Generated"], vor.inputs["Vector"])
    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def simple_material(name, color, roughness=0.6, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat

skin_mat = make_skin_material()
yellow_mat = simple_material("Yellow Green Eyes", (0.58, 0.72, 0.08, 1.0), 0.42)
pupil_mat = simple_material("Dark Pupils and Mouth", (0.003, 0.006, 0.002, 1.0), 0.55)
ridge_mat = simple_material("Olive Spine Ridge", (0.11, 0.17, 0.025, 1.0), 0.8)
dark_spot_mat = simple_material("Raised Dark Speckles", (0.018, 0.028, 0.008, 1.0), 0.85)

created = []

# ---------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------

def smooth_mesh(obj):
    if obj.type == 'MESH':
        for poly in obj.data.polygons:
            poly.use_smooth = True

def uv_sphere(name, location, scale, material, segments=40, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_mesh(obj)
    obj.data.materials.append(material)
    created.append(obj)
    return obj

def ico_sphere(name, location, radius, material, subdivisions=2, scale=None):
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=subdivisions,
        radius=radius,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    if scale:
        obj.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_mesh(obj)
    obj.data.materials.append(material)
    created.append(obj)
    return obj

def tapered_segment(name, start, end, r_start, r_end, material, vertices=16):
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    length = direction.length
    midpoint = (start + end) * 0.5
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=r_start,
        radius2=r_end,
        depth=length,
        location=midpoint
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    smooth_mesh(obj)
    obj.data.materials.append(material)
    bevel = obj.modifiers.new("Soft organic edge", 'BEVEL')
    bevel.width = min(r_start, r_end) * 0.22
    bevel.segments = 2
    created.append(obj)
    return obj

def curve_line(name, points, bevel, material, resolution=2):
    curve = bpy.data.curves.new(name + "Curve", 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = resolution
    curve.bevel_depth = bevel
    curve.bevel_resolution = 3
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(points) - 1)
    for bp, co in zip(spline.bezier_points, points):
        bp.co = co
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    created.append(obj)
    return obj

def tapered_tail(name, centers, radii, material, sides=24, vertical_scale=0.72):
    verts = []
    faces = []
    count = len(centers)

    for i, center in enumerate(centers):
        c = Vector(center)
        if i == 0:
            tangent = Vector(centers[1]) - c
        elif i == count - 1:
            tangent = c - Vector(centers[i - 1])
        else:
            tangent = Vector(centers[i + 1]) - Vector(centers[i - 1])
        tangent.normalize()

        horizontal_normal = Vector((-tangent.y, tangent.x, 0.0))
        if horizontal_normal.length < 0.01:
            horizontal_normal = Vector((1, 0, 0))
        horizontal_normal.normalize()
        vertical = Vector((0, 0, 1))

        for j in range(sides):
            angle = 2.0 * math.pi * j / sides
            offset = (
                horizontal_normal * math.cos(angle) * radii[i] +
                vertical * math.sin(angle) * radii[i] * vertical_scale
            )
            verts.append(tuple(c + offset))

    for i in range(count - 1):
        for j in range(sides):
            a = i * sides + j
            b = i * sides + (j + 1) % sides
            c = (i + 1) * sides + (j + 1) % sides
            d = (i + 1) * sides + j
            faces.append((a, b, c, d))

    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple((count - 1) * sides + j for j in range(sides)))

    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    smooth_mesh(obj)
    created.append(obj)
    return obj

# ---------------------------------------------------------------------
# Main torso, neck, and head
# ---------------------------------------------------------------------

body = uv_sphere(
    "Wide Flattened Torso",
    (0.0, 0.15, 0.58),
    (1.22, 2.18, 0.49),
    skin_mat,
    64,
    32
)

chest = uv_sphere(
    "Compressed Shoulder Girdle",
    (0.0, 1.62, 0.61),
    (0.91, 0.98, 0.43),
    skin_mat,
    48,
    28
)

neck = uv_sphere(
    "Short Neck",
    (0.0, 2.17, 0.65),
    (0.63, 0.72, 0.36),
    skin_mat,
    44,
    26
)

head = uv_sphere(
    "Small Rounded Head",
    (0.0, 2.73, 0.72),
    (0.76, 0.79, 0.43),
    skin_mat,
    56,
    30
)

snout = uv_sphere(
    "Rounded Snout",
    (0.0, 3.27, 0.65),
    (0.59, 0.56, 0.31),
    skin_mat,
    48,
    26
)

# ---------------------------------------------------------------------
# Long tapered tail
# ---------------------------------------------------------------------

tail_centers = []
tail_radii = []
tail_steps = 48
for i in range(tail_steps):
    t = i / (tail_steps - 1)
    y = -1.72 - 7.15 * t
    x = 0.34 * math.sin(math.pi * t) - 0.12 * math.sin(2.4 * math.pi * t) * t
    z = 0.54 - 0.25 * t + 0.025 * math.sin(math.pi * t)
    tail_centers.append((x, y, z))
    tail_radii.append(0.46 * ((1.0 - t) ** 1.42) + 0.025)

tail = tapered_tail("Extremely Long Tapered Tail", tail_centers, tail_radii, skin_mat)

# ---------------------------------------------------------------------
# Limbs and grasping feet
# ---------------------------------------------------------------------

def make_limb(side, front=True):
    s = 1.0 if side == "Left" else -1.0
    if front:
        hip = (s * 0.84, 1.30, 0.52)
        elbow = (s * 1.43, 1.55, 0.37)
        wrist = (s * 1.76, 1.15, 0.25)
        foot_center = (s * 1.88, 1.05, 0.22)
        label = side + " Front"
        toe_forward = 0.28
    else:
        hip = (s * 0.98, -1.05, 0.50)
        elbow = (s * 1.52, -1.28, 0.34)
        wrist = (s * 1.77, -1.71, 0.22)
        foot_center = (s * 1.85, -1.86, 0.20)
        label = side + " Hind"
        toe_forward = -0.27

    tapered_segment(label + " Upper Limb", hip, elbow, 0.22, 0.17, skin_mat, 18)
    uv_sphere(label + " Elbow", elbow, (0.21, 0.20, 0.17), skin_mat, 28, 16)
    tapered_segment(label + " Fore Limb", elbow, wrist, 0.17, 0.115, skin_mat, 16)
    uv_sphere(label + " Grasping Palm", foot_center, (0.22, 0.28, 0.125), skin_mat, 28, 16)

    base_x = foot_center[0]
    base_y = foot_center[1]
    base_z = foot_center[2]
    toe_specs = [
        (0.17 * s, toe_forward + 0.14, 0.0),
        (0.27 * s, toe_forward, -0.01),
        (0.22 * s, -toe_forward * 0.76, 0.0),
        (0.10 * s, -toe_forward * 1.00, 0.01),
    ]
    for n, (dx, dy, dz) in enumerate(toe_specs):
        start = (
            base_x + 0.07 * s,
            base_y + (0.05 if dy > 0 else -0.05),
            base_z
        )
        bend = (
            base_x + dx * 0.58,
            base_y + dy * 0.55,
            base_z + 0.015
        )
        end = (
            base_x + dx,
            base_y + dy,
            base_z + dz
        )
        tapered_segment(label + " Toe %02dA" % n, start, bend, 0.055, 0.042, skin_mat, 12)
        tapered_segment(label + " Toe %02dB" % n, bend, end, 0.043, 0.018, skin_mat, 12)

for limb_side in ("Left", "Right"):
    make_limb(limb_side, True)
    make_limb(limb_side, False)

# ---------------------------------------------------------------------
# Spine ridge
# ---------------------------------------------------------------------

ridge_verts = []
ridge_faces = []
ridge_sections = 30
for i in range(ridge_sections):
    y = -1.65 + i * (4.35 / (ridge_sections - 1))
    if y < 0.15:
        q = (y - 0.15) / 2.18
        top = 0.58 + 0.49 * math.sqrt(max(0.0, 1.0 - q * q))
    elif y < 1.8:
        q = (y - 0.35) / 2.1
        top = 0.60 + 0.49 * math.sqrt(max(0.0, 1.0 - q * q))
    else:
        q = (y - 2.55) / 1.2
        top = 0.69 + 0.38 * math.sqrt(max(0.0, 1.0 - q * q))
    height = 0.055 + 0.045 * math.sin(math.pi * i / (ridge_sections - 1))
    width = 0.055
    ridge_verts.extend([
        (-width, y, top - 0.005),
        (0.0, y, top + height),
        (width, y, top - 0.005)
    ])

for i in range(ridge_sections - 1):
    a = i * 3
    b = (i + 1) * 3
    ridge_faces.extend([
        (a, b, b + 1, a + 1),
        (a + 1, b + 1, b + 2, a + 2)
    ])

mesh = bpy.data.meshes.new("SubtleSpinalRidgeMesh")
mesh.from_pydata(ridge_verts, [], ridge_faces)
mesh.update()
ridge_obj = bpy.data.objects.new("Subtle Spine Ridge", mesh)
bpy.context.collection.objects.link(ridge_obj)
ridge_obj.data.materials.append(ridge_mat)
created.append(ridge_obj)

# ---------------------------------------------------------------------
# Prominent turret eyes, pupils, nostrils, and mouth seam
# ---------------------------------------------------------------------

for s, side in ((1.0, "Left"), (-1.0, "Right")):
    turret_center = (s * 0.59, 2.78, 0.91)
    globe_center = (s * 0.72, 2.80, 1.00)
    uv_sphere(side + " Eye Turret", turret_center, (0.37, 0.34, 0.31), skin_mat, 40, 24)
    uv_sphere(side + " Yellow Green Eye", globe_center, (0.255, 0.245, 0.235), yellow_mat, 40, 24)

    look = Vector((s * 0.52, 0.18, 0.83)).normalized()
    pupil_center = Vector(globe_center) + look * 0.215
    uv_sphere(side + " Round Pupil", pupil_center, (0.084, 0.055, 0.075), pupil_mat, 28, 16)

    nostril = (s * 0.34, 3.64, 0.76)
    uv_sphere(side + " Nostril", nostril, (0.043, 0.033, 0.026), pupil_mat, 20, 12)

curve_line(
    "Left Mouth Seam",
    [(-0.52, 3.29, 0.63), (-0.47, 3.55, 0.61), (-0.20, 3.69, 0.60)],
    0.014,
    pupil_mat
)
curve_line(
    "Right Mouth Seam",
    [(0.52, 3.29, 0.63), (0.47, 3.55, 0.61), (0.20, 3.69, 0.60)],
    0.014,
    pupil_mat
)

# ---------------------------------------------------------------------
# Small raised skin granules on the most visible upper surfaces
# ---------------------------------------------------------------------

def scatter_surface_bumps(center, radii, amount, name_prefix):
    cx, cy, cz = center
    rx, ry, rz = radii
    for i in range(amount):
        angle = random.uniform(0.0, math.tau)
        radial = math.sqrt(random.uniform(0.04, 0.94))
        nx = radial * math.cos(angle)
        ny = radial * math.sin(angle)
        nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))
        x = cx + rx * nx
        y = cy + ry * ny
        z = cz + rz * nz
        radius = random.uniform(0.022, 0.052)
        material = dark_spot_mat if random.random() < 0.24 else skin_mat
        ico_sphere(
            name_prefix + " Granule %03d" % i,
            (x, y, z + radius * 0.25),
            radius,
            material,
            subdivisions=1,
            scale=(1.0, 1.0, random.uniform(0.55, 0.95))
        )

scatter_surface_bumps((0.0, 0.15, 0.58), (1.19, 2.10, 0.48), 62, "Torso")
scatter_surface_bumps((0.0, 2.72, 0.72), (0.72, 0.72, 0.41), 22, "Head")
scatter_surface_bumps((0.0, 3.25, 0.65), (0.55, 0.50, 0.29), 10, "Snout")

# A sparse row of minute tail granules reinforces the leathery surface.
for i in range(5, tail_steps - 5, 3):
    c = Vector(tail_centers[i])
    r = tail_radii[i]
    offset_x = random.uniform(-0.55, 0.55) * r
    z_surface = c.z + r * 0.70 * math.sqrt(max(0.0, 1.0 - (offset_x / max(r, 0.001)) ** 2))
    ico_sphere(
        "Tail Granule %03d" % i,
        (c.x + offset_x, c.y, z_surface),
        max(0.012, min(0.034, r * 0.11)),
        dark_spot_mat if random.random() < 0.3 else skin_mat,
        subdivisions=1,
        scale=(1.0, 1.0, 0.7)
    )

# ---------------------------------------------------------------------
# Place the complete creature at the origin with its lowest point at Z=0.
# ---------------------------------------------------------------------

bpy.context.view_layer.update()

min_corner = Vector((1e9, 1e9, 1e9))
max_corner = Vector((-1e9, -1e9, -1e9))
for obj in created:
    if obj.type not in {'MESH', 'CURVE'}:
        continue
    for corner in obj.bound_box:
        world_corner = obj.matrix_world @ Vector(corner)
        min_corner.x = min(min_corner.x, world_corner.x)
        min_corner.y = min(min_corner.y, world_corner.y)
        min_corner.z = min(min_corner.z, world_corner.z)
        max_corner.x = max(max_corner.x, world_corner.x)
        max_corner.y = max(max_corner.y, world_corner.y)
        max_corner.z = max(max_corner.z, world_corner.z)

offset = Vector((
    -(min_corner.x + max_corner.x) * 0.5,
    -(min_corner.y + max_corner.y) * 0.5,
    -min_corner.z
))
for obj in created:
    obj.location += offset

# Set a sensible viewport presentation without adding cameras or lights.
bpy.context.scene.world.color = (0.035, 0.035, 0.035)
for obj in bpy.context.selected_objects:
    obj.select_set(False)
if body:
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
