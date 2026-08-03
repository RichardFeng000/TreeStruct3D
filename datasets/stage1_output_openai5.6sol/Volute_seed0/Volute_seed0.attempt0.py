import bpy
import math
from mathutils import Matrix, Vector

# Clear the scene completely.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                   bpy.data.cameras, bpy.data.lights):
    if datablocks != bpy.data.materials:
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)

# Materials for the cream and brown shell pattern.
def make_material(name, color, roughness=0.38):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = 0.0
    return material

materials = [
    make_material("Warm Ivory", (0.78, 0.61, 0.37), 0.34),
    make_material("Pale Cream", (0.93, 0.82, 0.59), 0.32),
    make_material("Stripe Tan", (0.52, 0.29, 0.12), 0.37),
    make_material("Stripe Brown", (0.27, 0.105, 0.035), 0.40),
    make_material("Deep Brown Accents", (0.105, 0.032, 0.012), 0.43),
    make_material("Aperture Interior", (0.095, 0.045, 0.024), 0.48),
]

vertices = []
faces = []
face_materials = []

turns = 2.72
u_max = turns * 2.0 * math.pi
u_segments = 270
v_segments = 160
start_scale = 0.052
growth = math.log(1.0 / start_scale) / u_max

center_radius_factor = 0.70
radial_radius_factor = 0.79
vertical_radius_factor = 1.16
y_compression = 0.86

def shell_scale(u):
    return start_scale * math.exp(growth * u)

def center_height(d):
    # A gently descending centerline creates the low, compact spire.
    return 1.36 * (1.0 - d ** 0.43)

def shell_point(u, v, radius_scale=1.0, tangent_offset=0.0):
    d = shell_scale(u)
    theta = u - u_max
    growth_lines = 1.0 + 0.0065 * math.sin(24.0 * u + 0.8 * math.sin(v))
    r_center = center_radius_factor * d
    r_cross = radial_radius_factor * d * radius_scale * growth_lines
    z_cross = vertical_radius_factor * d * radius_scale * growth_lines

    radial_distance = r_center + r_cross * math.cos(v)
    x = radial_distance * math.cos(theta)
    y = y_compression * radial_distance * math.sin(theta)
    z = center_height(d) + z_cross * math.sin(v)

    # Tangent points in the direction of the open mouth at the final whorl.
    tx = -math.sin(theta)
    ty = y_compression * math.cos(theta)
    tangent = Vector((tx, ty, 0.0)).normalized()
    return Vector((x, y, z)) + tangent * tangent_offset

def stripe_material(u, v):
    # Longitudinal bands converge toward the apex and undulate across the whorl.
    phase = (
        10.0 * v
        + 1.18 * math.sin(1.34 * u + 0.45)
        + 0.36 * math.sin(4.7 * u - 0.8)
        + 0.15 * math.sin(2.0 * v + 2.1 * u)
    )
    wave = math.sin(phase)
    secondary = math.sin(
        20.0 * v - 0.72 * math.sin(2.0 * u) + 0.25 * math.sin(6.3 * u)
    )

    if wave > 0.84:
        return 4
    if wave > 0.25:
        return 3
    if wave > 0.00 or secondary > 0.965:
        return 2
    if math.sin(0.55 * phase + 0.25) > 0.70:
        return 0
    return 1

# Main coiled outer surface.
outer_start = len(vertices)
for ui in range(u_segments + 1):
    u = u_max * ui / u_segments
    for vi in range(v_segments):
        v = 2.0 * math.pi * vi / v_segments
        vertices.append(tuple(shell_point(u, v)))

for ui in range(u_segments):
    u_mid = u_max * (ui + 0.5) / u_segments
    row_a = outer_start + ui * v_segments
    row_b = row_a + v_segments
    for vi in range(v_segments):
        vn = (vi + 1) % v_segments
        faces.append((row_a + vi, row_b + vi, row_b + vn, row_a + vn))
        v_mid = 2.0 * math.pi * (vi + 0.5) / v_segments
        face_materials.append(stripe_material(u_mid, v_mid))

# Close the tiny apex end.
apex_ring = outer_start
apex_center = Vector((0.0, 0.0, 0.0))
for vi in range(v_segments):
    apex_center += Vector(vertices[apex_ring + vi])
apex_center /= v_segments
apex_index = len(vertices)
vertices.append(tuple(apex_center))
for vi in range(v_segments):
    vn = (vi + 1) % v_segments
    faces.append((apex_index, apex_ring + vn, apex_ring + vi))
    v_mid = 2.0 * math.pi * (vi + 0.5) / v_segments
    face_materials.append(stripe_material(0.0, v_mid))

# Rolled, thick aperture lip.
lip_start = len(vertices)
lip_rings = 8
for ri in range(lip_rings):
    t = ri / (lip_rings - 1)
    radius_scale = 1.0 - 0.12 * t + 0.035 * math.sin(math.pi * t)
    tangent_offset = 0.050 * math.sin(math.pi * t)
    for vi in range(v_segments):
        v = 2.0 * math.pi * vi / v_segments
        vertices.append(tuple(shell_point(u_max, v, radius_scale, tangent_offset)))

for ri in range(lip_rings - 1):
    row_a = lip_start + ri * v_segments
    row_b = row_a + v_segments
    for vi in range(v_segments):
        vn = (vi + 1) % v_segments
        faces.append((row_a + vi, row_b + vi, row_b + vn, row_a + vn))
        v_mid = 2.0 * math.pi * (vi + 0.5) / v_segments
        mat = stripe_material(u_max, v_mid)
        if mat == 1 and ri > lip_rings // 2:
            mat = 0
        face_materials.append(mat)

# Bridge the main shell endpoint to the beginning of the rolled lip.
outer_end_row = outer_start + u_segments * v_segments
first_lip_row = lip_start
for vi in range(v_segments):
    vn = (vi + 1) % v_segments
    faces.append((
        outer_end_row + vi,
        first_lip_row + vi,
        first_lip_row + vn,
        outer_end_row + vn
    ))
    v_mid = 2.0 * math.pi * (vi + 0.5) / v_segments
    face_materials.append(stripe_material(u_max, v_mid))

# Deep narrowing inner aperture.
inner_start = len(vertices)
inner_segments = 56
inner_depth = 1.23
for ji in range(inner_segments + 1):
    t = ji / inner_segments
    u = u_max - inner_depth * t
    radius_scale = 0.88 * (1.0 - t) ** 1.25 + 0.10
    tangent_offset = 0.008 * (1.0 - t)
    for vi in range(v_segments):
        v = 2.0 * math.pi * vi / v_segments
        point = shell_point(u, v, radius_scale, tangent_offset)
        vertices.append(tuple(point))

# Bridge final lip ring to inner mouth.
last_lip_row = lip_start + (lip_rings - 1) * v_segments
inner_mouth_row = inner_start
for vi in range(v_segments):
    vn = (vi + 1) % v_segments
    faces.append((
        last_lip_row + vi,
        inner_mouth_row + vi,
        inner_mouth_row + vn,
        last_lip_row + vn
    ))
    v_mid = 2.0 * math.pi * (vi + 0.5) / v_segments
    edge_mat = stripe_material(u_max, v_mid)
    face_materials.append(3 if edge_mat in (3, 4) else 0)

# Reversed winding for the visible inner wall.
for ji in range(inner_segments):
    row_a = inner_start + ji * v_segments
    row_b = row_a + v_segments
    for vi in range(v_segments):
        vn = (vi + 1) % v_segments
        faces.append((row_a + vi, row_a + vn, row_b + vn, row_b + vi))
        if ji < 5:
            v_mid = 2.0 * math.pi * (vi + 0.5) / v_segments
            outer_mat = stripe_material(u_max, v_mid)
            face_materials.append(3 if outer_mat in (3, 4) else 0)
        else:
            face_materials.append(5)

# Cap the far end of the cavity with a dark, recessed surface.
back_row = inner_start + inner_segments * v_segments
back_center = Vector((0.0, 0.0, 0.0))
for vi in range(v_segments):
    back_center += Vector(vertices[back_row + vi])
back_center /= v_segments
back_index = len(vertices)
vertices.append(tuple(back_center))
for vi in range(v_segments):
    vn = (vi + 1) % v_segments
    faces.append((back_row + vi, back_row + vn, back_index))
    face_materials.append(5)

mesh = bpy.data.meshes.new("Textured_Volute_Shell_Mesh")
mesh.from_pydata(vertices, [], faces)
mesh.materials.clear()
for material in materials:
    mesh.materials.append(material)

for polygon, material_index in zip(mesh.polygons, face_materials):
    polygon.material_index = material_index
    polygon.use_smooth = True

mesh.update()
shell = bpy.data.objects.new("Textured Volute Shell", mesh)
bpy.context.collection.objects.link(shell)

# Present the shell at a subtle three-quarter angle while keeping it at the origin.
shell.rotation_euler = (
    math.radians(8.0),
    math.radians(-11.0),
    math.radians(-24.0)
)
bpy.context.view_layer.objects.active = shell
shell.select_set(True)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# Center the finished geometry precisely around the world origin.
world_bounds = [shell.matrix_world @ Vector(corner) for corner in shell.bound_box]
minimum = Vector((
    min(v.x for v in world_bounds),
    min(v.y for v in world_bounds),
    min(v.z for v in world_bounds)
))
maximum = Vector((
    max(v.x for v in world_bounds),
    max(v.y for v in world_bounds),
    max(v.z for v in world_bounds)
))
shell.location -= (minimum + maximum) * 0.5
bpy.context.view_layer.update()

# Preserve smooth custom normals across the dense procedural surface.
for polygon in mesh.polygons:
    polygon.use_smooth = True

shell.select_set(True)
bpy.context.view_layer.objects.active = shell
