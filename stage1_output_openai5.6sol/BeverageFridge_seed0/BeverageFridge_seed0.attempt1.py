import bpy
import math

# Clear the scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
for curve in list(bpy.data.curves):
    if curve.users == 0:
        bpy.data.curves.remove(curve)
for material in list(bpy.data.materials):
    if material.users == 0:
        bpy.data.materials.remove(material)

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'METERS'
scene.render.film_transparent = False

# Keep dark materials from becoming excessively washed out.
scene.view_settings.look = 'AgX - Medium High Contrast'

# Plain white environment.
world = bpy.data.worlds.get("World")
if world is None:
    world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world_nodes = world.node_tree.nodes
background = world_nodes.get("Background")
if background is not None:
    background.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    background.inputs["Strength"].default_value = 0.8


def make_material(name, color, metallic=0.0, roughness=0.4, coat=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color

    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness

    if "Coat Weight" in shader.inputs:
        shader.inputs["Coat Weight"].default_value = coat
    if "Coat Roughness" in shader.inputs:
        shader.inputs["Coat Roughness"].default_value = max(0.08, roughness * 0.6)

    return material


cabinet_material = make_material(
    "Deep Brown Cabinet",
    (0.026, 0.007, 0.0025, 1.0),
    metallic=0.04,
    roughness=0.42,
    coat=0.10
)

door_material = make_material(
    "Deep Brown Door",
    (0.038, 0.009, 0.003, 1.0),
    metallic=0.04,
    roughness=0.36,
    coat=0.15
)

gasket_material = make_material(
    "Black Door Gasket",
    (0.003, 0.002, 0.0015, 1.0),
    metallic=0.0,
    roughness=0.72
)

glass_material = make_material(
    "Smoked Glass Top",
    (0.006, 0.007, 0.008, 1.0),
    metallic=0.05,
    roughness=0.16,
    coat=0.55
)

metal_material = make_material(
    "Brushed Metal Handle",
    (0.34, 0.38, 0.40, 1.0),
    metallic=0.92,
    roughness=0.31,
    coat=0.08
)

rubber_material = make_material(
    "Black Rubber",
    (0.0025, 0.0025, 0.0025, 1.0),
    metallic=0.0,
    roughness=0.82
)


def apply_bevel(obj, width, segments=3):
    modifier = obj.modifiers.new("Soft Edges", 'BEVEL')
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = 'ANGLE'
    modifier.angle_limit = math.radians(25.0)
    modifier.harden_normals = True

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def add_box(name, location, dimensions, material, bevel=0.0, segments=3):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    if material is not None:
        obj.data.materials.append(material)

    if bevel > 0.0:
        apply_bevel(obj, bevel, segments)

    return obj


def add_cylinder(
    name,
    radius,
    depth,
    location,
    material,
    rotation=(0.0, 0.0, 0.0),
    vertices=40,
    bevel=0.0
):
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

    if material is not None:
        obj.data.materials.append(material)

    if bevel > 0.0:
        apply_bevel(obj, bevel, 3)

    for polygon in obj.data.polygons:
        polygon.use_smooth = True

    return obj


# Compact, nearly cube-shaped insulated cabinet.
body = add_box(
    "Refrigerator Cabinet",
    location=(0.0, 0.0, 0.67),
    dimensions=(1.24, 1.10, 1.20),
    material=cabinet_material,
    bevel=0.042,
    segments=5
)

# Recessed underside and short feet.
add_box(
    "Recessed Underside",
    location=(0.0, 0.015, 0.075),
    dimensions=(1.08, 0.92, 0.07),
    material=rubber_material,
    bevel=0.018,
    segments=3
)

for x in (-0.47, 0.47):
    for y in (-0.38, 0.38):
        add_cylinder(
            "Rubber Foot",
            radius=0.052,
            depth=0.065,
            location=(x, y, 0.0325),
            material=rubber_material,
            vertices=28,
            bevel=0.007
        )

# Dark gasket frame behind the front door.
frame_y = -0.566

add_box(
    "Left Gasket",
    location=(-0.555, frame_y, 0.69),
    dimensions=(0.030, 0.035, 1.08),
    material=gasket_material,
    bevel=0.006,
    segments=2
)
add_box(
    "Right Gasket",
    location=(0.555, frame_y, 0.69),
    dimensions=(0.030, 0.035, 1.08),
    material=gasket_material,
    bevel=0.006,
    segments=2
)
add_box(
    "Upper Gasket",
    location=(0.0, frame_y, 1.215),
    dimensions=(1.08, 0.035, 0.030),
    material=gasket_material,
    bevel=0.006,
    segments=2
)
add_box(
    "Lower Gasket",
    location=(0.0, frame_y, 0.165),
    dimensions=(1.08, 0.035, 0.030),
    material=gasket_material,
    bevel=0.006,
    segments=2
)

# Separate rounded front door.
door = add_box(
    "Front Door",
    location=(0.0, -0.605, 0.69),
    dimensions=(1.08, 0.095, 1.02),
    material=door_material,
    bevel=0.032,
    segments=5
)

# Restrained dark toe kick beneath the door.
add_box(
    "Front Toe Kick",
    location=(0.0, -0.610, 0.115),
    dimensions=(1.02, 0.065, 0.075),
    material=rubber_material,
    bevel=0.014,
    segments=3
)

# Thin support and smooth smoked-glass top.
add_box(
    "Glass Top Support",
    location=(0.0, 0.0, 1.282),
    dimensions=(1.20, 1.06, 0.030),
    material=gasket_material,
    bevel=0.012,
    segments=3
)

add_box(
    "Dark Glass Top",
    location=(0.0, -0.005, 1.315),
    dimensions=(1.29, 1.14, 0.050),
    material=glass_material,
    bevel=0.022,
    segments=5
)

# Vertical metallic handle on the front-right side.
handle_x = 0.425
handle_y = -0.715
handle_z = 0.705
handle_length = 0.70

add_cylinder(
    "Vertical Door Handle",
    radius=0.033,
    depth=handle_length,
    location=(handle_x, handle_y, handle_z),
    material=metal_material,
    vertices=48,
    bevel=0.008
)

# Rounded handle ends.
for z in (
    handle_z - handle_length * 0.5,
    handle_z + handle_length * 0.5
):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        radius=0.033,
        location=(handle_x, handle_y, z)
    )
    cap = bpy.context.object
    cap.name = "Handle End Cap"
    cap.data.materials.append(metal_material)
    for polygon in cap.data.polygons:
        polygon.use_smooth = True

# Two firmly connected stand-offs.
for z in (0.48, 0.93):
    add_cylinder(
        "Handle Stand-off",
        radius=0.024,
        depth=0.090,
        location=(handle_x, -0.675, z),
        material=metal_material,
        rotation=(math.radians(90.0), 0.0, 0.0),
        vertices=36,
        bevel=0.005
    )

    add_cylinder(
        "Handle Mount",
        radius=0.044,
        depth=0.018,
        location=(handle_x, -0.653, z),
        material=metal_material,
        rotation=(math.radians(90.0), 0.0, 0.0),
        vertices=40,
        bevel=0.004
    )

# Place all generated geometry in one coherent collection.
assembly_collection = bpy.data.collections.new("Compact Beverage Refrigerator")
scene.collection.children.link(assembly_collection)

for obj in list(scene.collection.objects):
    if obj.type == 'MESH':
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        assembly_collection.objects.link(obj)

bpy.ops.object.select_all(action='DESELECT')
for obj in assembly_collection.objects:
    obj.select_set(True)

bpy.context.view_layer.objects.active = door