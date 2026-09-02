import bpy
import math
import random
from mathutils import Vector, Euler

random.seed(18473)

# Clear the scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    if datablocks is not bpy.data.materials:
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)

def make_material(name, color, roughness=0.7):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

bark_mat = make_material("Warm Brown Bark", (0.22, 0.075, 0.025, 1.0), 0.92)
dark_bark_mat = make_material("Dark Bark Accents", (0.095, 0.025, 0.009, 1.0), 0.96)
leaf_mats = [
    make_material("Leaf Green", (0.095, 0.35, 0.055, 1.0), 0.82),
    make_material("Leaf Dark Green", (0.035, 0.20, 0.025, 1.0), 0.86),
    make_material("Leaf Light Green", (0.20, 0.48, 0.075, 1.0), 0.78),
    make_material("Leaf Olive Green", (0.15, 0.31, 0.035, 1.0), 0.84),
]
pink_mats = [
    make_material("Flower Pink", (0.95, 0.30, 0.49, 1.0), 0.66),
    make_material("Flower Pale Pink", (1.0, 0.52, 0.66, 1.0), 0.62),
    make_material("Flower Deep Pink", (0.70, 0.095, 0.24, 1.0), 0.70),
]
center_mat = make_material("Flower Centers", (1.0, 0.58, 0.08, 1.0), 0.64)

branch_verts = []
branch_faces = []

def append_tube(points, radii, sides=10):
    points = [Vector(p) for p in points]
    base = len(branch_verts)
    frames = []

    for i, point in enumerate(points):
        if i == 0:
            tangent = (points[1] - points[0]).normalized()
        elif i == len(points) - 1:
            tangent = (points[-1] - points[-2]).normalized()
        else:
            tangent = (points[i + 1] - points[i - 1]).normalized()

        if i == 0:
            reference = Vector((0.0, 0.0, 1.0))
            if abs(tangent.dot(reference)) > 0.88:
                reference = Vector((1.0, 0.0, 0.0))
            axis_a = tangent.cross(reference).normalized()
        else:
            old_a = frames[-1][0]
            axis_a = old_a - tangent * old_a.dot(tangent)
            if axis_a.length < 0.001:
                reference = Vector((1.0, 0.0, 0.0))
                axis_a = tangent.cross(reference)
            axis_a.normalize()
        axis_b = tangent.cross(axis_a).normalized()
        frames.append((axis_a, axis_b))

        for j in range(sides):
            angle = math.tau * j / sides
            uneven = 1.0 + 0.045 * math.sin(j * 3.0 + i * 1.7)
            offset = (axis_a * math.cos(angle) + axis_b * math.sin(angle))
            branch_verts.append(tuple(point + offset * radii[i] * uneven))

    for i in range(len(points) - 1):
        ring_a = base + i * sides
        ring_b = ring_a + sides
        for j in range(sides):
            nj = (j + 1) % sides
            branch_faces.append((ring_a + j, ring_a + nj, ring_b + nj, ring_b + j))

    branch_faces.append(tuple(base + j for j in reversed(range(sides))))
    end = base + (len(points) - 1) * sides
    branch_faces.append(tuple(end + j for j in range(sides)))

# Thick, short, slightly twisted trunk.
trunk_points = [
    Vector((0.00, 0.00, 0.00)),
    Vector((-0.035, 0.025, 0.32)),
    Vector((0.055, -0.035, 0.68)),
    Vector((-0.035, 0.055, 1.02)),
    Vector((0.085, 0.015, 1.36)),
    Vector((0.055, -0.025, 1.68)),
]
append_tube(trunk_points, [0.52, 0.49, 0.45, 0.40, 0.35, 0.30], 14)

# Low root flares, keeping the tree seated at z=0.
for i in range(9):
    angle = math.tau * i / 9.0 + random.uniform(-0.16, 0.16)
    direction = Vector((math.cos(angle), math.sin(angle), 0.0))
    side = Vector((-direction.y, direction.x, 0.0))
    points = [
        Vector((0.0, 0.0, 0.20)) + direction * 0.24,
        direction * random.uniform(0.48, 0.63) + side * random.uniform(-0.08, 0.08) + Vector((0, 0, 0.09)),
        direction * random.uniform(0.88, 1.13) + side * random.uniform(-0.13, 0.13) + Vector((0, 0, 0.035)),
    ]
    append_tube(points, [0.23, 0.115, 0.025], 9)

leaf_anchors = []
flower_candidates = []
junctions = []

crown = Vector((0.055, -0.025, 1.58))

# Radially spreading, upward-curving main limbs with irregular secondary forks.
for i in range(10):
    base_angle = math.tau * i / 10.0 + random.uniform(-0.20, 0.20)
    length = random.uniform(2.05, 2.65)
    lateral = random.uniform(-0.22, 0.22)
    points = [crown + Vector((random.uniform(-0.10, 0.10), random.uniform(-0.10, 0.10), random.uniform(-0.08, 0.11)))]
    for j in range(1, 6):
        t = j / 5.0
        angle = base_angle + lateral * math.sin(t * math.pi) + random.uniform(-0.055, 0.055)
        radial = length * (t ** 0.88)
        sideways = 0.13 * math.sin(t * math.pi * 2.0 + i)
        p = crown + Vector((
            math.cos(angle) * radial - math.sin(angle) * sideways,
            math.sin(angle) * radial + math.cos(angle) * sideways,
            0.20 + 1.02 * math.sin(t * math.pi * 0.52) + random.uniform(-0.07, 0.07)
        ))
        points.append(p)
    append_tube(points, [0.29, 0.255, 0.205, 0.155, 0.105, 0.067], 10)
    junctions.extend([points[0], points[3], points[4]])
    leaf_anchors.append((points[3], 11, 0.50))
    leaf_anchors.append((points[4], 12, 0.46))

    for fork in range(2):
        split_index = 3 if fork == 0 else 4
        start = points[split_index]
        fork_angle = base_angle + (-1 if fork == 0 else 1) * random.uniform(0.31, 0.58)
        fork_length = random.uniform(1.05, 1.48)
        sec = [start]
        for j in range(1, 5):
            t = j / 4.0
            bend = random.uniform(-0.08, 0.08) * t
            a = fork_angle + bend
            sec.append(start + Vector((
                math.cos(a) * fork_length * t,
                math.sin(a) * fork_length * t,
                0.15 * t + 0.30 * math.sin(t * math.pi * 0.55) + random.uniform(-0.035, 0.035)
            )))
        append_tube(sec, [0.115, 0.095, 0.072, 0.048, 0.025], 8)
        junctions.append(start)
        leaf_anchors.append((sec[2], 10, 0.38))
        leaf_anchors.append((sec[3], 12, 0.40))
        flower_candidates.append(sec[-1])

        # Two fine terminal twigs at each secondary branch.
        incoming = (sec[-1] - sec[-2]).normalized()
        incoming_angle = math.atan2(incoming.y, incoming.x)
        for twig_side in (-1, 1):
            twig_angle = incoming_angle + twig_side * random.uniform(0.28, 0.55)
            twig_length = random.uniform(0.48, 0.78)
            twig_start = sec[-1]
            twig = [
                twig_start,
                twig_start + Vector((
                    math.cos(twig_angle) * twig_length * 0.50,
                    math.sin(twig_angle) * twig_length * 0.50,
                    random.uniform(0.08, 0.18)
                )),
                twig_start + Vector((
                    math.cos(twig_angle + random.uniform(-0.10, 0.10)) * twig_length,
                    math.sin(twig_angle + random.uniform(-0.10, 0.10)) * twig_length,
                    random.uniform(0.14, 0.28)
                ))
            ]
            append_tube(twig, [0.041, 0.025, 0.010], 7)
            leaf_anchors.append((twig[-1], random.randint(18, 24), random.uniform(0.34, 0.48)))
            flower_candidates.append(twig[-1])

# Add several smaller crown branches to avoid a hollow canopy center.
for i in range(7):
    angle = math.tau * i / 7.0 + 0.28
    start = crown + Vector((0, 0, random.uniform(-0.05, 0.10)))
    end = start + Vector((math.cos(angle) * random.uniform(1.0, 1.5),
                          math.sin(angle) * random.uniform(1.0, 1.5),
                          random.uniform(0.75, 1.05)))
    mid = (start + end) * 0.5 + Vector((random.uniform(-0.15, 0.15),
                                        random.uniform(-0.15, 0.15),
                                        random.uniform(0.08, 0.20)))
    append_tube([start, mid, end], [0.13, 0.075, 0.022], 8)
    leaf_anchors.append((end, 20, 0.48))
    flower_candidates.append(end)

branch_mesh = bpy.data.meshes.new("Gnarled Branch Structure")
branch_mesh.from_pydata(branch_verts, [], branch_faces)
branch_mesh.update()
branch_obj = bpy.data.objects.new("Short Trunk and Gnarled Branches", branch_mesh)
bpy.context.collection.objects.link(branch_obj)
branch_obj.data.materials.append(bark_mat)
for poly in branch_obj.data.polygons:
    poly.use_smooth = True

# Bark knots at major junctions.
knot_verts = []
knot_faces = []

def append_uv_ellipsoid(vertices, faces, center, scale, rings=5, segments=8):
    center = Vector(center)
    base = len(vertices)
    vertices.append(tuple(center + Vector((0, 0, scale.z))))
    for r in range(1, rings):
        phi = math.pi * r / rings
        for s in range(segments):
            theta = math.tau * s / segments
            vertices.append(tuple(center + Vector((
                scale.x * math.sin(phi) * math.cos(theta),
                scale.y * math.sin(phi) * math.sin(theta),
                scale.z * math.cos(phi)
            ))))
    bottom_index = len(vertices)
    vertices.append(tuple(center - Vector((0, 0, scale.z))))

    first_ring = base + 1
    for s in range(segments):
        faces.append((base, first_ring + s, first_ring + (s + 1) % segments))
    for r in range(rings - 2):
        a = first_ring + r * segments
        b = a + segments
        for s in range(segments):
            ns = (s + 1) % segments
            faces.append((a + s, b + s, b + ns, a + ns))
    last_ring = first_ring + (rings - 2) * segments
    for s in range(segments):
        faces.append((last_ring + s, bottom_index, last_ring + (s + 1) % segments))

for j, p in enumerate(junctions):
    if j % 2 == 0:
        scale = Vector((random.uniform(0.10, 0.16), random.uniform(0.08, 0.13), random.uniform(0.10, 0.18)))
        append_uv_ellipsoid(knot_verts, knot_faces, p + Vector((0, 0, random.uniform(-0.02, 0.04))), scale)

knot_mesh = bpy.data.meshes.new("Natural Branch Knots")
knot_mesh.from_pydata(knot_verts, [], knot_faces)
knot_mesh.update()
knot_obj = bpy.data.objects.new("Bark Knots", knot_mesh)
bpy.context.collection.objects.link(knot_obj)
knot_obj.data.materials.append(dark_bark_mat)
for poly in knot_obj.data.polygons:
    poly.use_smooth = True

leaf_geometry = [{"verts": [], "faces": []} for _ in leaf_mats]
all_leaf_positions = []

def append_lens(geometry, center, length, width, thickness, yaw, tilt_x, tilt_y, points=10):
    verts = geometry["verts"]
    faces = geometry["faces"]
    base = len(verts)
    rotation = Euler((tilt_x, tilt_y, yaw), 'XYZ').to_matrix()
    center = Vector(center)

    for k in range(points):
        a = math.tau * k / points
        # Slightly asymmetric broadleaf outline.
        x = math.cos(a) * length * 0.5
        y = math.sin(a) * width * 0.5 * (0.92 + 0.08 * math.cos(a))
        local = Vector((x, y, 0.0))
        verts.append(tuple(center + rotation @ local))

    top = len(verts)
    verts.append(tuple(center + rotation @ Vector((-0.02 * length, 0.0, thickness))))
    bottom = len(verts)
    verts.append(tuple(center + rotation @ Vector((0.02 * length, 0.0, -thickness * 0.65))))

    for k in range(points):
        nk = (k + 1) % points
        faces.append((base + k, base + nk, top))
        faces.append((base + nk, base + k, bottom))

# Build clustered leaves around terminal branches.
for anchor, count, spread in leaf_anchors:
    for _ in range(count):
        a = random.random() * math.tau
        radius = spread * math.sqrt(random.random())
        offset = Vector((
            math.cos(a) * radius * random.uniform(0.7, 1.25),
            math.sin(a) * radius * random.uniform(0.7, 1.25),
            random.gauss(0.08, spread * 0.32)
        ))
        center = Vector(anchor) + offset
        center.z = max(center.z, 2.18 + random.uniform(-0.08, 0.10))
        length = random.uniform(0.22, 0.34)
        width = length * random.uniform(0.38, 0.52)
        yaw = random.random() * math.tau
        tilt_x = random.uniform(-0.40, 0.40)
        tilt_y = random.uniform(-0.40, 0.40)
        mat_index = random.choices(range(len(leaf_mats)), weights=[42, 25, 21, 12])[0]
        append_lens(leaf_geometry[mat_index], center, length, width,
                    random.uniform(0.012, 0.022), yaw, tilt_x, tilt_y)
        all_leaf_positions.append(center)

# A loose inner layer gives the crown a broad, irregular continuous silhouette.
for _ in range(190):
    angle = random.random() * math.tau
    radius = 0.45 + 2.15 * math.sqrt(random.random())
    boundary_wave = 1.0 + 0.10 * math.sin(angle * 5.0) + 0.07 * math.sin(angle * 9.0 + 1.2)
    radius *= boundary_wave
    center = Vector((
        math.cos(angle) * radius + random.uniform(-0.12, 0.12),
        math.sin(angle) * radius + random.uniform(-0.12, 0.12),
        2.70 + 0.48 * (1.0 - min(radius / 3.0, 1.0)) + random.uniform(-0.22, 0.28)
    ))
    length = random.uniform(0.22, 0.33)
    mat_index = random.choices(range(len(leaf_mats)), weights=[45, 24, 20, 11])[0]
    append_lens(leaf_geometry[mat_index], center, length, length * random.uniform(0.39, 0.52),
                random.uniform(0.012, 0.021), random.random() * math.tau,
                random.uniform(-0.38, 0.38), random.uniform(-0.38, 0.38))
    all_leaf_positions.append(center)

for index, geometry in enumerate(leaf_geometry):
    mesh = bpy.data.meshes.new("Broadleaf Mesh %02d" % index)
    mesh.from_pydata(geometry["verts"], [], geometry["faces"])
    mesh.update()
    obj = bpy.data.objects.new("Small Green Leaves %02d" % index, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(leaf_mats[index])
    for poly in obj.data.polygons:
        poly.use_smooth = True

# Pink flower clusters: each cluster contains several distinct five-petal blossoms.
petal_geometry = [{"verts": [], "faces": []} for _ in pink_mats]
center_verts = []
center_faces = []

random.shuffle(flower_candidates)
cluster_locations = flower_candidates[:28]

# Supplement candidates from upper leaves if needed.
while len(cluster_locations) < 28 and all_leaf_positions:
    cluster_locations.append(random.choice(all_leaf_positions))

for cluster_index, candidate in enumerate(cluster_locations):
    base_center = Vector(candidate) + Vector((
        random.uniform(-0.18, 0.18),
        random.uniform(-0.18, 0.18),
        random.uniform(0.22, 0.38)
    ))
    blossom_count = random.choice((3, 3, 4))
    for b in range(blossom_count):
        ca = math.tau * b / blossom_count + random.uniform(-0.3, 0.3)
        cr = random.uniform(0.04, 0.15)
        flower_center = base_center + Vector((
            math.cos(ca) * cr,
            math.sin(ca) * cr,
            random.uniform(-0.035, 0.08)
        ))
        rotation_offset = random.random() * math.tau
        petal_mat_index = random.choices(range(len(pink_mats)), weights=[50, 35, 15])[0]
        for p in range(5):
            pa = rotation_offset + math.tau * p / 5.0
            petal_center = flower_center + Vector((
                math.cos(pa) * 0.062,
                math.sin(pa) * 0.062,
                random.uniform(-0.005, 0.012)
            ))
            append_lens(
                petal_geometry[petal_mat_index],
                petal_center,
                random.uniform(0.13, 0.17),
                random.uniform(0.070, 0.092),
                random.uniform(0.014, 0.022),
                pa,
                random.uniform(-0.10, 0.10),
                random.uniform(-0.10, 0.10),
                points=8
            )
        append_uv_ellipsoid(
            center_verts,
            center_faces,
            flower_center + Vector((0, 0, 0.022)),
            Vector((0.036, 0.036, 0.025)),
            rings=4,
            segments=7
        )

for index, geometry in enumerate(petal_geometry):
    mesh = bpy.data.meshes.new("Pink Petal Mesh %02d" % index)
    mesh.from_pydata(geometry["verts"], [], geometry["faces"])
    mesh.update()
    obj = bpy.data.objects.new("Scattered Pink Flower Petals %02d" % index, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(pink_mats[index])
    for poly in obj.data.polygons:
        poly.use_smooth = True

center_mesh = bpy.data.meshes.new("Flower Center Mesh")
center_mesh.from_pydata(center_verts, [], center_faces)
center_mesh.update()
center_obj = bpy.data.objects.new("Small Golden Flower Centers", center_mesh)
bpy.context.collection.objects.link(center_obj)
center_obj.data.materials.append(center_mat)
for poly in center_obj.data.polygons:
    poly.use_smooth = True

# Organize the assembly without adding any environmental geometry.
tree_collection = bpy.data.collections.new("Broadleaf Tree Assembly")
bpy.context.scene.collection.children.link(tree_collection)
for obj in list(bpy.context.collection.objects):
    if obj.name in tree_collection.objects:
        continue
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    tree_collection.objects.link(obj)

# Neutral world settings; no camera, light, ground, or backdrop are created.
bpy.context.scene.world.color = (0.05, 0.05, 0.05)
bpy.context.view_layer.objects.active = branch_obj
branch_obj.select_set(True)