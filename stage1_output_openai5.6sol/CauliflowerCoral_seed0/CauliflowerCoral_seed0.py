import bpy
import math
import random
from mathutils import Vector

random.seed(1847)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for datablocks in (
    bpy.data.meshes,
    bpy.data.curves,
    bpy.data.metaballs,
    bpy.data.materials,
    bpy.data.cameras,
    bpy.data.lights
):
    for datablock in list(datablocks):
        if datablock.users == 0:
            datablocks.remove(datablock)

vertices = []
faces = []
face_materials = []

def add_face(indices, material_index):
    faces.append(tuple(indices))
    face_materials.append(material_index)

def make_basis(axis):
    w = Vector(axis).normalized()
    reference = Vector((0.0, 0.0, 1.0))
    if abs(w.dot(reference)) > 0.92:
        reference = Vector((1.0, 0.0, 0.0))
    u = reference.cross(w).normalized()
    v = w.cross(u).normalized()
    return u, v, w

def rough_factor(theta, phi, seed, amount):
    wave = (
        0.46 * math.sin(theta * 5.0 + seed * 0.37) * math.sin(phi * 4.0 + 0.8)
        + 0.28 * math.cos(theta * 9.0 - phi * 6.0 + seed * 0.71)
        + 0.18 * math.sin(theta * 14.0 + phi * 9.0 + seed)
        + 0.08 * math.cos(theta * 23.0 - phi * 13.0)
    )
    return 1.0 + amount * wave

def append_ellipsoid(center, radii, axis=(0.0, 0.0, 1.0),
                     segments=14, rings=9, seed=0.0,
                     material_index=0, roughness=0.035):
    center = Vector(center)
    rx, ry, rz = radii
    u, v, w = make_basis(axis)
    start = len(vertices)

    vertices.append(tuple(center + w * rz * rough_factor(0.0, 0.0, seed, roughness)))

    for ring in range(1, rings):
        phi = math.pi * ring / rings
        sp = math.sin(phi)
        cp = math.cos(phi)
        for segment in range(segments):
            theta = math.tau * segment / segments
            ct = math.cos(theta)
            st = math.sin(theta)
            factor = rough_factor(theta, phi, seed, roughness)
            factor *= 1.0 + random.uniform(-roughness * 0.12, roughness * 0.12)
            point = (
                center
                + u * (rx * sp * ct * factor)
                + v * (ry * sp * st * factor)
                + w * (rz * cp * factor)
            )
            vertices.append(tuple(point))

    bottom = len(vertices)
    vertices.append(tuple(center - w * rz * rough_factor(0.0, math.pi, seed, roughness)))

    first_ring = start + 1
    for segment in range(segments):
        nxt = (segment + 1) % segments
        add_face((start, first_ring + segment, first_ring + nxt), material_index)

    for ring in range(rings - 2):
        current = first_ring + ring * segments
        following = current + segments
        for segment in range(segments):
            nxt = (segment + 1) % segments
            add_face((
                current + segment,
                following + segment,
                following + nxt,
                current + nxt
            ), material_index)

    final_ring = first_ring + (rings - 2) * segments
    for segment in range(segments):
        nxt = (segment + 1) % segments
        add_face((final_ring + segment, bottom, final_ring + nxt), material_index)

    return {
        "center": center,
        "radii": (rx, ry, rz),
        "basis": (u, v, w)
    }

golden = (1.0 + math.sqrt(5.0)) * 0.5
ico_raw = [
    (-1, golden, 0), (1, golden, 0), (-1, -golden, 0), (1, -golden, 0),
    (0, -1, golden), (0, 1, golden), (0, -1, -golden), (0, 1, -golden),
    (golden, 0, -1), (golden, 0, 1), (-golden, 0, -1), (-golden, 0, 1)
]
ico_vertices = [Vector(p).normalized() for p in ico_raw]
ico_faces = [
    (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
    (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
    (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
    (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)
]

def append_granule(center, normal, radius, material_index):
    center = Vector(center)
    normal = Vector(normal).normalized()
    u, v, w = make_basis(normal)
    start = len(vertices)

    sx = radius * random.uniform(0.82, 1.12)
    sy = radius * random.uniform(0.82, 1.12)
    sz = radius * random.uniform(0.90, 1.28)
    rotation = random.random() * math.tau
    cr = math.cos(rotation)
    sr = math.sin(rotation)

    for p in ico_vertices:
        x = p.x * cr - p.y * sr
        y = p.x * sr + p.y * cr
        jitter = random.uniform(0.94, 1.06)
        point = center + u * (x * sx * jitter) + v * (y * sy * jitter) + w * (p.z * sz * jitter)
        vertices.append(tuple(point))

    for face in ico_faces:
        add_face((start + face[0], start + face[1], start + face[2]), material_index)

def ellipsoid_surface(shape, direction):
    q = Vector(direction).normalized()
    center = shape["center"]
    rx, ry, rz = shape["radii"]
    u, v, w = shape["basis"]

    point = center + u * (q.x * rx) + v * (q.y * ry) + w * (q.z * rz)
    normal = (
        u * (q.x / max(rx, 0.001))
        + v * (q.y / max(ry, 0.001))
        + w * (q.z / max(rz, 0.001))
    ).normalized()
    return point, normal

def scatter_fine_polyps(shape, count, size_range, lower_limit=-0.42):
    for _ in range(count):
        azimuth = random.random() * math.tau
        local_z = random.uniform(lower_limit, 1.0)
        radial = math.sqrt(max(0.0, 1.0 - local_z * local_z))
        direction = Vector((
            math.cos(azimuth) * radial,
            math.sin(azimuth) * radial,
            local_z
        ))
        point, normal = ellipsoid_surface(shape, direction)
        radius = random.uniform(*size_range)
        center = point + normal * radius * 0.08
        material = random.choice((0, 1, 1, 1, 2, 3))
        append_granule(center, normal, radius, material)

def add_clustered_nubs(shape, groups=2):
    for _ in range(groups):
        azimuth = random.random() * math.tau
        local_z = random.uniform(0.20, 0.95)
        radial = math.sqrt(max(0.0, 1.0 - local_z * local_z))
        direction = Vector((math.cos(azimuth) * radial, math.sin(azimuth) * radial, local_z))
        point, normal = ellipsoid_surface(shape, direction)
        tangent_a = normal.cross(Vector((0.0, 0.0, 1.0)))
        if tangent_a.length < 0.08:
            tangent_a = normal.cross(Vector((1.0, 0.0, 0.0)))
        tangent_a.normalize()
        tangent_b = normal.cross(tangent_a).normalized()
        base_size = random.uniform(0.027, 0.042)

        for index in range(random.choice((3, 4))):
            angle = math.tau * index / 3.0 + random.uniform(-0.25, 0.25)
            offset = (
                tangent_a * math.cos(angle)
                + tangent_b * math.sin(angle)
            ) * base_size * random.uniform(0.55, 0.90)
            append_granule(
                point + offset + normal * base_size * 0.06,
                normal,
                base_size * random.uniform(0.72, 1.04),
                random.choice((1, 1, 2))
            )

base_main = append_ellipsoid(
    (0.0, 0.0, 0.39),
    (2.52, 2.02, 0.43),
    segments=28,
    rings=12,
    seed=2.4,
    material_index=0,
    roughness=0.055
)
base_secondary = append_ellipsoid(
    (-0.18, 0.08, 0.51),
    (2.27, 1.79, 0.39),
    axis=(0.03, -0.02, 1.0),
    segments=26,
    rings=11,
    seed=5.2,
    material_index=3,
    roughness=0.065
)
scatter_fine_polyps(base_main, 150, (0.022, 0.040), -0.08)
scatter_fine_polyps(base_secondary, 110, (0.021, 0.039), 0.05)

placements = [(0.0, 0.0, 0.0, 0)]
ring_data = [
    (0.49, 7),
    (1.04, 13),
    (1.62, 19)
]

for ring_index, (radius, count) in enumerate(ring_data, start=1):
    phase = random.uniform(0.0, math.tau)
    for index in range(count):
        angle = phase + math.tau * index / count + random.uniform(-0.13, 0.13)
        r = radius * random.uniform(0.88, 1.10)
        x = math.cos(angle) * r * 1.28
        y = math.sin(angle) * r
        placements.append((x, y, min(1.0, r / 1.78), ring_index))

for index, (x, y, radial_fraction, ring_index) in enumerate(placements):
    centrality = 1.0 - radial_fraction
    radial = Vector((x / 2.55, y / 2.05, 0.0))
    if radial.length > 0.001:
        radial.normalize()

    width = random.uniform(0.38, 0.52) + centrality * 0.09
    depth = width * random.uniform(0.86, 1.12)
    height_radius = random.uniform(0.48, 0.65) + centrality * random.uniform(0.14, 0.27)

    outward_lean = random.uniform(0.10, 0.28) * radial_fraction
    axis = Vector((
        radial.x * outward_lean + random.uniform(-0.09, 0.09),
        radial.y * outward_lean + random.uniform(-0.09, 0.09),
        1.0
    )).normalized()

    base_norm = min(0.97, (x / 2.52) ** 2 + (y / 2.02) ** 2)
    mound_top = 0.39 + 0.43 * math.sqrt(max(0.0, 1.0 - base_norm))
    center_z = mound_top + height_radius * random.uniform(0.22, 0.34)
    center_z += centrality * 0.14 + random.uniform(-0.06, 0.08)

    center = Vector((
        x + random.uniform(-0.07, 0.07),
        y + random.uniform(-0.07, 0.07),
        center_z
    ))

    body = append_ellipsoid(
        center,
        (width, depth, height_radius),
        axis=axis,
        segments=15,
        rings=10,
        seed=20.0 + index * 1.73,
        material_index=random.choice((0, 0, 0, 3)),
        roughness=random.uniform(0.045, 0.075)
    )
    scatter_fine_polyps(body, random.randint(22, 32), (0.024, 0.045), -0.55)
    add_clustered_nubs(body, random.choice((1, 2)))

    u, v, w = body["basis"]
    crown_origin = center + w * height_radius * 0.76
    crown_shapes = []

    central_radius = width * random.uniform(0.38, 0.50)
    central_shape = append_ellipsoid(
        crown_origin + w * central_radius * 0.18,
        (
            central_radius * random.uniform(0.90, 1.10),
            central_radius * random.uniform(0.90, 1.10),
            central_radius * random.uniform(0.85, 1.12)
        ),
        axis=w,
        segments=12,
        rings=8,
        seed=100.0 + index,
        material_index=random.choice((0, 0, 1, 3)),
        roughness=0.07
    )
    crown_shapes.append(central_shape)

    knob_count = random.choice((5, 6, 7))
    phase = random.random() * math.tau
    for knob_index in range(knob_count):
        angle = phase + math.tau * knob_index / knob_count + random.uniform(-0.18, 0.18)
        knob_radius = width * random.uniform(0.27, 0.38)
        offset_radius = width * random.uniform(0.40, 0.57)
        offset = u * (math.cos(angle) * offset_radius) + v * (math.sin(angle) * offset_radius)
        knob_center = (
            crown_origin
            + offset
            + w * random.uniform(-0.03, 0.12)
        )
        knob_axis = (w + offset.normalized() * random.uniform(0.04, 0.16)).normalized()
        knob_shape = append_ellipsoid(
            knob_center,
            (
                knob_radius * random.uniform(0.88, 1.10),
                knob_radius * random.uniform(0.88, 1.10),
                knob_radius * random.uniform(0.92, 1.20)
            ),
            axis=knob_axis,
            segments=11,
            rings=8,
            seed=200.0 + index * 11.0 + knob_index,
            material_index=random.choice((0, 0, 1, 3)),
            roughness=0.075
        )
        crown_shapes.append(knob_shape)

    for crown_shape in crown_shapes:
        scatter_fine_polyps(crown_shape, random.randint(10, 16), (0.023, 0.043), -0.58)
        if random.random() < 0.70:
            add_clustered_nubs(crown_shape, 1)

min_x = min(v[0] for v in vertices)
max_x = max(v[0] for v in vertices)
min_y = min(v[1] for v in vertices)
max_y = max(v[1] for v in vertices)
min_z = min(v[2] for v in vertices)

offset_x = (min_x + max_x) * 0.5
offset_y = (min_y + max_y) * 0.5
vertices = [(x - offset_x, y - offset_y, z - min_z) for x, y, z in vertices]

mesh = bpy.data.meshes.new("CauliflowerCoral_Geometry")
mesh.from_pydata(vertices, [], faces)
mesh.update()

coral = bpy.data.objects.new("Cauliflower_Coral", mesh)
bpy.context.collection.objects.link(coral)

def create_material(name, color, roughness):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = (*color, 1.0)
        principled.inputs["Roughness"].default_value = roughness
        if "IOR" in principled.inputs:
            principled.inputs["IOR"].default_value = 1.36
    return material

materials = [
    create_material("Warm Sandy Beige", (0.57, 0.46, 0.33), 0.91),
    create_material("Pale Tan Polyp Tips", (0.69, 0.59, 0.44), 0.93),
    create_material("Faint Green Gray Undertone", (0.46, 0.48, 0.39), 0.94),
    create_material("Warm Crevice Tan", (0.43, 0.34, 0.25), 0.95)
]

for material in materials:
    coral.data.materials.append(material)

for polygon, material_index in zip(mesh.polygons, face_materials):
    polygon.material_index = material_index
    polygon.use_smooth = True

coral.select_set(True)
bpy.context.view_layer.objects.active = coral
bpy.context.collection.name = "Cauliflower Coral"
coral["description"] = "Dense low cauliflower coral with interlocking rounded lobes and fine granular polyps"
coral["procedural_seed"] = 1847