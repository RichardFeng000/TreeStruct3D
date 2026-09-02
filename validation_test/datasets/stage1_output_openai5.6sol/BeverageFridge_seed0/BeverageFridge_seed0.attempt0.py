import bpy
import math

from mathutils import Vector

# Clear the default scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    if datablocks != bpy.data.materials:
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'METERS'

# Plain white world background without adding backdrop geometry.
world = bpy.data.worlds.get("World")
if world is None:
    world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
background = world.node_tree.nodes.get("Background")
if background:
    background.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    background.inputs["Strength"].default_value = 0.8


def make_material(name, color, metallic=0.0, roughness=0.4,
                  coat=0.0, transmission=0.0, ior=1.45):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["IOR"].default_value = ior
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
    if "Coat Roughness" in bsdf.inputs:
        bsdf.inputs["Coat Roughness"].default_value = max(0.02, roughness * 0.5)
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    return mat


cabinet_mat = make_material(
    "Dark Brown Cabinet",
    (0.075, 0.025, 0.012, 1.0),
    metallic=0.08,
    roughness=0.27,
    coat=0.20
)
door_mat = make_material(
    "Dark Brown Door",
    (0.105, 0.033, 0.014, 1.0),
    metallic=0.10,
    roughness=0.22,
    coat=0.28
)
edge_mat = make_material(
    "Dark Door Gasket",
    (0.008, 0.005, 0.004, 1.0),
    metallic=0.0,
    roughness=0.58
)
glass_mat = make_material(
    "Dark Glass Top",
    (0.012, 0.009, 0.008, 1.0),
    metallic=0.0,
    roughness=0.065,
    coat=0.65,
    transmission=0.12,
    ior=1.50
)
metal_mat = make_material(
    "Brushed Stainless Steel",
    (0.42, 0.47, 0.50, 1.0),
    metallic=0.96,
    roughness=0.19,
    coat=0.12
)
black_mat = make_material(
    "Black Underside",
    (0.006, 0.006, 0.006, 1.0),
    metallic=0.0,
    roughness=0.48
)


def bevel_object(obj, width, segments=3):
    modifier = obj.modifiers.new(name="Rounded Edges", type='BEVEL')
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
    if material:
        obj.data.materials.append(material)
    if bevel > 0.0:
        bevel_object(obj, bevel, segments)
    return obj


def add_cylinder(name, radius, depth, location, material,
                 rotation=(0.0, 0.0, 0.0), vertices=32, bevel=0.0):
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
    if bevel > 0.0:
        bevel_object(obj, bevel, 3)

    # Smooth cylindrical and bevel surfaces while retaining stable cap geometry.
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


# Main insulated cabinet, raised slightly to allow low feet beneath it.
body = add_box(
    "Refrigerator Cabinet",
    location=(0.0, 0.0, 0.72),
    dimensions=(1.34, 1.18, 1.32),
    material=cabinet_mat,
    bevel=0.055,
    segments=5
)

# Slightly recessed lower underside gives the appliance a grounded toe-kick profile.
underside = add_box(
    "Bottom Underside",
    location=(0.0, 0.005, 0.075),
    dimensions=(1.16, 1.02, 0.085),
    material=black_mat,
    bevel=0.025,
    segments=3
)

# Four compact anti-vibration feet.
for x in (-0.49, 0.49):
    for y in (-0.41, 0.41):
        add_cylinder(
            "Rubber Foot",
            radius=0.066,
            depth=0.06,
            location=(x, y, 0.03),
            material=black_mat,
            vertices=24,
            bevel=0.009
        )

# Door gasket visible as a narrow dark frame in the perimeter gap.
add_box(
    "Left Door Gasket",
    location=(-0.606, -0.601, 0.72),
    dimensions=(0.032, 0.035, 1.205),
    material=edge_mat,
    bevel=0.008,
    segments=2
)
add_box(
    "Right Door Gasket",
    location=(0.606, -0.601, 0.72),
    dimensions=(0.032, 0.035, 1.205),
    material=edge_mat,
    bevel=0.008,
    segments=2
)
add_box(
    "Upper Door Gasket",
    location=(0.0, -0.601, 1.315),
    dimensions=(1.205, 0.035, 0.032),
    material=edge_mat,
    bevel=0.008,
    segments=2
)
add_box(
    "Lower Door Gasket",
    location=(0.0, -0.601, 0.125),
    dimensions=(1.205, 0.035, 0.032),
    material=edge_mat,
    bevel=0.008,
    segments=2
)

# Main rounded refrigerator door.
door = add_box(
    "Front Door",
    location=(0.0, -0.618, 0.72),
    dimensions=(1.17, 0.105, 1.16),
    material=door_mat,
    bevel=0.042,
    segments=5
)

# Dark recessed toe strip beneath the door.
toe_strip = add_box(
    "Front Toe Kick",
    location=(0.0, -0.623, 0.105),
    dimensions=(1.06, 0.055, 0.075),
    material=black_mat,
    bevel=0.018,
    segments=3
)

# Thin upper door reveal emphasizes the separate opening panel.
upper_reveal = add_box(
    "Upper Door Reveal",
    location=(0.0, -0.674, 1.275),
    dimensions=(1.035, 0.008, 0.014),
    material=edge_mat,
    bevel=0.004,
    segments=2
)

# Smooth dark glass top with a small overhang.
glass_top = add_box(
    "Dark Glass Top",
    location=(0.0, -0.005, 1.405),
    dimensions=(1.38, 1.215, 0.055),
    material=glass_mat,
    bevel=0.032,
    segments=6
)

# Thin dark support layer beneath the glass makes the glass slab edge readable.
glass_support = add_box(
    "Glass Top Support",
    location=(0.0, -0.002, 1.372),
    dimensions=(1.31, 1.145, 0.027),
    material=edge_mat,
    bevel=0.018,
    segments=3
)

# Vertical brushed-metal handle on the right side of the front door.
handle_x = 0.455
handle_y = -0.765
handle_z = 0.735
handle_length = 0.80

handle = add_cylinder(
    "Vertical Metal Handle",
    radius=0.034,
    depth=handle_length,
    location=(handle_x, handle_y, handle_z),
    material=metal_mat,
    vertices=40,
    bevel=0.009
)

# Rounded metal end caps.
for z in (handle_z - handle_length * 0.5, handle_z + handle_length * 0.5):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        radius=0.0345,
        location=(handle_x, handle_y, z)
    )
    cap = bpy.context.object
    cap.name = "Handle Rounded End"
    cap.data.materials.append(metal_mat)
    for polygon in cap.data.polygons:
        polygon.use_smooth = True

# Two horizontal stand-offs connecting the handle to the door.
for z in (0.455, 1.015):
    add_cylinder(
        "Handle Stand-off",
        radius=0.026,
        depth=0.105,
        location=(handle_x, -0.711, z),
        material=metal_mat,
        rotation=(math.radians(90.0), 0.0, 0.0),
        vertices=32,
        bevel=0.006
    )
    add_cylinder(
        "Handle Mounting Rosette",
        radius=0.052,
        depth=0.014,
        location=(handle_x, -0.678, z),
        material=metal_mat,
        rotation=(math.radians(90.0), 0.0, 0.0),
        vertices=36,
        bevel=0.004
    )

# Organize all generated geometry in a single named collection.
fridge_collection = bpy.data.collections.new("Compact Beverage Refrigerator")
scene.collection.children.link(fridge_collection)

for obj in list(scene.collection.objects):
    if obj.type == 'MESH':
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        fridge_collection.objects.link(obj)

# Set sensible viewport colors and select the coherent assembly.
bpy.ops.object.select_all(action='DESELECT')
for obj in fridge_collection.objects:
    obj.select_set(True)

if door:
    bpy.context.view_layer.objects.active = door
