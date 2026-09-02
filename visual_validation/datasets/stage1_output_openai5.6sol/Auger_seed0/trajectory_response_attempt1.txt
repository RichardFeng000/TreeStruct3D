import bpy
import math
from mathutils import Matrix

# Clear the scene completely.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    pass

# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def make_principled_material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.32
    return mat

shell_mat = bpy.data.materials.new("Wavy Brown and Cream Shell")
shell_mat.diffuse_color = (0.48, 0.23, 0.09, 1.0)
shell_mat.use_nodes = True
nodes = shell_mat.node_tree.nodes
links = shell_mat.node_tree.links
nodes.clear()

output = nodes.new("ShaderNodeOutputMaterial")
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
texcoord = nodes.new("ShaderNodeTexCoord")
separate = nodes.new("ShaderNodeSeparateXYZ")
noise = nodes.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = 4.2
noise.inputs["Detail"].default_value = 5.0
noise.inputs["Roughness"].default_value = 0.72

mul_v = nodes.new("ShaderNodeMath")
mul_v.operation = 'MULTIPLY'
mul_v.inputs[1].default_value = 50.0

mul_u = nodes.new("ShaderNodeMath")
mul_u.operation = 'MULTIPLY'
mul_u.inputs[1].default_value = -6.283185307

noise_center = nodes.new("ShaderNodeMath")
noise_center.operation = 'SUBTRACT'
noise_center.inputs[1].default_value = 0.48

noise_mul = nodes.new("ShaderNodeMath")
noise_mul.operation = 'MULTIPLY'
noise_mul.inputs[1].default_value = 5.2

add_uv = nodes.new("ShaderNodeMath")
add_uv.operation = 'ADD'
add_noise = nodes.new("ShaderNodeMath")
add_noise.operation = 'ADD'
sine = nodes.new("ShaderNodeMath")
sine.operation = 'SINE'

ramp = nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.interpolation = 'EASE'
while len(ramp.color_ramp.elements) > 2:
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[-1])
e0 = ramp.color_ramp.elements[0]
e0.position = 0.18
e0.color = (0.055, 0.016, 0.006, 1.0)
e1 = ramp.color_ramp.elements[1]
e1.position = 0.82
e1.color = (0.88, 0.68, 0.38, 1.0)
e_mid1 = ramp.color_ramp.elements.new(0.39)
e_mid1.color = (0.27, 0.075, 0.018, 1.0)
e_mid2 = ramp.color_ramp.elements.new(0.61)
e_mid2.color = (0.96, 0.84, 0.58, 1.0)

fine_v = nodes.new("ShaderNodeMath")
fine_v.operation = 'MULTIPLY'
fine_v.inputs[1].default_value = 175.0
fine_u = nodes.new("ShaderNodeMath")
fine_u.operation = 'MULTIPLY'
fine_u.inputs[1].default_value = -12.56637
fine_add = nodes.new("ShaderNodeMath")
fine_add.operation = 'ADD'
fine_sine = nodes.new("ShaderNodeMath")
fine_sine.operation = 'SINE'
fine_scale = nodes.new("ShaderNodeMath")
fine_scale.operation = 'MULTIPLY'
fine_scale.inputs[1].default_value = 0.5
bump = nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.28
bump.inputs["Distance"].default_value = 0.035

links.new(texcoord.outputs["UV"], separate.inputs["Vector"])
links.new(texcoord.outputs["UV"], noise.inputs["Vector"])
links.new(separate.outputs["Y"], mul_v.inputs[0])
links.new(separate.outputs["X"], mul_u.inputs[0])
links.new(noise.outputs["Fac"], noise_center.inputs[0])
links.new(noise_center.outputs[0], noise_mul.inputs[0])
links.new(mul_v.outputs[0], add_uv.inputs[0])
links.new(mul_u.outputs[0], add_uv.inputs[1])
links.new(add_uv.outputs[0], add_noise.inputs[0])
links.new(noise_mul.outputs[0], add_noise.inputs[1])
links.new(add_noise.outputs[0], sine.inputs[0])
links.new(sine.outputs[0], ramp.inputs["Fac"])
links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

links.new(separate.outputs["Y"], fine_v.inputs[0])
links.new(separate.outputs["X"], fine_u.inputs[0])
links.new(fine_v.outputs[0], fine_add.inputs[0])
links.new(fine_u.outputs[0], fine_add.inputs[1])
links.new(fine_add.outputs[0], fine_sine.inputs[0])
links.new(fine_sine.outputs[0], fine_scale.inputs[0])
links.new(fine_scale.outputs[0], bump.inputs["Height"])
links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

bsdf.inputs["Roughness"].default_value = 0.38
if "Specular IOR Level" in bsdf.inputs:
    bsdf.inputs["Specular IOR Level"].default_value = 0.38

cream_mat = make_principled_material("Raised Cream Growth Ridges", (0.78, 0.55, 0.28), 0.4)
brown_mat = make_principled_material("Dark Spiral Sutures", (0.16, 0.035, 0.009), 0.44)
aperture_mat = make_principled_material("Deep Aperture", (0.022, 0.007, 0.003), 0.3)
lip_mat = make_principled_material("Polished Aperture Lip", (0.69, 0.42, 0.18), 0.32)

# ---------------------------------------------------------------------------
# Shell body
# ---------------------------------------------------------------------------

profile_points = [
    (-3.12, 0.13),
    (-2.88, 0.43),
    (-2.52, 0.76),
    (-2.08, 0.99),
    (-1.55, 1.14),
    (-0.95, 1.18),
    (-0.30, 1.08),
    (0.40, 0.94),
    (1.10, 0.79),
    (1.75, 0.64),
    (2.35, 0.50),
    (2.88, 0.37),
    (3.35, 0.26),
    (3.75, 0.15),
    (4.12, 0.045),
]

def smoothstep(v):
    return v * v * (3.0 - 2.0 * v)

def envelope(z):
    if z <= profile_points[0][0]:
        return profile_points[0][1]
    if z >= profile_points[-1][0]:
        return profile_points[-1][1]
    for i in range(len(profile_points) - 1):
        z0, r0 = profile_points[i]
        z1, r1 = profile_points[i + 1]
        if z0 <= z <= z1:
            q = smoothstep((z - z0) / (z1 - z0))
            return r0 + (r1 - r0) * q
    return 0.01

z_min = -3.12
z_max = 4.12
ring_count = 206
side_count = 192
verts = []
faces = []

for i in range(ring_count):
    t = i / (ring_count - 1)
    z = z_min + (z_max - z_min) * t
    base_r = envelope(z)
    growth = 8.35 * (t ** 0.86)
    tip_fade = min(1.0, base_r / 0.22)
    for j in range(side_count):
        theta = 2.0 * math.pi * j / side_count
        phase = 2.0 * math.pi * growth - theta
        rounded_whorl = (0.5 + 0.5 * math.cos(phase)) ** 1.7
        whorl_factor = 0.944 + 0.115 * rounded_whorl
        axial_ribs = 0.0105 * math.cos(15.0 * theta + 0.45 * math.sin(phase))
        fine_spiral = 0.006 * math.cos(3.0 * phase + 0.35)
        r = base_r * (whorl_factor + tip_fade * (axial_ribs + fine_spiral))
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        verts.append((x, y, z))

for i in range(ring_count - 1):
    for j in range(side_count):
        nj = (j + 1) % side_count
        a = i * side_count + j
        b = i * side_count + nj
        c = (i + 1) * side_count + nj
        d = (i + 1) * side_count + j
        faces.append((a, b, c, d))

bottom_index = len(verts)
verts.append((0.0, 0.0, -3.27))
top_index = len(verts)
verts.append((0.0, 0.0, 4.31))

for j in range(side_count):
    nj = (j + 1) % side_count
    faces.append((bottom_index, nj, j))
    a = (ring_count - 1) * side_count + j
    b = (ring_count - 1) * side_count + nj
    faces.append((top_index, a, b))

shell_mesh = bpy.data.meshes.new("Auger Shell Body Mesh")
shell_mesh.from_pydata(verts, [], faces)
shell_mesh.update()
shell_obj = bpy.data.objects.new("Elongated Spiraling Auger Shell", shell_mesh)
bpy.context.collection.objects.link(shell_obj)
shell_obj.data.materials.append(shell_mat)

for poly in shell_mesh.polygons:
    poly.use_smooth = True

uv_layer = shell_mesh.uv_layers.new(name="Growth Coordinates")
quad_count = (ring_count - 1) * side_count
for p_index in range(quad_count):
    i = p_index // side_count
    j = p_index % side_count
    u0 = j / side_count
    u1 = (j + 1) / side_count
    v0 = i / (ring_count - 1)
    v1 = (i + 1) / (ring_count - 1)
    poly = shell_mesh.polygons[p_index]
    coords = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    for loop_idx, uv in zip(poly.loop_indices, coords):
        uv_layer.data[loop_idx].uv = uv

# ---------------------------------------------------------------------------
# Raised helical growth ridges
# ---------------------------------------------------------------------------

def surface_radius(z, theta):
    t = max(0.0, min(1.0, (z - z_min) / (z_max - z_min)))
    base_r = envelope(z)
    growth = 8.35 * (t ** 0.86)
    phase = 2.0 * math.pi * growth - theta
    rounded_whorl = (0.5 + 0.5 * math.cos(phase)) ** 1.7
    whorl_factor = 0.944 + 0.115 * rounded_whorl
    tip_fade = min(1.0, base_r / 0.22)
    axial_ribs = 0.0105 * math.cos(15.0 * theta + 0.45 * math.sin(phase))
    fine_spiral = 0.006 * math.cos(3.0 * phase + 0.35)
    return base_r * (whorl_factor + tip_fade * (axial_ribs + fine_spiral))

def create_spiral_curve(name, phase_offset, material, bevel_depth, z_start=-2.92, z_end=4.02):
    curve_data = bpy.data.curves.new(name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 1
    curve_data.bevel_depth = bevel_depth
    curve_data.bevel_resolution = 2
    curve_data.resolution_u = 2
    spline = curve_data.splines.new('NURBS')
    count = 360
    spline.points.add(count - 1)
    for k in range(count):
        q = k / (count - 1)
        z = z_start + (z_end - z_start) * q
        t = max(0.0, min(1.0, (z - z_min) / (z_max - z_min)))
        growth = 8.35 * (t ** 0.86)
        theta = 2.0 * math.pi * growth + phase_offset
        r = surface_radius(z, theta) + bevel_depth * 0.55
        spline.points[k].co = (r * math.cos(theta), r * math.sin(theta), z, 1.0)
    spline.order_u = 3
    spline.use_endpoint_u = True
    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

create_spiral_curve("Cream Spiral Growth Cord", 0.0, cream_mat, 0.022)
create_spiral_curve("Dark Suture Cord", math.pi, brown_mat, 0.014, -2.88, 4.03)
create_spiral_curve("Secondary Fine Spiral Cord", 0.42, cream_mat, 0.010, -2.75, 3.85)

# ---------------------------------------------------------------------------
# Recessed aperture
# ---------------------------------------------------------------------------

aperture_verts = [(0.0, -1.18, -2.02)]
aperture_faces = []
radial_steps = 8
angular_steps = 96

def aperture_boundary(angle):
    s = math.sin(angle)
    width_factor = 0.68 + 0.24 * ((s + 1.0) * 0.5)
    x = 0.56 * width_factor * math.cos(angle)
    z = -2.02 + 1.29 * s
    return x, z

for ri in range(1, radial_steps + 1):
    q = ri / radial_steps
    for j in range(angular_steps):
        a = 2.0 * math.pi * j / angular_steps
        bx, bz = aperture_boundary(a)
        y = -1.18 - 0.045 * q * q
        aperture_verts.append((bx * q, y, -2.02 + (bz + 2.02) * q))

for j in range(angular_steps):
    nj = (j + 1) % angular_steps
    aperture_faces.append((0, 1 + j, 1 + nj))

for ri in range(radial_steps - 1):
    ring0 = 1 + ri * angular_steps
    ring1 = 1 + (ri + 1) * angular_steps
    for j in range(angular_steps):
        nj = (j + 1) % angular_steps
        aperture_faces.append((ring0 + j, ring1 + j, ring1 + nj, ring0 + nj))

ap_mesh = bpy.data.meshes.new("Recessed Aperture Mesh")
ap_mesh.from_pydata(aperture_verts, [], aperture_faces)
ap_mesh.update()
ap_obj = bpy.data.objects.new("Long Oval Shell Aperture", ap_mesh)
bpy.context.collection.objects.link(ap_obj)
ap_obj.data.materials.append(aperture_mat)
for poly in ap_mesh.polygons:
    poly.use_smooth = True

# Aperture lip.
lip_curve = bpy.data.curves.new("Thick Aperture Lip Curve", type='CURVE')
lip_curve.dimensions = '3D'
lip_curve.bevel_depth = 0.061
lip_curve.bevel_resolution = 3
lip_spline = lip_curve.splines.new('NURBS')
lip_count = 128
lip_spline.points.add(lip_count - 1)
for j in range(lip_count):
    a = 2.0 * math.pi * j / lip_count
    x, z = aperture_boundary(a)
    lip_spline.points[j].co = (x, -1.295, z, 1.0)
lip_spline.use_cyclic_u = True
lip_spline.order_u = 3
lip_obj = bpy.data.objects.new("Rolled Aperture Lip", lip_curve)
bpy.context.collection.objects.link(lip_obj)
lip_obj.data.materials.append(lip_mat)

# Inner columella fold.
col_curve = bpy.data.curves.new("Columella Fold Curve", type='CURVE')
col_curve.dimensions = '3D'
col_curve.bevel_depth = 0.047
col_curve.bevel_resolution = 3
col_spline = col_curve.splines.new('NURBS')
col_count = 56
col_spline.points.add(col_count - 1)
for i in range(col_count):
    q = i / (col_count - 1)
    z = -3.00 + 1.96 * q
    x = 0.245 + 0.075 * math.sin(math.pi * q) - 0.04 * q
    y = -1.315 - 0.018 * math.sin(math.pi * q)
    col_spline.points[i].co = (x, y, z, 1.0)
col_spline.order_u = 3
col_spline.use_endpoint_u = True
col_obj = bpy.data.objects.new("Curved Columella Fold", col_curve)
bpy.context.collection.objects.link(col_obj)
col_obj.data.materials.append(cream_mat)

# Small internal folds near the upper aperture.
for idx, zc in enumerate((-1.23, -1.48, -1.72)):
    fold_curve = bpy.data.curves.new("Aperture Fold Curve", type='CURVE')
    fold_curve.dimensions = '3D'
    fold_curve.bevel_depth = 0.025 - idx * 0.003
    fold_curve.bevel_resolution = 2
    fold_spline = fold_curve.splines.new('NURBS')
    fold_count = 24
    fold_spline.points.add(fold_count - 1)
    for k in range(fold_count):
        q = k / (fold_count - 1)
        x = -0.28 + 0.48 * q
        z = zc + 0.055 * math.sin(math.pi * q)
        fold_spline.points[k].co = (x, -1.307, z, 1.0)
    fold_spline.order_u = 3
    fold_spline.use_endpoint_u = True
    fold_obj = bpy.data.objects.new("Aperture Growth Fold", fold_curve)
    bpy.context.collection.objects.link(fold_obj)
    fold_obj.data.materials.append(lip_mat)

# ---------------------------------------------------------------------------
# Give the complete assembly a subtle three-quarter presentation tilt while
# keeping it centered around the origin.
# ---------------------------------------------------------------------------

transform = (
    Matrix.Rotation(math.radians(-7.0), 4, 'X')
    @ Matrix.Rotation(math.radians(11.0), 4, 'Y')
    @ Matrix.Rotation(math.radians(-16.0), 4, 'Z')
    @ Matrix.Translation((0.0, 0.0, -0.50))
)

for obj in list(bpy.context.scene.objects):
    obj.matrix_world = transform @ obj.matrix_world

# Ensure no non-geometry scene objects remain.
for obj in list(bpy.context.scene.objects):
    if obj.type not in {'MESH', 'CURVE'}:
        bpy.data.objects.remove(obj, do_unlink=True)