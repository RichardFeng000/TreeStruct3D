import bpy
import math

# Clear the default scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    pass

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

# Materials
def make_material(name, color, roughness=0.55, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return mat

mat_body = make_material("Cabinet Shadow Gaps", (0.105, 0.115, 0.115), 0.48)
mat_plinth = make_material("Recessed Toe Kick", (0.075, 0.080, 0.078), 0.42)
mat_counter = make_material("Light Countertop", (0.84, 0.825, 0.765), 0.36)
mat_counter_edge = make_material("Countertop Underside", (0.66, 0.645, 0.59), 0.44)
mat_warm_gray = make_material("Warm Gray Fronts", (0.43, 0.415, 0.375), 0.52)
mat_taupe = make_material("Taupe Fronts", (0.53, 0.485, 0.415), 0.55)
mat_cream = make_material("Cream Fronts", (0.69, 0.665, 0.595), 0.56)
mat_sage = make_material("Muted Sage Fronts", (0.39, 0.44, 0.39), 0.57)
mat_side = make_material("End Panels", (0.48, 0.465, 0.415), 0.54)
mat_metal = make_material("Brushed Metal Hardware", (0.20, 0.205, 0.19), 0.28, 0.72)

def create_box(name, location, dimensions, material, bevel=0.0, segments=3):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    if bevel > 0.0:
        modifier = obj.modifiers.new(name="Softened Edges", type='BEVEL')
        modifier.width = bevel
        modifier.segments = segments
        modifier.limit_method = 'ANGLE'
    return obj

def create_cylinder(name, location, radius, depth, material, rotation=(0.0, 0.0, 0.0), vertices=20, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    if bevel > 0.0:
        modifier = obj.modifiers.new(name="Rounded Ends", type='BEVEL')
        modifier.width = bevel
        modifier.segments = 2
    return obj

# Main cabinet body and recessed base.
create_box(
    "Main Cabinet Carcass",
    (0.0, 0.0, 1.365),
    (6.20, 1.96, 2.17),
    mat_body,
    bevel=0.035,
    segments=3
)
create_box(
    "Recessed Toe Kick",
    (0.0, 0.105, 0.16),
    (5.94, 1.69, 0.32),
    mat_plinth,
    bevel=0.025,
    segments=2
)

# Thin underside shadow/support beneath the worktop.
create_box(
    "Countertop Underside",
    (0.0, 0.0, 2.475),
    (6.40, 2.12, 0.09),
    mat_counter_edge,
    bevel=0.025,
    segments=3
)

# Light-colored overhanging countertop slab.
create_box(
    "Light Countertop Slab",
    (0.0, 0.0, 2.62),
    (6.72, 2.38, 0.24),
    mat_counter,
    bevel=0.065,
    segments=5
)

front_y = -1.015
panel_depth = 0.085
panel_bottom = 0.43
panel_top = 2.35
panel_height = panel_top - panel_bottom

def add_front_panel(name, x, z, width, height, material, bevel=0.025):
    return create_box(
        name,
        (x, front_y, z),
        (width, panel_depth, height),
        material,
        bevel=bevel,
        segments=3
    )

def add_horizontal_handle(name, x, z, width=0.50):
    y_bar = -1.125
    create_box(
        name + " Bar",
        (x, y_bar, z),
        (width, 0.075, 0.075),
        mat_metal,
        bevel=0.035,
        segments=4
    )
    for side in (-1.0, 1.0):
        create_cylinder(
            name + (" Left Mount" if side < 0 else " Right Mount"),
            (x + side * (width * 0.36), -1.075, z),
            0.035,
            0.105,
            mat_metal,
            rotation=(math.pi / 2.0, 0.0, 0.0),
            vertices=16,
            bevel=0.008
        )

def add_vertical_handle(name, x, z, height=0.50):
    y_bar = -1.125
    create_box(
        name + " Bar",
        (x, y_bar, z),
        (0.075, 0.075, height),
        mat_metal,
        bevel=0.035,
        segments=4
    )
    for side in (-1.0, 1.0):
        create_cylinder(
            name + (" Lower Mount" if side < 0 else " Upper Mount"),
            (x, -1.075, z + side * (height * 0.36)),
            0.035,
            0.105,
            mat_metal,
            rotation=(math.pi / 2.0, 0.0, 0.0),
            vertices=16,
            bevel=0.008
        )

# Left tall cabinet door.
add_front_panel(
    "Left Tall Door",
    -2.345,
    (panel_bottom + panel_top) * 0.5,
    1.34,
    panel_height,
    mat_warm_gray
)
add_vertical_handle("Left Door Handle", -1.83, 1.40, 0.54)

# First drawer bank: four closed drawer fronts.
drawer_x = -0.925
drawer_w = 1.40
drawer_gap = 0.055
drawer_heights = (0.43, 0.43, 0.46, 0.46)
cursor = panel_top
for index, height in enumerate(drawer_heights):
    center_z = cursor - height * 0.5
    add_front_panel(
        "Center Left Drawer %02d" % (index + 1),
        drawer_x,
        center_z,
        drawer_w,
        height,
        (mat_taupe if index % 2 == 0 else mat_cream),
        bevel=0.022
    )
    add_horizontal_handle(
        "Center Left Drawer %02d Handle" % (index + 1),
        drawer_x,
        center_z + height * 0.20,
        0.54
    )
    cursor -= height + drawer_gap

# Double-door center-right section.
double_center = 0.70
door_gap = 0.055
double_total_width = 1.72
single_width = (double_total_width - door_gap) * 0.5
left_door_x = double_center - (single_width + door_gap) * 0.5
right_door_x = double_center + (single_width + door_gap) * 0.5

add_front_panel(
    "Center Right Left Door",
    left_door_x,
    (panel_bottom + panel_top) * 0.5,
    single_width,
    panel_height,
    mat_sage
)
add_front_panel(
    "Center Right Right Door",
    right_door_x,
    (panel_bottom + panel_top) * 0.5,
    single_width,
    panel_height,
    mat_sage
)
add_vertical_handle("Center Right Left Door Handle", double_center - 0.16, 1.40, 0.52)
add_vertical_handle("Center Right Right Door Handle", double_center + 0.16, 1.40, 0.52)

# Right drawer bank with three drawers.
drawer_x = 2.31
drawer_w = 1.36
drawer_gap = 0.055
drawer_heights = (0.48, 0.63, 0.70)
cursor = panel_top
for index, height in enumerate(drawer_heights):
    center_z = cursor - height * 0.5
    add_front_panel(
        "Right Drawer %02d" % (index + 1),
        drawer_x,
        center_z,
        drawer_w,
        height,
        (mat_cream, mat_taupe, mat_warm_gray)[index],
        bevel=0.022
    )
    add_horizontal_handle(
        "Right Drawer %02d Handle" % (index + 1),
        drawer_x,
        center_z + height * 0.22,
        0.55
    )
    cursor -= height + drawer_gap

# Side end panels, giving the island a finished three-quarter-view appearance.
create_box(
    "Right Finished End Panel",
    (3.125, 0.0, 1.39),
    (0.085, 1.80, 1.88),
    mat_side,
    bevel=0.028,
    segments=3
)
create_box(
    "Right End Inset Field",
    (3.174, 0.0, 1.39),
    (0.035, 1.46, 1.52),
    mat_warm_gray,
    bevel=0.035,
    segments=3
)
create_box(
    "Left Finished End Panel",
    (-3.125, 0.0, 1.39),
    (0.085, 1.80, 1.88),
    mat_side,
    bevel=0.028,
    segments=3
)
create_box(
    "Left End Inset Field",
    (-3.174, 0.0, 1.39),
    (0.035, 1.46, 1.52),
    mat_taupe,
    bevel=0.035,
    segments=3
)

# Closed panels on the reverse side so the island remains complete from all views.
back_y = 1.015
back_panel_specs = (
    (-2.03, 1.84, mat_warm_gray),
    (0.00, 2.05, mat_cream),
    (2.03, 1.84, mat_sage),
)
for index, (x, width, material) in enumerate(back_panel_specs):
    create_box(
        "Rear Closed Panel %02d" % (index + 1),
        (x, back_y, 1.39),
        (width, panel_depth, panel_height),
        material,
        bevel=0.025,
        segments=3
    )

# Narrow vertical rear seams/fillers add visible cabinet divisions.
for index, x in enumerate((-1.005, 1.005)):
    create_box(
        "Rear Divider %02d" % (index + 1),
        (x, 1.064, 1.39),
        (0.045, 0.025, panel_height),
        mat_body,
        bevel=0.008,
        segments=2
    )

# Keep the assembly centered and selected as the final modeled object group.
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
bpy.context.view_layer.objects.active = bpy.data.objects.get("Main Cabinet Carcass")