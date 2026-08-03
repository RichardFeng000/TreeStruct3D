import bpy
import bmesh
import math
from mathutils import Vector, Matrix

# Clear the default scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

for datablocks in (bpy.data.meshes, bpy.data.curves):
    for datablock in list(datablocks):
        if datablock.users == 0:
            datablocks.remove(datablock)


def make_material(name, color, metallic=0.0, roughness=0.45):
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        base_color = bsdf.inputs.get("Base Color")
        metallic_input = bsdf.inputs.get("Metallic")
        roughness_input = bsdf.inputs.get("Roughness")
        if base_color:
            base_color.default_value = (*color, 1.0)
        if metallic_input:
            metallic_input.default_value = metallic
        if roughness_input:
            roughness_input.default_value = roughness
    return mat


purple = make_material(
    "Deep Aubergine Ceramic",
    (0.105, 0.018, 0.155),
    metallic=0.0,
    roughness=0.22
)
purple_edge = make_material(
    "Aubergine Rim",
    (0.155, 0.032, 0.225),
    metallic=0.0,
    roughness=0.20
)
wood = make_material(
    "Warm Walnut Wood",
    (0.31, 0.125, 0.045),
    metallic=0.0,
    roughness=0.38
)
wood_light = make_material(
    "Turned Walnut Highlights",
    (0.43, 0.205, 0.075),
    metallic=0.0,
    roughness=0.34
)
wood_dark = make_material(
    "Walnut End Grain",
    (0.20, 0.065, 0.022),
    metallic=0.0,
    roughness=0.46
)


def smooth_object(obj):
    if obj.type == 'MESH':
        for polygon in obj.data.polygons:
            polygon.use_smooth = True


def rounded_box(name, location, dimensions, material, bevel=0.06, segments=4):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    modifier = obj.modifiers.new(name="Soft rounded wooden edges", type='BEVEL')
    modifier.width = bevel
    modifier.segments = segments
    modifier.limit_method = 'ANGLE'

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.data.materials.append(material)
    return obj


def cylinder(
    name,
    radius,
    depth,
    location,
    material,
    vertices=32,
    bevel=0.0
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        end_fill_type='NGON',
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)

    if bevel > 0.0:
        modifier = obj.modifiers.new(name="Rounded turned edges", type='BEVEL')
        modifier.width = bevel
        modifier.segments = 3
        modifier.limit_method = 'ANGLE'
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    smooth_object(obj)
    return obj


def sphere(
    name,
    radius,
    location,
    material,
    scale=(1.0, 1.0, 1.0),
    segments=32,
    rings=16
):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=radius,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    smooth_object(obj)
    return obj


def torus(
    name,
    major_radius,
    minor_radius,
    location,
    rotation,
    material,
    major_segments=96,
    minor_segments=12
):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=major_segments,
        minor_segments=minor_segments,
        major_radius=major_radius,
        minor_radius=minor_radius,
        location=location,
        rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    smooth_object(obj)
    return obj


# Wooden base rails.
rounded_box(
    "Left front-to-back foot",
    (-1.17, -0.01, 0.13),
    (0.28, 1.62, 0.26),
    wood,
    bevel=0.075
)
rounded_box(
    "Right front-to-back foot",
    (1.17, -0.01, 0.13),
    (0.28, 1.62, 0.26),
    wood,
    bevel=0.075
)
rounded_box(
    "Front lower cross rail",
    (0.0, -0.69, 0.21),
    (2.62, 0.25, 0.25),
    wood_light,
    bevel=0.07
)
rounded_box(
    "Rear lower cross rail",
    (0.0, 0.66, 0.21),
    (2.62, 0.25, 0.25),
    wood,
    bevel=0.07
)
rounded_box(
    "Rear supporting crossbar",
    (0.0, 0.43, 0.62),
    (2.62, 0.19, 0.21),
    wood_light,
    bevel=0.065
)

# Tall rear turned pegs.
for index, x in enumerate((-1.25, 1.25)):
    cylinder(
        f"Rear upright peg {index + 1}",
        0.095,
        3.02,
        (x, 0.43, 1.73),
        wood,
        vertices=40,
        bevel=0.025
    )
    sphere(
        f"Rear peg rounded foot {index + 1}",
        0.101,
        (x, 0.43, 0.25),
        wood,
        scale=(1.0, 1.0, 0.85)
    )
    sphere(
        f"Rear peg finial {index + 1}",
        0.145,
        (x, 0.43, 3.285),
        wood_light,
        scale=(1.0, 1.0, 1.14)
    )
    torus(
        f"Rear peg collar {index + 1}",
        0.105,
        0.022,
        (x, 0.43, 3.12),
        (0.0, 0.0, 0.0),
        wood_dark,
        major_segments=40,
        minor_segments=8
    )
    torus(
        f"Rear peg lower turning {index + 1}",
        0.102,
        0.015,
        (x, 0.43, 0.47),
        (0.0, 0.0, 0.0),
        wood_dark,
        major_segments=40,
        minor_segments=8
    )

# Short front retaining pegs.
for index, x in enumerate((-1.18, 1.18)):
    cylinder(
        f"Front retaining peg {index + 1}",
        0.10,
        0.85,
        (x, -0.55, 0.62),
        wood,
        vertices=40,
        bevel=0.025
    )
    sphere(
        f"Front peg finial {index + 1}",
        0.135,
        (x, -0.55, 1.07),
        wood_light,
        scale=(1.0, 1.0, 1.08)
    )
    torus(
        f"Front peg collar {index + 1}",
        0.106,
        0.019,
        (x, -0.55, 0.93),
        (0.0, 0.0, 0.0),
        wood_dark,
        major_segments=40,
        minor_segments=8
    )

# Contact blocks supporting the plate's lower edge.
for index, x in enumerate((-0.92, 0.92)):
    rounded_box(
        f"Plate resting block {index + 1}",
        (x, -0.22, 0.39),
        (0.34, 0.34, 0.18),
        wood_light,
        bevel=0.06
    )

# Lathed ceramic plate with its local axis along Y.
plate_profile = [
    (0.000, 0.080),
    (0.260, 0.078),
    (0.600, 0.066),
    (0.970, 0.025),
    (1.250, -0.045),
    (1.445, -0.125),
    (1.565, -0.168),
    (1.635, -0.138),
    (1.670, -0.070),
    (1.670, 0.010),
    (1.630, 0.075),
    (1.520, 0.115),
    (1.300, 0.145),
    (1.020, 0.170),
    (0.750, 0.205),
    (0.610, 0.255),
    (0.570, 0.300),
    (0.470, 0.315),
    (0.370, 0.270),
    (0.350, 0.225),
    (0.230, 0.215),
    (0.000, 0.205)
]

plate_segments = 144
profile_count = len(plate_profile)
plate_vertices = []
plate_faces = []

for segment in range(plate_segments):
    angle = 2.0 * math.pi * segment / plate_segments
    cosine = math.cos(angle)
    sine = math.sin(angle)

    for radius, y_coordinate in plate_profile:
        plate_vertices.append(
            (radius * cosine, y_coordinate, radius * sine)
        )

for segment in range(plate_segments):
    next_segment = (segment + 1) % plate_segments

    for profile_index in range(profile_count - 1):
        a = segment * profile_count + profile_index
        b = next_segment * profile_count + profile_index
        c = next_segment * profile_count + profile_index + 1
        d = segment * profile_count + profile_index + 1
        plate_faces.append((a, b, c, d))

plate_mesh = bpy.data.meshes.new("Dish-shaped circular plate mesh")
plate_mesh.from_pydata(plate_vertices, [], plate_faces)
plate_mesh.update()

bm = bmesh.new()
bm.from_mesh(plate_mesh)
bmesh.ops.remove_doubles(
    bm,
    verts=list(bm.verts),
    dist=0.00001
)
bmesh.ops.recalc_face_normals(
    bm,
    faces=list(bm.faces)
)
bm.to_mesh(plate_mesh)
bm.free()
plate_mesh.update()

plate = bpy.data.objects.new(
    "Large dark purple circular plate",
    plate_mesh
)
bpy.context.collection.objects.link(plate)
plate.data.materials.append(purple)
smooth_object(plate)

# Lean the plate backward against the rear uprights.
plate_center = Vector((0.0, 0.0, 2.075))
plate_tilt = math.radians(-8.0)
plate.location = plate_center
plate.rotation_euler = (plate_tilt, 0.0, 0.0)

plate_bevel = plate.modifiers.new(
    name="Fine ceramic edge softening",
    type='BEVEL'
)
plate_bevel.width = 0.012
plate_bevel.segments = 2
plate_bevel.limit_method = 'ANGLE'

tilt_matrix = Matrix.Rotation(plate_tilt, 4, 'X')


def transformed_plate_point(local_point):
    return plate_center + tilt_matrix @ Vector(local_point)


# Raised front rim.
front_rim_location = transformed_plate_point((0.0, -0.145, 0.0))
torus(
    "Raised circular plate rim",
    1.505,
    0.035,
    front_rim_location,
    (math.radians(90.0) + plate_tilt, 0.0, 0.0),
    purple_edge,
    major_segments=144,
    minor_segments=14
)

# Inner dish transition bead.
inner_bead_location = transformed_plate_point((0.0, -0.043, 0.0))
torus(
    "Inner dish transition ring",
    1.205,
    0.018,
    inner_bead_location,
    (math.radians(90.0) + plate_tilt, 0.0, 0.0),
    purple_edge,
    major_segments=144,
    minor_segments=10
)

# Rear ceramic foot ring.
foot_location = transformed_plate_point((0.0, 0.268, 0.0))
torus(
    "Rear ceramic foot ring",
    0.505,
    0.055,
    foot_location,
    (math.radians(90.0) + plate_tilt, 0.0, 0.0),
    purple,
    major_segments=96,
    minor_segments=14
)

# Leave the central plate selected.
for obj in bpy.context.scene.objects:
    obj.select_set(False)

plate.select_set(True)
bpy.context.view_layer.objects.active = plate

# Use the renderer enum supported by the execution environment.
supported_engines = {
    item.identifier
    for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
}
if "BLENDER_EEVEE" in supported_engines:
    bpy.context.scene.render.engine = "BLENDER_EEVEE"
elif "BLENDER_EEVEE_NEXT" in supported_engines:
    bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"

bpy.context.scene.world.color = (0.045, 0.045, 0.045)