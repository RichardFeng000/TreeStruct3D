import bpy
import math
import random
from mathutils import Vector

random.seed(1847)

# Clear the scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    for datablock in list(datablocks):
        if datablock.users == 0:
            datablocks.remove(datablock)


def make_translucent_material(name, color, alpha, roughness=0.35, transmission=0.3, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (color[0], color[1], color[2], alpha)
    mat.use_nodes = True

    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = 1.36
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
        if "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = transmission
        elif "Transmission" in bsdf.inputs:
            bsdf.inputs["Transmission"].default_value = transmission
        if "Coat Weight" in bsdf.inputs:
            bsdf.inputs["Coat Weight"].default_value = 0.08

    if hasattr(mat, "surface_render_method"):
        try:
            mat.surface_render_method = 'DITHERED'
        except TypeError:
            pass
    if hasattr(mat, "use_transparency_overlap"):
        mat.use_transparency_overlap = False
    mat.use_screen_refraction = True if hasattr(mat, "use_screen_refraction") else False
    mat.show_transparent_back = True
    return mat


bell_materials = [
    make_translucent_material("Bell_Pale_Lavender", (0.80, 0.54, 0.76), 0.34, 0.28, 0.38),
    make_translucent_material("Bell_Soft_Pink", (0.92, 0.60, 0.75), 0.28, 0.32, 0.34),
    make_translucent_material("Bell_Cool_Facet", (0.68, 0.49, 0.78), 0.24, 0.38, 0.32),
]
rim_material = make_translucent_material("Bell_Rim", (0.96, 0.60, 0.78), 0.42, 0.28, 0.3)
tentacle_material = make_translucent_material("Wispy_Tentacles", (0.96, 0.48, 0.70), 0.43, 0.32, 0.18)
oral_material = make_translucent_material("Central_Oral_Arm", (0.90, 0.42, 0.72), 0.48, 0.3, 0.24)
shadow_materials = [
    make_translucent_material("Shadow_Haze_Outer", (0.12, 0.055, 0.15), 0.025, 0.75, 0.0),
    make_translucent_material("Shadow_Haze_Middle", (0.10, 0.035, 0.12), 0.035, 0.75, 0.0),
    make_translucent_material("Shadow_Haze_Core", (0.075, 0.02, 0.09), 0.05, 0.75, 0.0),
]

# Faceted, softly lobed bell.
segments = 72
outer_rings = 17
underside_rings = 6
vertices = []
rings = []

top_index = len(vertices)
vertices.append((0.0, 0.0, 4.34))

for ring in range(1, outer_rings + 1):
    theta = (ring / outer_rings) * (math.pi * 0.5)
    base_radius = 2.18 * (math.sin(theta) ** 0.91)
    base_z = 2.04 + 2.30 * math.cos(theta)
    current_ring = []

    for j in range(segments):
        angle = math.tau * j / segments
        edge_weight = math.sin(theta) ** 3.3
        lobe = 1.0 + 0.043 * edge_weight * math.cos(10.0 * angle)
        micro = 1.0 + 0.009 * math.sin(17.0 * angle + ring * 1.71)
        radius = base_radius * lobe * micro
        z = base_z
        z -= 0.065 * edge_weight * (0.5 + 0.5 * math.cos(10.0 * angle))
        if ring not in (1, outer_rings):
            z += random.uniform(-0.012, 0.012)
            radius += random.uniform(-0.011, 0.011)
        current_ring.append(len(vertices))
        vertices.append((radius * math.cos(angle), radius * math.sin(angle), z))
    rings.append(current_ring)

rim_radius = 2.18
for ring in range(1, underside_rings + 1):
    u = ring / (underside_rings + 1)
    current_ring = []
    base_radius = rim_radius * (1.0 - u) + 0.18 * u
    base_z = 1.98 - 0.34 * math.sin(math.pi * u * 0.82) - 0.03 * u

    for j in range(segments):
        angle = math.tau * j / segments
        lobe_strength = (1.0 - u) ** 2
        radius = base_radius * (1.0 + 0.038 * lobe_strength * math.cos(10.0 * angle))
        z = base_z - 0.025 * lobe_strength * math.cos(10.0 * angle)
        current_ring.append(len(vertices))
        vertices.append((radius * math.cos(angle), radius * math.sin(angle), z))
    rings.append(current_ring)

bottom_center = len(vertices)
vertices.append((0.0, 0.0, 1.73))

faces = []
for j in range(segments):
    faces.append((top_index, rings[0][j], rings[0][(j + 1) % segments]))

for r in range(len(rings) - 1):
    a = rings[r]
    b = rings[r + 1]
    for j in range(segments):
        jn = (j + 1) % segments
        if (j + r) % 2 == 0:
            faces.append((a[j], b[j], b[jn]))
            faces.append((a[j], b[jn], a[jn]))
        else:
            faces.append((a[j], b[j], a[jn]))
            faces.append((a[jn], b[j], b[jn]))

for j in range(segments):
    faces.append((rings[-1][j], bottom_center, rings[-1][(j + 1) % segments]))

bell_mesh = bpy.data.meshes.new("Faceted_Bell_Mesh")
bell_mesh.from_pydata(vertices, [], faces)
bell_mesh.update()

bell = bpy.data.objects.new("Translucent_Faceted_Bell", bell_mesh)
bpy.context.collection.objects.link(bell)
for material in bell_materials:
    bell.data.materials.append(material)

for polygon in bell.data.polygons:
    center_z = polygon.center.z if hasattr(polygon, "center") else 3.0
    selector = random.random()
    if selector < 0.69:
        polygon.material_index = 0
    elif selector < 0.89:
        polygon.material_index = 1
    else:
        polygon.material_index = 2
    polygon.use_smooth = False

# Delicate rounded rim following the lobed skirt.
rim_curve = bpy.data.curves.new("Soft_Lobed_Rim_Curve", type='CURVE')
rim_curve.dimensions = '3D'
rim_curve.resolution_u = 1
rim_curve.bevel_depth = 0.047
rim_curve.bevel_resolution = 3
rim_curve.resolution_u = 2
rim_curve.materials.append(rim_material)

rim_spline = rim_curve.splines.new('NURBS')
rim_spline.points.add(segments - 1)
for j, point in enumerate(rim_spline.points):
    angle = math.tau * j / segments
    radius = rim_radius * (1.0 + 0.043 * math.cos(10.0 * angle))
    z = 2.04 - 0.065 * (0.5 + 0.5 * math.cos(10.0 * angle))
    point.co = (radius * math.cos(angle), radius * math.sin(angle), z, 1.0)
    point.radius = 0.86 + 0.13 * math.cos(10.0 * angle)
rim_spline.use_cyclic_u = True
rim_spline.order_u = 3
rim_spline.use_endpoint_u = False

rim_object = bpy.data.objects.new("Luminous_Lobed_Rim", rim_curve)
bpy.context.collection.objects.link(rim_object)

# Numerous thread-like, tangled tentacles in one coherent curve object.
tentacle_curve = bpy.data.curves.new("Wispy_Tentacle_Curves", type='CURVE')
tentacle_curve.dimensions = '3D'
tentacle_curve.resolution_u = 2
tentacle_curve.bevel_depth = 0.014
tentacle_curve.bevel_resolution = 2
tentacle_curve.resolution_u = 2
tentacle_curve.materials.append(tentacle_material)

tentacle_count = 62
golden_angle = math.pi * (3.0 - math.sqrt(5.0))

for i in range(tentacle_count):
    spline = tentacle_curve.splines.new('BEZIER')
    point_count = random.randint(11, 16)
    spline.bezier_points.add(point_count - 1)

    radial = 0.18 + 1.58 * math.sqrt((i + 0.5) / tentacle_count)
    angle0 = i * golden_angle + random.uniform(-0.18, 0.18)
    start = Vector((
        radial * math.cos(angle0),
        radial * math.sin(angle0),
        1.86 - 0.13 * (radial / 1.75) ** 2
    ))

    length = random.uniform(4.0, 6.25)
    if i % 7 == 0:
        length += 0.45
    drift_angle = angle0 + random.uniform(-1.8, 1.8)
    drift = Vector((math.cos(drift_angle), math.sin(drift_angle), 0.0)) * random.uniform(0.12, 0.65)
    phase_a = random.uniform(0.0, math.tau)
    phase_b = random.uniform(0.0, math.tau)
    frequency_a = random.uniform(1.15, 2.55)
    frequency_b = random.uniform(2.0, 4.2)
    amplitude = random.uniform(0.10, 0.34)

    for p, bezier_point in enumerate(spline.bezier_points):
        t = p / (point_count - 1)
        downward = length * (t ** 1.02)
        growing_wave = amplitude * (0.25 + 0.9 * t)
        curl_x = growing_wave * math.sin(math.tau * frequency_a * t + phase_a)
        curl_y = growing_wave * math.cos(math.tau * frequency_b * t + phase_b)
        secondary = 0.08 * t * math.sin(math.tau * (frequency_b + 1.3) * t + phase_a)

        location = start + drift * (t ** 1.35)
        location.x += curl_x + secondary * math.cos(angle0)
        location.y += curl_y + secondary * math.sin(angle0)
        location.z -= downward
        location.z += 0.06 * math.sin(math.tau * 2.0 * t + phase_b) * t

        bezier_point.co = location
        bezier_point.handle_left_type = 'AUTO'
        bezier_point.handle_right_type = 'AUTO'
        taper = max(0.18, (1.0 - 0.68 * t))
        bezier_point.radius = random.uniform(0.55, 1.22) * taper

tentacles = bpy.data.objects.new("Cascade_of_Wispy_Tentacles", tentacle_curve)
bpy.context.collection.objects.link(tentacles)

# A thicker, ruffled ribbon-like central oral arm spiraling downward.
steps = 150
ribbon_vertices = []
ribbon_faces = []

for i in range(steps):
    t = i / (steps - 1)
    turns = 3.85
    angle = math.tau * turns * t + 0.38 * math.sin(math.tau * 1.7 * t)
    spiral_radius = 0.11 + 0.42 * math.sin(math.pi * t) ** 1.15
    center = Vector((
        spiral_radius * math.cos(angle),
        spiral_radius * math.sin(angle),
        1.78 - 5.25 * t + 0.10 * math.sin(math.tau * 2.4 * t)
    ))

    twist = angle * 0.57 + math.tau * 1.75 * t
    width_direction = Vector((
        math.cos(twist),
        math.sin(twist),
        0.58 * math.sin(twist * 1.37)
    )).normalized()

    base_width = 0.28 * (1.0 - 0.48 * t) + 0.07
    ruffle = 1.0 + 0.26 * math.sin(math.tau * 11.0 * t)
    width = base_width * ruffle

    left = center - width_direction * width
    right = center + width_direction * width * (0.88 + 0.12 * math.sin(math.tau * 7.0 * t))
    ribbon_vertices.extend((tuple(left), tuple(right)))

for i in range(steps - 1):
    a = i * 2
    ribbon_faces.append((a, a + 2, a + 3, a + 1))

ribbon_mesh = bpy.data.meshes.new("Spiral_Oral_Arm_Mesh")
ribbon_mesh.from_pydata(ribbon_vertices, [], ribbon_faces)
ribbon_mesh.update()

oral_arm = bpy.data.objects.new("Single_Spiraling_Ribbon_Oral_Arm", ribbon_mesh)
bpy.context.collection.objects.link(oral_arm)
oral_arm.data.materials.append(oral_material)

for polygon in oral_arm.data.polygons:
    polygon.use_smooth = True

solidify = oral_arm.modifiers.new("Delicate_Ribbon_Thickness", 'SOLIDIFY')
solidify.thickness = 0.025
solidify.offset = 0.0

bevel = oral_arm.modifiers.new("Soft_Ribbon_Edges", 'BEVEL')
bevel.width = 0.018
bevel.segments = 2
bevel.limit_method = 'ANGLE'

# Soft, volumetric-looking dark haze beneath the lowest tentacles.
shadow_specs = [
    ((1.20, 0.76, 0.10), (-0.10, 0.08, -4.68), shadow_materials[0]),
    ((0.88, 0.55, 0.075), (0.10, -0.04, -4.67), shadow_materials[1]),
    ((0.54, 0.34, 0.055), (-0.02, 0.01, -4.66), shadow_materials[2]),
]

for index, (scale, location, material) in enumerate(shadow_specs):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=48,
        ring_count=16,
        location=location
    )
    haze = bpy.context.object
    haze.name = "Diffuse_Shadow_Haze_%02d" % index
    haze.scale = scale
    haze.data.materials.append(material)
    for polygon in haze.data.polygons:
        polygon.use_smooth = True

# Keep the complete jellyfish assembly selected and centered around the world origin.
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = bell
