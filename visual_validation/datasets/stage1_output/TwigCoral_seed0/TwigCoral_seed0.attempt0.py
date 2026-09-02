import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

random.seed(42)

# Clear scene
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for block in list(bpy.data.meshes):
    bpy.data.meshes.remove(block)
for block in list(bpy.data.materials):
    bpy.data.materials.remove(block)

# Create mesh and object
mesh = bpy.data.meshes.new("TwigCoral")
obj = bpy.data.objects.new("TwigCoral", mesh)
bpy.context.collection.objects.link(obj)

bm = bmesh.new()

# Parameters
CIRCLE_SEGMENTS = 6
BASE_RADIUS = 0.055
TIP_RADIUS = 0.006
MAX_DEPTH = 3


def generate_branch_path(start_pos, direction, length, segments):
    """Generate a curved, irregular path for a branch."""
    points = [Vector(start_pos)]
    pos = Vector(start_pos)
    dir_vec = Vector(direction).normalized()

    rot_axis = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.15, 0.15)))
    if rot_axis.length > 0.001:
        rot_axis.normalize()
    else:
        rot_axis = Vector((0, 1, 0))

    curvature = random.uniform(0.04, 0.14)

    for i in range(segments):
        angle = curvature * (1 + random.uniform(-0.5, 0.5))
        dir_vec.rotate(Matrix.Rotation(angle, 4, rot_axis))

        if random.random() < 0.08:
            new_axis = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.2, 0.2))).normalized()
            dir_vec.rotate(Matrix.Rotation(random.uniform(-0.25, 0.25), 4, new_axis))

        dir_vec.z *= 0.65
        if dir_vec.length > 0.001:
            dir_vec.normalize()

        step = length / segments
        pos += dir_vec * step
        points.append(Vector(pos))

    return points


def build_tube(bm, path, start_radius, end_radius, circle_segments):
    """Build a tapered tube along a path."""
    rings = []
    n = len(path)

    for i, point in enumerate(path):
        t = i / max(n - 1, 1)
        radius = start_radius * (1 - t) + end_radius * t
        radius *= (1 + random.uniform(-0.2, 0.2))
        radius = max(radius, 0.002)

        if i < n - 1:
            tangent = path[i + 1] - point
            if tangent.length > 0.001:
                tangent.normalize()
            else:
                tangent = Vector((0, 0, 1))
        elif i > 0:
            tangent = point - path[i - 1]
            if tangent.length > 0.001:
                tangent.normalize()
            else:
                tangent = Vector((0, 0, 1))
        else:
            tangent = Vector((0, 0, 1))

        if abs(tangent.z) < 0.9:
            up = Vector((0, 0, 1))
        else:
            up = Vector((1, 0, 0))

        right = tangent.cross(up)
        if right.length > 0.001:
            right.normalize()
        else:
            right = Vector((1, 0, 0))

        up = right.cross(tangent)
        if up.length > 0.001:
            up.normalize()
        else:
            up = Vector((0, 1, 0))

        ring = []
        for j in range(circle_segments):
            angle = 2 * math.pi * j / circle_segments
            offset = (right * math.cos(angle) + up * math.sin(angle)) * radius
            v = bm.verts.new(point + offset)
            ring.append(v)
        rings.append(ring)

    for i in range(len(rings) - 1):
        r1 = rings[i]
        r2 = rings[i + 1]
        for j in range(circle_segments):
            j2 = (j + 1) % circle_segments
            try:
                bm.faces.new([r1[j], r1[j2], r2[j2], r2[j]])
            except ValueError:
                pass

    if len(rings) > 0:
        try:
            bm.faces.new(rings[0][::-1])
        except ValueError:
            pass
        try:
            bm.faces.new(rings[-1])
        except ValueError:
            pass

    return rings


def generate_branches(bm, start_pos, direction, length, radius_start, radius_end, depth, max_depth):
    """Recursively generate branches with sub-branches."""
    if depth > max_depth or length < 0.035 or radius_start < 0.003:
        return

    direction = Vector(direction)
    direction.z = max(direction.z, -0.08) * 0.55
    if direction.length > 0.001:
        direction.normalize()
    else:
        direction = Vector((1, 0, 0))

    segments = max(5, int(12 * (1 - depth * 0.12)))
    path = generate_branch_path(start_pos, direction, length, segments)

    build_tube(bm, path, radius_start, radius_end, CIRCLE_SEGMENTS)

    if depth < max_depth:
        num_sub = random.randint(2, 4)
        for _ in range(num_sub):
            t = random.uniform(0.25, 0.85)
            idx = min(int(t * (len(path) - 1)), len(path) - 1)
            branch_start = path[idx]

            sub_dir = direction.copy()
            sub_dir.rotate(Matrix.Rotation(random.uniform(-1.1, 1.1), 4, 'Z'))
            sub_dir.rotate(Matrix.Rotation(random.uniform(-0.35, 0.35), 4, 'X'))
            sub_dir.z = max(sub_dir.z, -0.05) * 0.5
            if sub_dir.length > 0.001:
                sub_dir.normalize()
            else:
                sub_dir = Vector((1, 0, 0))

            sub_length = length * random.uniform(0.35, 0.65)
            sub_radius_start = radius_start * (1 - t * 0.6) * 0.65
            sub_radius_end = max(TIP_RADIUS * 0.5, sub_radius_start * 0.15)

            generate_branches(bm, branch_start, sub_dir, sub_length, sub_radius_start, sub_radius_end, depth + 1, max_depth)


def add_base_mass(bm, center, radius):
    """Add a lumpy spherical base mass."""
    seg_h = 7
    seg_v = 5

    rings = []
    for i in range(seg_v + 1):
        phi = math.pi * i / seg_v
        if i == 0 or i == seg_v:
            r = radius * (1 + random.uniform(-0.2, 0.2))
            v = bm.verts.new(center + Vector((0, 0, r * math.cos(phi))))
            rings.append([v])
        else:
            ring = []
            for j in range(seg_h):
                theta = 2 * math.pi * j / seg_h
                r = radius * (1 + random.uniform(-0.25, 0.25))
                x = r * math.sin(phi) * math.cos(theta)
                y = r * math.sin(phi) * math.sin(theta)
                z = r * math.cos(phi)
                v = bm.verts.new(center + Vector((x, y, z)))
                ring.append(v)
            rings.append(ring)

    for i in range(seg_v):
        r1 = rings[i]
        r2 = rings[i + 1]
        if i == 0:
            for j in range(seg_h):
                j2 = (j + 1) % seg_h
                try:
                    bm.faces.new([r1[0], r2[j2], r2[j]])
                except ValueError:
                    pass
        elif i == seg_v - 1:
            for j in range(seg_h):
                j2 = (j + 1) % seg_h
                try:
                    bm.faces.new([r1[j], r1[j2], r2[0]])
                except ValueError:
                    pass
        else:
            for j in range(seg_h):
                j2 = (j + 1) % seg_h
                try:
                    bm.faces.new([r1[j], r1[j2], r2[j2], r2[j]])
                except ValueError:
                    pass


def add_polyp_bump(bm, center, radius):
    """Add a small sphere as a polyp bump or nodule."""
    seg = 5
    rings_count = 3

    rings = []
    for i in range(rings_count + 1):
        phi = math.pi * i / rings_count
        if i == 0 or i == rings_count:
            v = bm.verts.new(center + Vector((0, 0, radius * math.cos(phi))))
            rings.append([v])
        else:
            ring = []
            for j in range(seg):
                theta = 2 * math.pi * j / seg
                x = radius * math.sin(phi) * math.cos(theta)
                y = radius * math.sin(phi) * math.sin(theta)
                z = radius * math.cos(phi)
                v = bm.verts.new(center + Vector((x, y, z)))
                ring.append(v)
            rings.append(ring)

    for i in range(rings_count):
        r1 = rings[i]
        r2 = rings[i + 1]
        if i == 0:
            for j in range(seg):
                j2 = (j + 1) % seg
                try:
                    bm.faces.new([r1[0], r2[j2], r2[j]])
                except ValueError:
                    pass
        elif i == rings_count - 1:
            for j in range(seg):
                j2 = (j + 1) % seg
                try:
                    bm.faces.new([r1[j], r1[j2], r2[0]])
                except ValueError:
                    pass
        else:
            for j in range(seg):
                j2 = (j + 1) % seg
                try:
                    bm.faces.new([r1[j], r1[j2], r2[j2], r2[j]])
                except ValueError:
                    pass


# ── Build central base mass ──
add_base_mass(bm, Vector((0, 0, 0.02)), 0.07)

# ── Generate main branches radiating outward ──
num_main = 26
for i in range(num_main):
    angle = 2 * math.pi * i / num_main + random.uniform(-0.15, 0.15)
    elevation = random.uniform(0.08, 0.45)
    direction = Vector((
        math.cos(angle) * math.cos(elevation),
        math.sin(angle) * math.cos(elevation),
        math.sin(elevation)
    ))

    length = random.uniform(0.45, 0.85)
    radius_start = BASE_RADIUS * random.uniform(0.8, 1.15)
    radius_end = TIP_RADIUS

    generate_branches(bm, Vector((0, 0, 0)), direction, length, radius_start, radius_end, 0, MAX_DEPTH)

# ── Extra dense branches from offset positions ──
for _ in range(16):
    angle = random.uniform(0, 2 * math.pi)
    elevation = random.uniform(0.05, 0.35)
    direction = Vector((
        math.cos(angle) * math.cos(elevation),
        math.sin(angle) * math.cos(elevation),
        math.sin(elevation)
    ))

    start = Vector((
        random.uniform(-0.05, 0.05),
        random.uniform(-0.05, 0.05),
        random.uniform(0, 0.04)
    ))
    length = random.uniform(0.25, 0.55)
    radius_start = BASE_RADIUS * 0.55
    radius_end = TIP_RADIUS * 0.7

    generate_branches(bm, start, direction, length, radius_start, radius_end, 0, MAX_DEPTH - 1)

# ── Add polyp bumps on branch surfaces ──
bm.faces.ensure_lookup_table()
face_data = [(f.calc_center_median(), f.normal.copy()) for f in bm.faces]

num_bumps = min(500, len(face_data) // 3)
if num_bumps > 0:
    bump_indices = random.sample(range(len(face_data)), num_bumps)
    for idx in bump_indices:
        center, normal = face_data[idx]
        bump_center = center + normal * random.uniform(0.001, 0.003)
        bump_radius = random.uniform(0.003, 0.009)
        add_polyp_bump(bm, bump_center, bump_radius)

# ── Add larger nodules at branch tips ──
bm.verts.ensure_lookup_table()
tip_verts = [v for v in bm.verts if v.co.length > 0.45]
if len(tip_verts) > 20:
    for v in random.sample(tip_verts, min(25, len(tip_verts))):
        add_polyp_bump(bm, v.co, random.uniform(0.006, 0.012))

# ── Vertex displacement noise for rough encrusted texture ──
for v in bm.verts:
    v.co += Vector((
        random.uniform(-0.002, 0.002),
        random.uniform(-0.002, 0.002),
        random.uniform(-0.002, 0.002)
    ))

# ── Lift so lowest point sits at z=0 ──
min_z = min(v.co.z for v in bm.verts)
for v in bm.verts:
    v.co.z -= min_z

# ── Cleanup mesh ──
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

# ── Apply vertex colors: dark reddish-brown base → dusty pink-beige tips ──
color_layer = bm.loops.layers.color.new("Color")

max_dist = max(v.co.length for v in bm.verts) if bm.verts else 0.01
max_dist = max(max_dist, 0.01)

base_color = Vector((0.28, 0.11, 0.06))   # dark reddish-brown
mid_color = Vector((0.55, 0.30, 0.22))    # warm transitional
tip_color = Vector((0.88, 0.70, 0.60))    # dusty pink-beige

for face in bm.faces:
    for loop in face.loops:
        vert = loop.vert
        dist = vert.co.length
        t = min(dist / max_dist, 1.0)

        if t < 0.35:
            tt = t / 0.35
            r = base_color.x * (1 - tt) + mid_color.x * tt
            g = base_color.y * (1 - tt) + mid_color.y * tt
            b = base_color.z * (1 - tt) + mid_color.z * tt
        else:
            tt = (t - 0.35) / 0.65
            r = mid_color.x * (1 - tt) + tip_color.x * tt
            g = mid_color.y * (1 - tt) + tip_color.y * tt
            b = mid_color.z * (1 - tt) + tip_color.z * tt

        n = random.uniform(-0.04, 0.04)
        loop[color_layer] = (
            max(0, min(1, r + n)),
            max(0, min(1, g + n)),
            max(0, min(1, b + n)),
            1.0
        )

# ── Write bmesh to mesh ──
bm.to_mesh(mesh)
bm.free()

# ── Subdivision surface for smoother branches ──
subsurf = obj.modifiers.new(name="Subsurf", type='SUBSURF')
subsurf.levels = 1
subsurf.render_levels = 1

# ── Material using vertex colors ──
mat = bpy.data.materials.new(name="CoralMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links

for node in list(nodes):
    nodes.remove(node)

output_node = nodes.new('ShaderNodeOutputMaterial')
output_node.location = (400, 0)

principled = nodes.new('ShaderNodeBsdfPrincipled')
principled.location = (100, 0)
principled.inputs['Roughness'].default_value = 0.85

vcol_node = nodes.new('ShaderNodeVertexColor')
vcol_node.layer_name = "Color"
vcol_node.location = (-200, 0)

links.new(vcol_node.outputs['Color'], principled.inputs['Base Color'])
links.new(principled.outputs['BSDF'], output_node.inputs['Surface'])

obj.data.materials.append(mat)

# ── Smooth shading ──
for poly in mesh.polygons:
    poly.use_smooth = True