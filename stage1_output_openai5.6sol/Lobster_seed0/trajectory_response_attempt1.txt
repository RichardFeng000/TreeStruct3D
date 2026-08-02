import bpy
import math
from mathutils import Vector

# Clear the scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    pass

# -------------------------------------------------------------------
# Materials
# -------------------------------------------------------------------

def make_shell_material(name, dark, mid, light, roughness=0.3, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump_noise = nodes.new("ShaderNodeTexNoise")
    bump = nodes.new("ShaderNodeBump")

    noise.inputs["Scale"].default_value = 3.8
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.68
    bump_noise.inputs["Scale"].default_value = 24.0
    bump_noise.inputs["Detail"].default_value = 3.0
    bump_noise.inputs["Roughness"].default_value = 0.62

    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    e0 = ramp.color_ramp.elements[0]
    e0.position = 0.18
    e0.color = (*dark, 1.0)
    e1 = ramp.color_ramp.elements.new(0.52)
    e1.color = (*mid, 1.0)
    e2 = ramp.color_ramp.elements.new(0.82)
    e2.color = (*light, 1.0)

    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = metallic
    if "Specular IOR Level" in principled.inputs:
        principled.inputs["Specular IOR Level"].default_value = 0.48
    if "Coat Weight" in principled.inputs:
        principled.inputs["Coat Weight"].default_value = 0.18
    if "Coat Roughness" in principled.inputs:
        principled.inputs["Coat Roughness"].default_value = 0.22

    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.035

    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    links.new(texcoord.outputs["Generated"], bump_noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], principled.inputs["Base Color"])
    links.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], principled.inputs["Normal"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    return mat

def make_simple_material(name, color, roughness=0.3):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.45
    return mat

shell_mat = make_shell_material(
    "Warm Reddish Brown Shell",
    (0.12, 0.025, 0.012),
    (0.42, 0.075, 0.028),
    (0.72, 0.22, 0.075),
    0.27
)
dark_shell_mat = make_shell_material(
    "Dark Articulation Shell",
    (0.055, 0.012, 0.008),
    (0.22, 0.035, 0.018),
    (0.39, 0.09, 0.035),
    0.34
)
underside_mat = make_shell_material(
    "Underside Shell",
    (0.10, 0.022, 0.012),
    (0.33, 0.075, 0.037),
    (0.52, 0.16, 0.075),
    0.38
)
white_tip_mat = make_simple_material("Ivory Claw Tips", (0.88, 0.77, 0.59), 0.25)
eye_mat = make_simple_material("Glossy Black Eyes", (0.004, 0.002, 0.001), 0.12)

# -------------------------------------------------------------------
# Geometry helpers
# -------------------------------------------------------------------

def smooth_mesh(obj):
    if obj.type == 'MESH':
        for poly in obj.data.polygons:
            poly.use_smooth = True

def add_uv_sphere(name, location, scale, material, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    smooth_mesh(obj)
    return obj

def add_oriented_ellipsoid(name, start, end, width, height, material, segments=28):
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    length = direction.length
    midpoint = (start + end) * 0.5
    obj = add_uv_sphere(name, midpoint, (length * 0.5, width, height), material, segments, 16)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = direction.to_track_quat('X', 'Z')
    return obj

def add_cylinder_between(name, start, end, radius, material, vertices=20, radius2=None):
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    length = direction.length
    midpoint = (start + end) * 0.5

    if radius2 is None:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=vertices,
            radius=radius,
            depth=length,
            location=midpoint
        )
    else:
        bpy.ops.mesh.primitive_cone_add(
            vertices=vertices,
            radius1=radius,
            radius2=radius2,
            depth=length,
            location=midpoint
        )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = direction.to_track_quat('Z', 'Y')
    obj.data.materials.append(material)
    smooth_mesh(obj)
    return obj

def add_curve(name, points, radii, material, bevel_depth=0.035, resolution=3):
    curve_data = bpy.data.curves.new(name + "Data", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 2
    curve_data.bevel_depth = bevel_depth
    curve_data.bevel_resolution = resolution
    curve_data.resolution_u = 2

    spline = curve_data.splines.new('NURBS')
    spline.points.add(len(points) - 1)
    for i, point in enumerate(points):
        spline.points[i].co = (*point, 1.0)
        spline.points[i].radius = radii[i]
    spline.order_u = min(4, len(points))
    spline.use_endpoint_u = True

    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

def add_joint(name, point, radius, material):
    return add_uv_sphere(name, point, (radius, radius, radius), material, 20, 12)

# -------------------------------------------------------------------
# Main cephalothorax and head
# -------------------------------------------------------------------

add_uv_sphere("Cephalothorax", (-0.28, 0.0, 0.72), (1.42, 0.79, 0.64), shell_mat, 48, 28)
add_uv_sphere("LowerThorax", (-0.15, 0.0, 0.39), (1.16, 0.63, 0.37), underside_mat, 40, 22)
add_uv_sphere("HeadDome", (-1.19, 0.0, 0.76), (0.55, 0.61, 0.50), shell_mat, 36, 22)

# Raised central carapace ridge and subtle side cheek plates.
add_oriented_ellipsoid("CarapaceRidge", (-1.10, 0.0, 1.22), (0.74, 0.0, 1.18), 0.09, 0.075, dark_shell_mat)
for side in (-1, 1):
    add_oriented_ellipsoid(
        "CheekPlate",
        (-1.23, side * 0.38, 0.71),
        (-0.60, side * 0.66, 0.68),
        0.18,
        0.25,
        shell_mat
    )

# Rostrum and small rostral side spines.
add_cylinder_between("Rostrum", (-1.48, 0.0, 0.95), (-2.08, 0.0, 1.02), 0.10, shell_mat, 24, 0.008)
for side in (-1, 1):
    add_cylinder_between(
        "RostralSpine",
        (-1.43, side * 0.25, 0.90),
        (-1.84, side * 0.39, 0.94),
        0.045,
        shell_mat,
        16,
        0.006
    )

# Eyes and short stalks.
for side in (-1, 1):
    stalk_base = (-1.40, side * 0.35, 0.93)
    stalk_end = (-1.62, side * 0.48, 1.02)
    add_cylinder_between("EyeStalk", stalk_base, stalk_end, 0.075, dark_shell_mat, 18)
    add_uv_sphere("Eye", stalk_end, (0.12, 0.105, 0.105), eye_mat, 24, 16)

# -------------------------------------------------------------------
# Segmented abdomen
# -------------------------------------------------------------------

abdomen_x = [0.88, 1.43, 1.96, 2.47, 2.96, 3.41]
abdomen_widths = [0.69, 0.66, 0.61, 0.55, 0.48, 0.39]
abdomen_heights = [0.52, 0.50, 0.47, 0.43, 0.37, 0.30]
for i, (x, width, height) in enumerate(zip(abdomen_x, abdomen_widths, abdomen_heights)):
    add_uv_sphere(
        "AbdominalSegment_%02d" % (i + 1),
        (x, 0.0, 0.66 - i * 0.025),
        (0.42, width, height),
        shell_mat,
        36,
        22
    )
    # Dark articulation visible at the leading edge of each segment.
    if i > 0:
        add_uv_sphere(
            "AbdominalJoint_%02d" % i,
            (x - 0.29, 0.0, 0.57 - i * 0.02),
            (0.11, width * 0.91, height * 0.78),
            dark_shell_mat,
            28,
            16
        )

    # Broad overlapping pleural plates on both sides.
    for side in (-1, 1):
        add_oriented_ellipsoid(
            "PleuralPlate_%02d_%s" % (i + 1, "L" if side < 0 else "R"),
            (x - 0.14, side * width * 0.72, 0.58 - i * 0.025),
            (x + 0.26, side * (width + 0.16), 0.42 - i * 0.025),
            0.22,
            0.12,
            shell_mat,
            24
        )

# Ventral abdominal scales.
for i, x in enumerate(abdomen_x[:-1]):
    width = abdomen_widths[i]
    add_uv_sphere(
        "VentralScale_%02d" % (i + 1),
        (x + 0.05, 0.0, 0.28 - i * 0.012),
        (0.31, width * 0.58, 0.11),
        underside_mat,
        28,
        14
    )

# Small swimmerets under the abdomen.
for i, x in enumerate(abdomen_x[1:-1]):
    for side in (-1, 1):
        root = (x, side * 0.25, 0.30)
        tip = (x + 0.18, side * 0.58, 0.12)
        add_cylinder_between("Swimmeret", root, tip, 0.035, dark_shell_mat, 12, 0.015)
        add_oriented_ellipsoid("SwimmeretBlade", tip, (tip[0] + 0.18, tip[1] + side * 0.11, tip[2]), 0.065, 0.025, underside_mat, 20)

# -------------------------------------------------------------------
# Tail fan
# -------------------------------------------------------------------

tail_root = (3.72, 0.0, 0.53)
add_uv_sphere("TailPeduncle", tail_root, (0.42, 0.34, 0.27), shell_mat, 30, 18)

tail_lobes = [
    ((3.82, 0.0, 0.54), (4.88, 0.0, 0.47), 0.30, 0.105),
    ((3.80, -0.16, 0.51), (4.72, -0.57, 0.42), 0.33, 0.095),
    ((3.80, 0.16, 0.51), (4.72, 0.57, 0.42), 0.33, 0.095),
    ((3.72, -0.27, 0.49), (4.47, -0.90, 0.39), 0.30, 0.085),
    ((3.72, 0.27, 0.49), (4.47, 0.90, 0.39), 0.30, 0.085)
]
for i, (start, end, width, height) in enumerate(tail_lobes):
    add_oriented_ellipsoid("TailFanLobe_%02d" % i, start, end, width, height, shell_mat, 32)
    add_cylinder_between("TailFanRib_%02d" % i, start, end, 0.025, dark_shell_mat, 12, 0.010)

# -------------------------------------------------------------------
# Walking legs
# -------------------------------------------------------------------

leg_positions = [-0.82, -0.30, 0.22, 0.67]
for side in (-1, 1):
    for i, x in enumerate(leg_positions):
        sweep = (i - 1.5) * 0.11
        hip = (x, side * 0.57, 0.48)
        upper = (x + sweep, side * (0.98 + i * 0.035), 0.30)
        knee = (x + 0.15 + i * 0.09, side * (1.24 + i * 0.05), 0.13)
        foot = (x + 0.46 + i * 0.11, side * (1.48 + i * 0.045), 0.075)

        add_cylinder_between("LegCoxa", hip, upper, 0.075, shell_mat, 16, 0.060)
        add_joint("LegJoint", upper, 0.085, dark_shell_mat)
        add_cylinder_between("LegFemur", upper, knee, 0.061, shell_mat, 16, 0.043)
        add_joint("LegKnee", knee, 0.062, dark_shell_mat)
        add_cylinder_between("LegTibia", knee, foot, 0.040, shell_mat, 14, 0.014)

# -------------------------------------------------------------------
# Claw-bearing arms and unequal chelae
# -------------------------------------------------------------------

def build_claw(side, large=True):
    side_sign = side
    if large:
        shoulder = (-0.92, side_sign * 0.58, 0.60)
        elbow = (-1.48, side_sign * 0.91, 0.48)
        wrist = (-1.91, side_sign * 1.02, 0.53)
        palm_center = (-2.43, side_sign * 1.06, 0.55)

        add_cylinder_between("CrusherUpperArm", shoulder, elbow, 0.16, shell_mat, 24, 0.13)
        add_joint("CrusherElbow", elbow, 0.18, dark_shell_mat)
        add_cylinder_between("CrusherForearm", elbow, wrist, 0.14, shell_mat, 24, 0.18)
        add_joint("CrusherWrist", wrist, 0.19, dark_shell_mat)
        add_oriented_ellipsoid(
            "CrusherPalm",
            (-1.91, side_sign * 1.03, 0.54),
            (-2.86, side_sign * 1.08, 0.55),
            0.48,
            0.39,
            shell_mat,
            42
        )
        add_uv_sphere("CrusherPalmBulge", palm_center, (0.48, 0.50, 0.40), shell_mat, 38, 22)

        inner_base = (-2.75, side_sign * 0.87, 0.55)
        outer_base = (-2.75, side_sign * 1.28, 0.58)
        inner_mid = (-3.23, side_sign * 0.76, 0.55)
        outer_mid = (-3.22, side_sign * 1.40, 0.60)
        inner_tip = (-3.71, side_sign * 0.84, 0.57)
        outer_tip = (-3.72, side_sign * 1.30, 0.59)

        add_cylinder_between("CrusherInnerFinger", inner_base, inner_mid, 0.18, shell_mat, 24, 0.115)
        add_cylinder_between("CrusherOuterFinger", outer_base, outer_mid, 0.20, shell_mat, 24, 0.12)
        add_cylinder_between("CrusherInnerIvoryTip", inner_mid, inner_tip, 0.12, white_tip_mat, 24, 0.055)
        add_cylinder_between("CrusherOuterIvoryTip", outer_mid, outer_tip, 0.125, white_tip_mat, 24, 0.055)
        add_uv_sphere("CrusherInnerRoundedTip", inner_tip, (0.085, 0.09, 0.085), white_tip_mat, 20, 14)
        add_uv_sphere("CrusherOuterRoundedTip", outer_tip, (0.09, 0.095, 0.09), white_tip_mat, 20, 14)

        # Blunt tooth geometry along the crushing edges.
        for j in range(3):
            t = (j + 1) / 4.0
            x = -2.78 * (1 - t) + -3.26 * t
            y = side_sign * (0.89 * (1 - t) + 0.77 * t)
            add_cylinder_between(
                "CrusherTooth",
                (x, y, 0.58),
                (x, y + side_sign * 0.10, 0.58),
                0.045,
                white_tip_mat if j == 2 else shell_mat,
                12,
                0.012
            )
    else:
        shoulder = (-0.95, side_sign * 0.57, 0.64)
        elbow = (-1.43, side_sign * 0.83, 0.53)
        wrist = (-1.85, side_sign * 0.91, 0.56)

        add_cylinder_between("CutterUpperArm", shoulder, elbow, 0.13, shell_mat, 22, 0.105)
        add_joint("CutterElbow", elbow, 0.145, dark_shell_mat)
        add_cylinder_between("CutterForearm", elbow, wrist, 0.11, shell_mat, 22, 0.135)
        add_joint("CutterWrist", wrist, 0.15, dark_shell_mat)
        add_oriented_ellipsoid(
            "CutterPalm",
            (-1.84, side_sign * 0.92, 0.56),
            (-2.52, side_sign * 0.97, 0.57),
            0.31,
            0.27,
            shell_mat,
            34
        )

        inner_base = (-2.43, side_sign * 0.83, 0.57)
        outer_base = (-2.43, side_sign * 1.10, 0.58)
        inner_mid = (-2.92, side_sign * 0.75, 0.58)
        outer_mid = (-2.94, side_sign * 1.18, 0.60)
        inner_tip = (-3.45, side_sign * 0.84, 0.60)
        outer_tip = (-3.48, side_sign * 1.09, 0.61)

        add_cylinder_between("CutterInnerFinger", inner_base, inner_mid, 0.105, shell_mat, 20, 0.065)
        add_cylinder_between("CutterOuterFinger", outer_base, outer_mid, 0.105, shell_mat, 20, 0.060)
        add_cylinder_between("CutterInnerPoint", inner_mid, inner_tip, 0.066, shell_mat, 18, 0.014)
        add_cylinder_between("CutterOuterPoint", outer_mid, outer_tip, 0.062, shell_mat, 18, 0.010)

# Large crusher on negative Y, smaller cutter on positive Y.
build_claw(-1, True)
build_claw(1, False)

# -------------------------------------------------------------------
# Long antennae and shorter antennules
# -------------------------------------------------------------------

antenna_left = [
    (-1.43, -0.27, 1.03),
    (-1.78, -0.43, 1.30),
    (-2.25, -0.55, 1.68),
    (-2.82, -0.66, 2.08),
    (-3.45, -0.82, 2.43),
    (-4.08, -1.04, 2.67),
    (-4.58, -1.29, 2.80)
]
antenna_right = [
    (-1.43, 0.27, 1.03),
    (-1.76, 0.43, 1.34),
    (-2.17, 0.58, 1.78),
    (-2.68, 0.73, 2.22),
    (-3.24, 0.91, 2.58),
    (-3.80, 1.15, 2.83),
    (-4.28, 1.43, 2.94)
]
taper = [1.35, 1.20, 1.00, 0.82, 0.62, 0.43, 0.22]
add_curve("LeftLongAntenna", antenna_left, taper, shell_mat, 0.045, 3)
add_curve("RightLongAntenna", antenna_right, taper, shell_mat, 0.045, 3)

# Smaller paired antennules beneath the main antennae.
for side in (-1, 1):
    pts = [
        (-1.50, side * 0.18, 0.98),
        (-1.90, side * 0.28, 1.08),
        (-2.30, side * 0.42, 1.19),
        (-2.68, side * 0.60, 1.24)
    ]
    add_curve("Antennule", pts, [1.0, 0.8, 0.55, 0.22], dark_shell_mat, 0.026, 2)

# -------------------------------------------------------------------
# Convert curves and combine the assembly into a single mesh object.
# -------------------------------------------------------------------

for obj in list(bpy.context.scene.objects):
    if obj.type == 'CURVE':
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target='MESH')
        smooth_mesh(bpy.context.object)

mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for obj in mesh_objects:
    obj.select_set(True)
if mesh_objects:
    bpy.context.view_layer.objects.active = mesh_objects[0]
    bpy.ops.object.join()
    lobster = bpy.context.object
    lobster.name = "Textured_Reddish_Brown_Lobster"
    smooth_mesh(lobster)

    # Apply scale and rotation data while preserving the assembled form.
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Keep the coherent model centered close to the world origin.
    bbox_center = sum((lobster.matrix_world @ Vector(corner) for corner in lobster.bound_box), Vector()) / 8.0
    lobster.location.x -= bbox_center.x
    lobster.location.y -= bbox_center.y
    lobster.location.z -= min((lobster.matrix_world @ Vector(corner)).z for corner in lobster.bound_box)
    bpy.context.view_layer.objects.active = lobster
    lobster.select_set(True)