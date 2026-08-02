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
scene.unit_settings.scale_length = 1.0

def make_material(name, color, roughness=0.72):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

page_materials = [
    make_material("Pages Warm Ivory", (0.79, 0.72, 0.57), 0.86),
    make_material("Pages Pale Cream", (0.88, 0.82, 0.68), 0.88),
    make_material("Pages Aged", (0.69, 0.60, 0.45), 0.90),
]
page_line_materials = [
    make_material("Page Shadow Light", (0.58, 0.50, 0.38), 0.92),
    make_material("Page Shadow Dark", (0.43, 0.36, 0.27), 0.94),
]

cover_materials = [
    make_material("Deep Navy Cloth", (0.055, 0.105, 0.16), 0.62),
    make_material("Burnt Sienna Cover", (0.43, 0.115, 0.055), 0.66),
    make_material("Forest Green Cloth", (0.075, 0.22, 0.13), 0.65),
    make_material("Ochre Cover", (0.58, 0.34, 0.075), 0.68),
    make_material("Burgundy Cloth", (0.30, 0.045, 0.065), 0.62),
    make_material("Dark Teal Cover", (0.035, 0.24, 0.24), 0.67),
    make_material("Brown Leather", (0.25, 0.105, 0.045), 0.58),
]
accent_materials = [
    make_material("Navy Edge Accent", (0.025, 0.052, 0.08), 0.65),
    make_material("Sienna Edge Accent", (0.25, 0.055, 0.025), 0.68),
    make_material("Green Edge Accent", (0.035, 0.12, 0.065), 0.67),
    make_material("Ochre Edge Accent", (0.36, 0.18, 0.025), 0.70),
    make_material("Burgundy Edge Accent", (0.16, 0.018, 0.028), 0.64),
    make_material("Teal Edge Accent", (0.018, 0.13, 0.13), 0.69),
    make_material("Leather Edge Accent", (0.13, 0.045, 0.016), 0.60),
]

created_objects = []

def local_to_world(x, y, z, angle, offset_x, offset_y):
    ca = math.cos(angle)
    sa = math.sin(angle)
    return (
        offset_x + x * ca - y * sa,
        offset_y + x * sa + y * ca,
        z
    )

def create_box(name, dimensions, local_center, angle, offset_x, offset_y,
               material, bevel=0.0, bevel_segments=3):
    location = local_to_world(
        local_center[0], local_center[1], local_center[2],
        angle, offset_x, offset_y
    )
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=(0.0, 0.0, angle))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    if material:
        obj.data.materials.append(material)

    if bevel > 0.0:
        modifier = obj.modifiers.new(name="Softened edges", type='BEVEL')
        modifier.width = min(bevel, min(dimensions) * 0.42)
        modifier.segments = bevel_segments
        modifier.limit_method = 'ANGLE'
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    created_objects.append(obj)
    return obj

books = [
    {
        "w": 3.72, "d": 2.52, "pages": 0.34, "cover": 0.085,
        "angle": math.radians(-4.0), "x": -0.03, "y": 0.01,
        "hard": True, "bands": True
    },
    {
        "w": 3.28, "d": 2.20, "pages": 0.27, "cover": 0.045,
        "angle": math.radians(3.5), "x": 0.13, "y": 0.05,
        "hard": False, "bands": False
    },
    {
        "w": 3.90, "d": 2.64, "pages": 0.40, "cover": 0.082,
        "angle": math.radians(-2.0), "x": -0.02, "y": -0.04,
        "hard": True, "bands": True
    },
    {
        "w": 3.43, "d": 2.34, "pages": 0.30, "cover": 0.052,
        "angle": math.radians(5.0), "x": -0.13, "y": 0.08,
        "hard": False, "bands": False
    },
    {
        "w": 4.02, "d": 2.74, "pages": 0.38, "cover": 0.088,
        "angle": math.radians(-4.5), "x": 0.07, "y": 0.01,
        "hard": True, "bands": True
    },
    {
        "w": 3.54, "d": 2.31, "pages": 0.26, "cover": 0.047,
        "angle": math.radians(2.5), "x": 0.04, "y": -0.01,
        "hard": False, "bands": False
    },
    {
        "w": 3.22, "d": 2.16, "pages": 0.32, "cover": 0.078,
        "angle": math.radians(-6.0), "x": 0.11, "y": 0.06,
        "hard": True, "bands": True
    },
]

z_cursor = 0.0

for index, book in enumerate(books):
    w = book["w"]
    d = book["d"]
    page_h = book["pages"]
    cover_t = book["cover"]
    angle = book["angle"]
    ox = book["x"]
    oy = book["y"]
    hard = book["hard"]

    cover_mat = cover_materials[index]
    accent_mat = accent_materials[index]
    page_mat = page_materials[index % len(page_materials)]

    page_w = w - (0.17 if hard else 0.11)
    page_d = d - (0.22 if hard else 0.14)
    page_y = 0.035
    total_h = page_h + 2.0 * cover_t

    lower_z = z_cursor + cover_t * 0.5
    page_z = z_cursor + cover_t + page_h * 0.5
    upper_z = z_cursor + cover_t + page_h + cover_t * 0.5

    cover_bevel = 0.035 if hard else 0.022

    create_box(
        f"Book {index + 1} Lower Cover",
        (w, d, cover_t),
        (0.0, 0.0, lower_z),
        angle, ox, oy, cover_mat, cover_bevel, 3
    )
    create_box(
        f"Book {index + 1} Upper Cover",
        (w, d, cover_t),
        (0.0, 0.0, upper_z),
        angle, ox, oy, cover_mat, cover_bevel, 3
    )

    create_box(
        f"Book {index + 1} Page Block",
        (page_w, page_d, page_h),
        (0.0, page_y, page_z),
        angle, ox, oy, page_mat, 0.027, 3
    )

    spine_depth = 0.145 if hard else 0.095
    spine_y = -d * 0.5 + spine_depth * 0.43
    create_box(
        f"Book {index + 1} Spine",
        (w - 0.035, spine_depth, total_h - 0.012),
        (0.0, spine_y, z_cursor + total_h * 0.5),
        angle, ox, oy, cover_mat,
        min(0.055, cover_t * 0.62), 4
    )

    hinge_offset = 0.145 if hard else 0.105
    for hinge_side in (-1.0, 1.0):
        hinge_y = -d * 0.5 + hinge_offset
        hinge_z = z_cursor + (cover_t * 0.55 if hinge_side < 0 else total_h - cover_t * 0.55)
        create_box(
            f"Book {index + 1} Hinge {hinge_side}",
            (w - 0.10, 0.035, 0.025 if hard else 0.018),
            (0.0, hinge_y, hinge_z),
            angle, ox, oy, accent_mat, 0.009, 2
        )

    front_y = page_y + page_d * 0.5 + 0.006
    right_x = page_w * 0.5 + 0.006
    left_x = -page_w * 0.5 - 0.006

    line_count = 7 if page_h >= 0.34 else 5
    for line_index in range(1, line_count + 1):
        fraction = line_index / (line_count + 1)
        line_z = z_cursor + cover_t + page_h * fraction
        line_thickness = 0.009 if line_index % 3 else 0.013
        line_mat = page_line_materials[(line_index + index) % 2]

        create_box(
            f"Book {index + 1} Fore-edge Page Line {line_index}",
            (page_w * (0.965 - 0.01 * (line_index % 2)), 0.016, line_thickness),
            (0.0, front_y, line_z),
            angle, ox, oy, line_mat, 0.003, 1
        )

        create_box(
            f"Book {index + 1} Right Page Line {line_index}",
            (0.016, page_d * 0.88, line_thickness),
            (right_x, page_y + 0.025, line_z),
            angle, ox, oy, line_mat, 0.003, 1
        )

        if line_index % 2 == 0:
            create_box(
                f"Book {index + 1} Left Page Line {line_index}",
                (0.016, page_d * 0.78, line_thickness),
                (left_x, page_y + 0.055, line_z),
                angle, ox, oy, line_mat, 0.003, 1
            )

    if hard:
        panel_t = 0.018
        panel_margin_x = 0.18
        panel_margin_y = 0.18
        create_box(
            f"Book {index + 1} Top Inset Panel",
            (w - panel_margin_x * 2.0, d - panel_margin_y * 2.0, panel_t),
            (0.0, 0.018, z_cursor + total_h + panel_t * 0.42),
            angle, ox, oy, accent_mat, 0.025, 3
        )

        border_width = 0.030
        border_z = z_cursor + total_h + panel_t + 0.006
        border_w = w - 0.38
        border_d = d - 0.38
        for bx, by, bdx, bdy in (
            (0.0, border_d * 0.5, border_w, border_width),
            (0.0, -border_d * 0.5, border_w, border_width),
            (border_w * 0.5, 0.0, border_width, border_d),
            (-border_w * 0.5, 0.0, border_width, border_d),
        ):
            create_box(
                f"Book {index + 1} Cover Border",
                (bdx, bdy, 0.014),
                (bx, by + 0.018, border_z),
                angle, ox, oy, cover_mat, 0.006, 2
            )

    if book["bands"]:
        for band_fraction in (-0.34, -0.11, 0.11, 0.34):
            band_x = w * band_fraction
            create_box(
                f"Book {index + 1} Raised Spine Band",
                (0.055, 0.038, total_h * 0.78),
                (band_x, -d * 0.5 - 0.012, z_cursor + total_h * 0.5),
                angle, ox, oy, accent_mat, 0.014, 3
            )

        for cap_x in (-w * 0.43, w * 0.43):
            create_box(
                f"Book {index + 1} Spine End Detail",
                (0.115, 0.031, total_h * 0.62),
                (cap_x, -d * 0.5 - 0.013, z_cursor + total_h * 0.5),
                angle, ox, oy, accent_mat, 0.012, 3
            )

    z_cursor += total_h + 0.018

# Join all geometry into one final mesh while preserving material assignments.
bpy.ops.object.select_all(action='DESELECT')
for obj in created_objects:
    if obj and obj.name in bpy.data.objects:
        obj.select_set(True)

if created_objects:
    bpy.context.view_layer.objects.active = created_objects[0]
    bpy.ops.object.join()
    stack = bpy.context.object
    stack.name = "Irregular Horizontal Book Stack"

    # Merge any coincident vertices created by overlapping decorative geometry.
    bpy.context.view_layer.objects.active = stack
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.00001)
    bpy.ops.object.mode_set(mode='OBJECT')

    for polygon in stack.data.polygons:
        polygon.use_smooth = False

    stack.select_set(True)