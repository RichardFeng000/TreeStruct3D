import bpy
import math
import random

from mathutils import Vector

# Clear the scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    if datablocks != bpy.data.materials:
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)

random.seed(1847)

def make_woody_material(name, colors, noise_scale, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (760, 0)

    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (500, 0)
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["IOR"].default_value = 1.47
    principled.inputs["Specular IOR Level"].default_value = 0.28

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-900, 0)

    noise_large = nodes.new("ShaderNodeTexNoise")
    noise_large.location = (-680, 120)
    noise_large.noise_dimensions = '3D'
    noise_large.inputs["Scale"].default_value = noise_scale
    noise_large.inputs["Detail"].default_value = 5.0
    noise_large.inputs["Roughness"].default_value = 0.72
    noise_large.inputs["Lacunarity"].default_value = 2.15
    noise_large.inputs["Distortion"].default_value = 0.22

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-420, 160)
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    e0 = ramp.color_ramp.elements[0]
    e0.position = 0.18
    e0.color = colors[0]

    e1 = ramp.color_ramp.elements.new(0.48)
    e1.color = colors[1]

    e2 = ramp.color_ramp.elements.new(0.76)
    e2.color = colors[2]

    noise_fine = nodes.new("ShaderNodeTexNoise")
    noise_fine.location = (-670, -210)
    noise_fine.noise_dimensions = '3D'
    noise_fine.inputs["Scale"].default_value = 58.0
    noise_fine.inputs["Detail"].default_value = 3.2
    noise_fine.inputs["Roughness"].default_value = 0.78
    noise_fine.inputs["Lacunarity"].default_value = 2.35

    wave = nodes.new("ShaderNodeTexWave")
    wave.location = (-665, -430)
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Z'
    wave.inputs["Scale"].default_value = 13.0
    wave.inputs["Distortion"].default_value = 6.5
    wave.inputs["Detail"].default_value = 4.0
    wave.inputs["Detail Scale"].default_value = 2.0

    mix = nodes.new("ShaderNodeMixRGB")
    mix.location = (-370, -220)
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 0.62

    bump = nodes.new("ShaderNodeBump")
    bump.location = (255, -135)
    bump.inputs["Strength"].default_value = 0.36
    bump.inputs["Distance"].default_value = 0.055
    bump.inputs["Invert"].default_value = False

    links.new(texcoord.outputs["Generated"], noise_large.inputs["Vector"])
    links.new(texcoord.outputs["Generated"], noise_fine.inputs["Vector"])
    links.new(texcoord.outputs["Generated"], wave.inputs["Vector"])
    links.new(noise_large.outputs["Fac"], ramp.inputs["Fac"])
    links.new(noise_fine.outputs["Fac"], mix.inputs[1])
    links.new(wave.outputs["Color"], mix.inputs[2])
    links.new(mix.outputs["Color"], bump.inputs["Height"])
    links.new(ramp.outputs["Color"], principled.inputs["Base Color"])
    links.new(bump.outputs["Normal"], principled.inputs["Normal"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    return mat

materials = [
    make_woody_material(
        "Deep umber wood",
        (
            (0.025, 0.010, 0.004, 1.0),
            (0.105, 0.037, 0.012, 1.0),
            (0.245, 0.095, 0.028, 1.0),
        ),
        5.2,
        0.65,
    ),
    make_woody_material(
        "Warm brown wood",
        (
            (0.040, 0.014, 0.005, 1.0),
            (0.155, 0.052, 0.014, 1.0),
            (0.330, 0.125, 0.035, 1.0),
        ),
        5.8,
        0.62,
    ),
    make_woody_material(
        "Aged brown wood",
        (
            (0.020, 0.009, 0.004, 1.0),
            (0.090, 0.030, 0.010, 1.0),
            (0.205, 0.073, 0.020, 1.0),
        ),
        6.5,
        0.69,
    ),
    make_woody_material(
        "Scale tips",
        (
            (0.012, 0.006, 0.003, 1.0),
            (0.060, 0.020, 0.007, 1.0),
            (0.150, 0.052, 0.014, 1.0),
        ),
        7.5,
        0.73,
    ),
]

vertices = []
faces = []
face_materials = []
face_smooth = []

def add_face(indices, material_index=0, smooth=True):
    faces.append(tuple(indices))
    face_materials.append(material_index)
    face_smooth.append(smooth)

# Dense tapered inner core, visible only in the deepest gaps.
core_segments = 32
core_rings = 24
core_ring_indices = []

bottom_z = -1.72
top_z = 1.78

bottom_pole = len(vertices)
vertices.append((0.0, 0.0, bottom_z))

for ring in range(1, core_rings):
    s = ring / core_rings
    z = bottom_z + (top_z - bottom_z) * s
    envelope = math.sin(math.pi * s) ** 0.72
    radius = 0.15 + 0.31 * envelope * (1.0 - 0.10 * s)
    ring_ids = []
    for j in range(core_segments):
        angle = 2.0 * math.pi * j / core_segments
        radial_jitter = 1.0 + 0.018 * math.sin(5.0 * angle + 9.0 * s)
        ring_ids.append(len(vertices))
        vertices.append((
            radius * radial_jitter * math.cos(angle),
            radius * radial_jitter * math.sin(angle),
            z,
        ))
    core_ring_indices.append(ring_ids)

top_pole = len(vertices)
vertices.append((0.0, 0.0, top_z))

first_ring = core_ring_indices[0]
for j in range(core_segments):
    add_face(
        (bottom_pole, first_ring[(j + 1) % core_segments], first_ring[j]),
        0,
        True,
    )

for r in range(len(core_ring_indices) - 1):
    a = core_ring_indices[r]
    b = core_ring_indices[r + 1]
    for j in range(core_segments):
        add_face(
            (a[j], a[(j + 1) % core_segments],
             b[(j + 1) % core_segments], b[j]),
            0,
            True,
        )

last_ring = core_ring_indices[-1]
for j in range(core_segments):
    add_face(
        (last_ring[j], last_ring[(j + 1) % core_segments], top_pole),
        0,
        True,
    )

# Individual overlapping scales follow a golden-angle phyllotactic spiral.
scale_count = 172
golden_angle = math.radians(137.50776405)

row_t = (0.0, 0.17, 0.35, 0.54, 0.72, 0.88, 1.0)
row_width = (0.18, 0.48, 0.80, 1.00, 0.94, 0.58, 0.10)
row_out = (0.00, 0.035, 0.12, 0.28, 0.55, 0.82, 1.00)
row_z = (0.43, 0.34, 0.21, 0.05, -0.13, -0.29, -0.40)
columns = 7

for i in range(scale_count):
    s = (i + 0.48) / scale_count
    body = math.sin(math.pi * s) ** 0.58

    center_z = -1.55 + 3.28 * s
    angle = i * golden_angle
    angle += 0.025 * math.sin(i * 0.91) + random.uniform(-0.012, 0.012)

    radial = Vector((math.cos(angle), math.sin(angle), 0.0))
    tangent = Vector((-math.sin(angle), math.cos(angle), 0.0))

    attachment_radius = 0.20 + 0.67 * body * (1.0 - 0.13 * s)
    attachment_radius += 0.018 * math.sin(i * 1.71)

    scale_width = (0.31 + 0.18 * body) * random.uniform(0.91, 1.08)
    scale_length = (0.42 + 0.22 * body) * random.uniform(0.92, 1.08)

    top_closure = max(0.0, (s - 0.78) / 0.22)
    bottom_closure = max(0.0, (0.10 - s) / 0.10)
    projection = (0.20 + 0.31 * body)
    projection *= (1.0 - 0.52 * top_closure)
    projection *= (1.0 - 0.18 * bottom_closure)
    projection *= random.uniform(0.91, 1.08)

    thickness = (0.038 + 0.018 * body) * random.uniform(0.90, 1.10)
    scale_mat = random.choices((0, 1, 2), weights=(0.26, 0.47, 0.27), k=1)[0]

    top_grid = []
    bottom_grid = []

    for r, t in enumerate(row_t):
        half_width = scale_width * row_width[r]
        top_row = []
        bottom_row = []

        for c in range(columns):
            q = -1.0 + 2.0 * c / (columns - 1)
            x = half_width * q

            cross_crown = (0.050 + 0.050 * body) * max(0.0, 1.0 - q * q)
            longitudinal_keel = (
                0.052
                * math.exp(-((t - 0.72) / 0.27) ** 2)
                * max(0.0, 1.0 - abs(q) ** 1.5)
            )
            woody_irregularity = (
                0.007 * math.sin(i * 2.3 + r * 1.7 + c * 2.1)
                + random.uniform(-0.0035, 0.0035)
            )

            outward = (
                attachment_radius
                + projection * row_out[r]
                + cross_crown
                + longitudinal_keel
                + woody_irregularity
            )

            z = center_z + scale_length * row_z[r]
            z += 0.012 * math.sin(q * math.pi + i * 0.37) * body
            x += 0.014 * math.sin(i * 0.63 + t * 4.0) * t

            top_position = radial * outward + tangent * x + Vector((0.0, 0.0, z))
            bottom_position = (
                radial * (outward - thickness)
                + tangent * x
                + Vector((0.0, 0.0, z - 0.012))
            )

            top_row.append(len(vertices))
            vertices.append(tuple(top_position))
            bottom_row.append(len(vertices))
            vertices.append(tuple(bottom_position))

        top_grid.append(top_row)
        bottom_grid.append(bottom_row)

    for r in range(len(row_t) - 1):
        for c in range(columns - 1):
            add_face(
                (
                    top_grid[r][c],
                    top_grid[r][c + 1],
                    top_grid[r + 1][c + 1],
                    top_grid[r + 1][c],
                ),
                scale_mat,
                True,
            )
            add_face(
                (
                    bottom_grid[r][c + 1],
                    bottom_grid[r][c],
                    bottom_grid[r + 1][c],
                    bottom_grid[r + 1][c + 1],
                ),
                scale_mat,
                True,
            )

    # Closed woody edges.
    for r in range(len(row_t) - 1):
        add_face(
            (
                top_grid[r][0],
                top_grid[r + 1][0],
                bottom_grid[r + 1][0],
                bottom_grid[r][0],
            ),
            scale_mat,
            False,
        )
        add_face(
            (
                top_grid[r + 1][-1],
                top_grid[r][-1],
                bottom_grid[r][-1],
                bottom_grid[r + 1][-1],
            ),
            scale_mat,
            False,
        )

    for c in range(columns - 1):
        add_face(
            (
                top_grid[0][c + 1],
                top_grid[0][c],
                bottom_grid[0][c],
                bottom_grid[0][c + 1],
            ),
            scale_mat,
            False,
        )
        add_face(
            (
                top_grid[-1][c],
                top_grid[-1][c + 1],
                bottom_grid[-1][c + 1],
                bottom_grid[-1][c],
            ),
            3,
            False,
        )

    # Raised polygonal apophysis at the exposed end of each woody scale.
    boss_t = 0.76
    boss_out = (
        attachment_radius
        + projection * 0.64
        + 0.075
        + 0.030 * body
    )
    boss_z = center_z - 0.17 * scale_length
    boss_half_width = 0.115 * (0.72 + 0.28 * body)
    boss_half_height = 0.095 * (0.76 + 0.24 * body)

    boss_ring = []
    boss_sides = 8
    for k in range(boss_sides):
        a = 2.0 * math.pi * k / boss_sides
        x = boss_half_width * math.cos(a)
        z_offset = boss_half_height * math.sin(a)
        ring_out = boss_out + 0.012 * math.cos(2.0 * a)
        position = radial * ring_out + tangent * x + Vector((0.0, 0.0, boss_z + z_offset))
        boss_ring.append(len(vertices))
        vertices.append(tuple(position))

    peak = len(vertices)
    peak_position = (
        radial * (boss_out + 0.105 + 0.035 * body)
        + Vector((0.0, 0.0, boss_z - 0.010))
    )
    vertices.append(tuple(peak_position))

    for k in range(boss_sides):
        add_face(
            (boss_ring[k], boss_ring[(k + 1) % boss_sides], peak),
            3 if random.random() < 0.78 else scale_mat,
            True,
        )

mesh = bpy.data.meshes.new("Pinecone_Geometry")
mesh.from_pydata(vertices, [], faces)
mesh.update(calc_edges=True)

pinecone = bpy.data.objects.new("Pinecone", mesh)
bpy.context.collection.objects.link(pinecone)

for mat in materials:
    pinecone.data.materials.append(mat)

for poly, mat_index, smooth in zip(mesh.polygons, face_materials, face_smooth):
    poly.material_index = mat_index
    poly.use_smooth = smooth

# Subtle beveling softens the exposed scale rims without erasing their layered form.
bevel = pinecone.modifiers.new("Soft woody edges", 'BEVEL')
bevel.width = 0.008
bevel.segments = 2
bevel.limit_method = 'ANGLE'
bevel.angle_limit = math.radians(34.0)

pinecone.rotation_euler[2] = math.radians(4.0)

bpy.context.view_layer.objects.active = pinecone
pinecone.select_set(True)