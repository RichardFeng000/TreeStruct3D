import bpy
import math

from mathutils import Vector


# Clear the default scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    if datablocks is not bpy.data.materials:
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def make_material(name, color, metallic=0.0, roughness=0.45):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True

    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return material


def make_cloud_display_material():
    material = bpy.data.materials.new("Gray Cloud Display")
    material.diffuse_color = (0.29, 0.31, 0.32, 1.0)
    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.name = "Display Coordinates"
    texcoord.location = (-650, 0)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.name = "Cloud Mapping"
    mapping.location = (-470, 0)
    mapping.inputs["Scale"].default_value = (0.75, 1.0, 1.15)

    noise_large = nodes.new("ShaderNodeTexNoise")
    noise_large.name = "Large Soft Clouds"
    noise_large.location = (-270, 70)
    noise_large.noise_dimensions = '3D'
    noise_large.inputs["Scale"].default_value = 2.2
    noise_large.inputs["Detail"].default_value = 5.0
    noise_large.inputs["Roughness"].default_value = 0.72
    noise_large.inputs["Lacunarity"].default_value = 2.1
    noise_large.inputs["Distortion"].default_value = 0.18

    noise_fine = nodes.new("ShaderNodeTexNoise")
    noise_fine.name = "Fine Cloud Detail"
    noise_fine.location = (-270, -150)
    noise_fine.noise_dimensions = '3D'
    noise_fine.inputs["Scale"].default_value = 8.0
    noise_fine.inputs["Detail"].default_value = 3.0
    noise_fine.inputs["Roughness"].default_value = 0.65

    mix = nodes.new("ShaderNodeMix")
    mix.name = "Cloud Layers"
    mix.data_type = 'FLOAT'
    mix.blend_type = 'MULTIPLY'
    mix.location = (-30, 20)
    mix.inputs["Factor"].default_value = 0.32

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.name = "Cloud Gray Palette"
    ramp.location = (180, 50)
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    e0 = ramp.color_ramp.elements[0]
    e0.position = 0.18
    e0.color = (0.12, 0.14, 0.15, 1.0)

    e1 = ramp.color_ramp.elements.new(0.43)
    e1.color = (0.27, 0.30, 0.31, 1.0)

    e2 = ramp.color_ramp.elements.new(0.66)
    e2.color = (0.48, 0.50, 0.50, 1.0)

    e3 = ramp.color_ramp.elements.new(0.84)
    e3.color = (0.68, 0.68, 0.65, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.name = "Subtle Display Grain"
    bump.location = (205, -155)
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.025

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_large.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_fine.inputs["Vector"])
    links.new(noise_large.outputs["Fac"], mix.inputs[2])
    links.new(noise_fine.outputs["Fac"], mix.inputs[3])
    links.new(mix.outputs["Result"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise_fine.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    bsdf.inputs["Metallic"].default_value = 0.05
    bsdf.inputs["Roughness"].default_value = 0.48
    return material


silver = make_material("Brushed Silver", (0.57, 0.58, 0.56), 0.78, 0.25)
silver_light = make_material("Light Silver Trim", (0.73, 0.74, 0.71), 0.82, 0.20)
champagne = make_material("Light Tan Metallic Bezel", (0.70, 0.61, 0.46), 0.72, 0.25)
champagne_edge = make_material("Champagne Highlight", (0.82, 0.73, 0.57), 0.70, 0.22)
graphite = make_material("Dark Graphite", (0.075, 0.082, 0.087), 0.58, 0.30)
base_top_material = make_material("Dark Base Top", (0.105, 0.112, 0.115), 0.48, 0.25)
rear_material = make_material("Rear Housing", (0.20, 0.215, 0.215), 0.65, 0.29)
screen_material = make_cloud_display_material()


def add_beveled_cube(name, location, dimensions, material, bevel=0.04, segments=3):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    if material:
        obj.data.materials.append(material)

    if bevel > 0.0:
        modifier = obj.modifiers.new("Rounded Edges", 'BEVEL')
        modifier.width = bevel
        modifier.segments = segments
        modifier.limit_method = 'ANGLE'
        modifier.angle_limit = math.radians(25.0)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    return obj


def add_cylinder(name, location, radius, depth, material, rotation=(0.0, 0.0, 0.0), vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        end_fill_type='NGON',
        location=location,
        rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    if material:
        obj.data.materials.append(material)

    bevel = obj.modifiers.new("Edge Softening", 'BEVEL')
    bevel.width = min(radius * 0.14, 0.035)
    bevel.segments = 3
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)

    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def make_extruded_profile(name, profile, y_front, y_back, material, bevel=0.05):
    count = len(profile)
    vertices = [(x, y_front, z) for x, z in profile]
    vertices.extend((x, y_back, z) for x, z in profile)

    faces = []
    faces.append(tuple(range(count - 1, -1, -1)))
    faces.append(tuple(range(count, count * 2)))

    for i in range(count):
        nxt = (i + 1) % count
        faces.append((i, nxt, count + nxt, count + i))

    mesh = bpy.data.meshes.new(name + " Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if material:
        obj.data.materials.append(material)

    bevel_modifier = obj.modifiers.new("Soft Machined Edges", 'BEVEL')
    bevel_modifier.width = bevel
    bevel_modifier.segments = 4
    bevel_modifier.limit_method = 'ANGLE'
    bevel_modifier.angle_limit = math.radians(20.0)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=bevel_modifier.name)
    obj.select_set(False)
    return obj


# Wide, low-profile dark base stand.
add_beveled_cube(
    "Wide Dark Base",
    (0.0, 0.08, 0.16),
    (4.90, 2.18, 0.32),
    graphite,
    bevel=0.15,
    segments=5
)

add_beveled_cube(
    "Base Upper Inset",
    (0.0, 0.04, 0.305),
    (4.54, 1.88, 0.13),
    base_top_material,
    bevel=0.105,
    segments=4
)

add_beveled_cube(
    "Base Front Silver Accent",
    (0.0, -0.996, 0.155),
    (4.30, 0.035, 0.095),
    silver,
    bevel=0.025,
    segments=3
)

# Pedestal foot collar and tapered central arm.
add_beveled_cube(
    "Pedestal Foot Collar",
    (0.0, 0.18, 0.42),
    (1.06, 0.72, 0.20),
    silver,
    bevel=0.085,
    segments=4
)

pedestal_profile = [
    (-0.48, 0.43),
    (0.48, 0.43),
    (0.37, 0.68),
    (0.285, 2.25),
    (0.34, 2.54),
    (0.43, 2.70),
    (0.43, 2.98),
    (-0.43, 2.98),
    (-0.43, 2.70),
    (-0.34, 2.54),
    (-0.285, 2.25),
    (-0.37, 0.68)
]
make_extruded_profile(
    "Slim Central Pedestal",
    pedestal_profile,
    -0.015,
    0.405,
    silver,
    bevel=0.055
)

add_beveled_cube(
    "Pedestal Front Accent",
    (0.0, -0.044, 1.55),
    (0.29, 0.035, 1.48),
    champagne,
    bevel=0.025,
    segments=3
)

# Horizontal hinge assembly tucked behind the panel.
add_cylinder(
    "Monitor Hinge",
    (0.0, 0.25, 2.82),
    0.22,
    1.20,
    graphite,
    rotation=(0.0, math.radians(90.0), 0.0),
    vertices=48
)

add_cylinder(
    "Left Hinge Cap",
    (-0.625, 0.25, 2.82),
    0.17,
    0.075,
    silver_light,
    rotation=(0.0, math.radians(90.0), 0.0),
    vertices=48
)

add_cylinder(
    "Right Hinge Cap",
    (0.625, 0.25, 2.82),
    0.17,
    0.075,
    silver_light,
    rotation=(0.0, math.radians(90.0), 0.0),
    vertices=48
)

# Thin rear monitor housing.
add_beveled_cube(
    "Thin Rear Monitor Housing",
    (0.0, 0.0, 4.55),
    (7.20, 0.34, 4.30),
    rear_material,
    bevel=0.115,
    segments=5
)

# Slight rear central cover gives the back shell a manufactured contour.
add_beveled_cube(
    "Rear Center Cover",
    (0.0, 0.195, 4.47),
    (3.10, 0.10, 2.66),
    graphite,
    bevel=0.14,
    segments=5
)

# Champagne-tan metallic front bezel.
add_beveled_cube(
    "Bezel Left",
    (-3.42, -0.205, 4.55),
    (0.36, 0.14, 4.06),
    champagne,
    bevel=0.055,
    segments=4
)

add_beveled_cube(
    "Bezel Right",
    (3.42, -0.205, 4.55),
    (0.36, 0.14, 4.06),
    champagne,
    bevel=0.055,
    segments=4
)

add_beveled_cube(
    "Bezel Top",
    (0.0, -0.205, 6.55),
    (6.62, 0.14, 0.30),
    champagne,
    bevel=0.055,
    segments=4
)

add_beveled_cube(
    "Bezel Bottom",
    (0.0, -0.205, 2.64),
    (6.62, 0.14, 0.48),
    champagne,
    bevel=0.065,
    segments=4
)

# Gray cloud-textured display, inset just behind the bezel.
add_beveled_cube(
    "Cloud Textured Display",
    (0.0, -0.238, 4.63),
    (6.28, 0.046, 3.48),
    screen_material,
    bevel=0.018,
    segments=3
)

# Narrow silver inner trim surrounding the display.
trim_depth = 0.042
add_beveled_cube(
    "Inner Trim Left",
    (-3.168, -0.259, 4.63),
    (0.060, trim_depth, 3.54),
    silver_light,
    bevel=0.018,
    segments=3
)

add_beveled_cube(
    "Inner Trim Right",
    (3.168, -0.259, 4.63),
    (0.060, trim_depth, 3.54),
    silver_light,
    bevel=0.018,
    segments=3
)

add_beveled_cube(
    "Inner Trim Top",
    (0.0, -0.259, 6.386),
    (6.39, trim_depth, 0.060),
    silver_light,
    bevel=0.018,
    segments=3
)

add_beveled_cube(
    "Inner Trim Bottom",
    (0.0, -0.259, 2.874),
    (6.39, trim_depth, 0.060),
    silver_light,
    bevel=0.018,
    segments=3
)

# Fine metallic highlight strips along the bezel's outer side edges.
add_beveled_cube(
    "Left Bezel Highlight",
    (-3.575, -0.276, 4.55),
    (0.035, 0.030, 3.83),
    champagne_edge,
    bevel=0.012,
    segments=2
)

add_beveled_cube(
    "Right Bezel Highlight",
    (3.575, -0.276, 4.55),
    (0.035, 0.030, 3.83),
    champagne_edge,
    bevel=0.012,
    segments=2
)

# Small physical status indicator inset into the lower bezel.
indicator_material = make_material("Status Indicator", (0.33, 0.42, 0.40), 0.15, 0.22)
add_beveled_cube(
    "Status Indicator",
    (3.00, -0.282, 2.635),
    (0.105, 0.026, 0.030),
    indicator_material,
    bevel=0.012,
    segments=3
)

# Keep the completed assembly cleanly selected and centered at the origin.
bpy.ops.object.select_all(action='DESELECT')