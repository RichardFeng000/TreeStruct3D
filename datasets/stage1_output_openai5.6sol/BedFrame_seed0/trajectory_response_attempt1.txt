import bpy
import math
from mathutils import Vector

# Clear the default scene.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    if datablocks != bpy.data.materials:
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)

# Materials.
def make_material(name, color, metallic=0.0, roughness=0.45):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat

wood = make_material("Warm Walnut", (0.25, 0.075, 0.028), 0.0, 0.34)
wood_dark = make_material("Dark Recessed Walnut", (0.105, 0.024, 0.009), 0.0, 0.40)
wood_light = make_material("Raised Walnut Molding", (0.39, 0.135, 0.045), 0.0, 0.30)
slat_mat = make_material("Slat Wood", (0.48, 0.24, 0.105), 0.0, 0.48)
metal = make_material("Antique Brass Accents", (0.34, 0.17, 0.045), 0.78, 0.24)

def assign_material(obj, mat):
    obj.data.materials.append(mat)

def apply_bevel(obj, amount=0.04, segments=3):
    if amount <= 0:
        return
    bevel = obj.modifiers.new("Softened edges", 'BEVEL')
    bevel.width = amount
    bevel.segments = segments
    bevel.limit_method = 'ANGLE'
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    obj.select_set(False)

def box(name, location, dimensions, material, bevel=0.035, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign_material(obj, material)
    apply_bevel(obj, bevel, 3)
    return obj

def tapered_box(name, x, y, z_bottom, z_top, bottom_size, top_size, material, bevel=0.025):
    hb = bottom_size / 2.0
    ht = top_size / 2.0
    verts = [
        (x-hb, y-hb, z_bottom), (x+hb, y-hb, z_bottom),
        (x+hb, y+hb, z_bottom), (x-hb, y+hb, z_bottom),
        (x-ht, y-ht, z_top), (x+ht, y-ht, z_top),
        (x+ht, y+ht, z_top), (x-ht, y+ht, z_top)
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7),
        (0, 1, 5, 4), (1, 2, 6, 5),
        (2, 3, 7, 6), (3, 0, 4, 7)
    ]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    assign_material(obj, material)
    apply_bevel(obj, bevel, 2)
    return obj

def cylinder(name, location, radius, depth, material, vertices=32, rotation=(0, 0, 0), bevel=0.015):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign_material(obj, material)
    if bevel:
        apply_bevel(obj, bevel, 2)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

def sphere(name, location, scale, material, segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign_material(obj, material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

def xz_frame(prefix, cx, cz, y, width, height, bar, depth, material, bevel=0.025):
    box(prefix + "_Top", (cx, y, cz + height/2 - bar/2),
        (width, depth, bar), material, bevel)
    box(prefix + "_Bottom", (cx, y, cz - height/2 + bar/2),
        (width, depth, bar), material, bevel)
    box(prefix + "_Left", (cx - width/2 + bar/2, y, cz),
        (bar, depth, height - 2*bar), material, bevel)
    box(prefix + "_Right", (cx + width/2 - bar/2, y, cz),
        (bar, depth, height - 2*bar), material, bevel)

def extruded_xz_shape(name, points, y_center, depth, material, bevel=0.035):
    front_y = y_center - depth / 2
    back_y = y_center + depth / 2
    n = len(points)
    verts = [(x, front_y, z) for x, z in points] + [(x, back_y, z) for x, z in points]
    faces = []
    faces.append(tuple(reversed(range(n))))
    faces.append(tuple(range(n, 2*n)))
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n+j, n+i))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    assign_material(obj, material)
    apply_bevel(obj, bevel, 3)
    return obj

# Main bed proportions.
bed_half_width = 1.80
head_y = 3.10
foot_y = -3.10
rail_z = 1.32
slat_z = 1.60

# Four tapered legs with square antique-brass toe caps and collars.
leg_positions = [
    (-1.78, head_y), (1.78, head_y),
    (-1.78, foot_y), (1.78, foot_y)
]
for index, (x, y) in enumerate(leg_positions):
    tapered_box("BrassToe_%02d" % index, x, y, 0.02, 0.29, 0.255, 0.285, metal, 0.018)
    tapered_box("TaperedWoodLeg_%02d" % index, x, y, 0.27, 1.55, 0.285, 0.405, wood, 0.032)
    box("BrassCollar_%02d" % index, (x, y, 0.43), (0.315, 0.315, 0.095), metal, 0.018)

# Side rails.
box("LeftSideRail", (-1.77, 0.0, rail_z), (0.28, 5.85, 0.58), wood, 0.055)
box("RightSideRail", (1.77, 0.0, rail_z), (0.28, 5.85, 0.58), wood, 0.055)

# Raised decorative bands on the visible exterior of both side rails.
box("LeftRailUpperMolding", (-1.925, 0.0, 1.49), (0.055, 5.55, 0.105), wood_light, 0.025)
box("LeftRailLowerMolding", (-1.925, 0.0, 1.16), (0.055, 5.55, 0.085), wood_light, 0.022)
box("RightRailUpperMolding", (1.925, 0.0, 1.49), (0.055, 5.55, 0.105), wood_light, 0.025)
box("RightRailLowerMolding", (1.925, 0.0, 1.16), (0.055, 5.55, 0.085), wood_light, 0.022)

# Inner ledges supporting the slats.
box("LeftSlatLedge", (-1.54, 0.0, 1.49), (0.22, 5.55, 0.18), wood_dark, 0.025)
box("RightSlatLedge", (1.54, 0.0, 1.49), (0.22, 5.55, 0.18), wood_dark, 0.025)

# Center support beam and two discreet support blocks.
box("CenterSupportBeam", (0.0, 0.0, 1.43), (0.20, 5.55, 0.26), wood_dark, 0.035)
box("CenterSupportBlockA", (0.0, -1.65, 0.93), (0.30, 0.30, 0.92), wood_dark, 0.025)
box("CenterSupportBlockB", (0.0, 1.65, 0.93), (0.30, 0.30, 0.92), wood_dark, 0.025)

# Open slatted sleeping surface.
slat_count = 15
for i in range(slat_count):
    y = -2.63 + i * (5.26 / (slat_count - 1))
    slat = box("SupportSlat_%02d" % i, (0.0, y, slat_z),
               (3.25, 0.19, 0.14), slat_mat, 0.035)
    # Small dark end blocks suggest the slats nesting into the side ledges.
    box("SlatEndL_%02d" % i, (-1.61, y, 1.56), (0.13, 0.205, 0.13), wood_dark, 0.02)
    box("SlatEndR_%02d" % i, (1.61, y, 1.56), (0.13, 0.205, 0.13), wood_dark, 0.02)

# Headboard tall corner posts.
for side, x in (("L", -1.80), ("R", 1.80)):
    box("HeadPost_" + side, (x, head_y, 3.22), (0.40, 0.42, 3.58), wood, 0.065)
    box("HeadPostInset_" + side, (x, head_y - 0.225, 3.22),
        (0.22, 0.075, 2.92), wood_light, 0.028)
    box("HeadPostCapital_" + side, (x, head_y, 4.94),
        (0.52, 0.52, 0.24), wood_light, 0.055)
    cylinder("HeadFinialNeck_" + side, (x, head_y, 5.14), 0.16, 0.22, wood_light, 32, bevel=0.02)
    sphere("HeadFinial_" + side, (x, head_y, 5.35), (0.23, 0.23, 0.28), wood, 32, 16)
    sphere("HeadFinialTip_" + side, (x, head_y, 5.62), (0.085, 0.085, 0.12), wood_light, 24, 12)

# Headboard panel backing and structural rails.
box("HeadboardLowerRail", (0.0, head_y, 1.92), (3.28, 0.34, 0.42), wood, 0.065)
box("HeadboardPanelBack", (0.0, head_y + 0.015, 3.34), (3.20, 0.22, 2.55), wood_dark, 0.075)
box("HeadboardUpperRail", (0.0, head_y, 4.60), (3.30, 0.38, 0.38), wood, 0.075)

# Decorative arched crown.
crown_points = [
    (-1.62, 4.55), (-1.42, 4.77), (-1.06, 4.86), (-0.72, 4.95),
    (-0.35, 5.18), (0.0, 5.32), (0.35, 5.18), (0.72, 4.95),
    (1.06, 4.86), (1.42, 4.77), (1.62, 4.55),
    (1.48, 4.38), (-1.48, 4.38)
]
extruded_xz_shape("ArchedHeadboardCrown", crown_points, head_y - 0.005, 0.36, wood, 0.055)

# Crown face molding and center crest.
molding_points = [
    (-1.39, 4.58), (-1.10, 4.68), (-0.70, 4.79), (-0.34, 5.00),
    (0.0, 5.13), (0.34, 5.00), (0.70, 4.79), (1.10, 4.68),
    (1.39, 4.58), (1.25, 4.48), (-1.25, 4.48)
]
extruded_xz_shape("CrownRaisedMolding", molding_points, head_y - 0.215, 0.075, wood_light, 0.025)
sphere("CentralCrownMedallion", (0.0, head_y - 0.277, 4.98),
       (0.30, 0.055, 0.23), wood_light, 32, 16)
for sx in (-1, 1):
    ornament = box("CrownLeaf_%s" % ("L" if sx < 0 else "R"),
                   (0.36*sx, head_y - 0.275, 4.92),
                   (0.34, 0.07, 0.12), wood_light, 0.035,
                   rotation=(0.0, sx * math.radians(28), 0.0))

# Three recessed, molded headboard panels.
panel_centers = (-1.05, 0.0, 1.05)
for i, cx in enumerate(panel_centers):
    panel_width = 0.86 if i != 1 else 0.94
    box("HeadInsetPanel_%d" % i, (cx, head_y - 0.145, 3.35),
        (panel_width, 0.115, 1.92), wood, 0.075)
    xz_frame("HeadPanelFrame_%d" % i, cx, 3.35, head_y - 0.235,
             panel_width + 0.13, 2.10, 0.105, 0.115, wood_light, 0.026)
    xz_frame("HeadPanelInner_%d" % i, cx, 3.35, head_y - 0.302,
             panel_width - 0.16, 1.69, 0.055, 0.07, wood_light, 0.018)
    sphere("HeadPanelMedallion_%d" % i, (cx, head_y - 0.356, 3.36),
           (0.245 if i != 1 else 0.29, 0.052, 0.39), wood_light, 28, 14)
    # Small raised beads above and below each oval medallion.
    sphere("HeadPanelBeadTop_%d" % i, (cx, head_y - 0.355, 3.88),
           (0.075, 0.04, 0.075), wood_light, 20, 10)
    sphere("HeadPanelBeadBottom_%d" % i, (cx, head_y - 0.355, 2.84),
           (0.075, 0.04, 0.075), wood_light, 20, 10)

# Vertical pilasters separating headboard panels.
for i, x in enumerate((-0.54, 0.54)):
    box("HeadPilaster_%d" % i, (x, head_y - 0.245, 3.35),
        (0.115, 0.13, 2.25), wood_light, 0.035)
    box("HeadPilasterCap_%d" % i, (x, head_y - 0.255, 4.48),
        (0.22, 0.15, 0.14), wood_light, 0.035)
    box("HeadPilasterBase_%d" % i, (x, head_y - 0.255, 2.22),
        (0.22, 0.15, 0.14), wood_light, 0.035)

# Short footboard posts.
for side, x in (("L", -1.80), ("R", 1.80)):
    box("FootPost_" + side, (x, foot_y, 1.93), (0.40, 0.42, 1.54), wood, 0.06)
    box("FootPostInset_" + side, (x, foot_y - 0.225, 1.94),
        (0.22, 0.075, 1.08), wood_light, 0.025)
    box("FootPostCapital_" + side, (x, foot_y, 2.72),
        (0.50, 0.50, 0.20), wood_light, 0.05)
    sphere("FootFinial_" + side, (x, foot_y, 2.91),
           (0.19, 0.19, 0.23), wood, 28, 14)
    sphere("FootFinialTip_" + side, (x, foot_y, 3.11),
           (0.07, 0.07, 0.10), wood_light, 20, 10)

# Footboard structure.
box("FootboardPanelBack", (0.0, foot_y, 1.96), (3.28, 0.27, 1.30), wood_dark, 0.07)
box("FootboardLowerRail", (0.0, foot_y, 1.35), (3.34, 0.36, 0.34), wood, 0.06)
box("FootboardUpperRail", (0.0, foot_y, 2.61), (3.34, 0.38, 0.32), wood, 0.065)

# Gentle central rise on the footboard top.
foot_crown = [
    (-1.57, 2.58), (-1.05, 2.64), (-0.52, 2.69), (0.0, 2.78),
    (0.52, 2.69), (1.05, 2.64), (1.57, 2.58),
    (1.48, 2.48), (-1.48, 2.48)
]
extruded_xz_shape("FootboardCrownedTop", foot_crown, foot_y, 0.36, wood, 0.045)

# Three molded panels on the outward face of the footboard.
for i, cx in enumerate(panel_centers):
    panel_width = 0.86 if i != 1 else 0.94
    box("FootInsetPanel_%d" % i, (cx, foot_y - 0.175, 1.98),
        (panel_width, 0.10, 0.82), wood, 0.055)
    xz_frame("FootPanelFrame_%d" % i, cx, 1.98, foot_y - 0.255,
             panel_width + 0.12, 0.98, 0.085, 0.10, wood_light, 0.023)
    xz_frame("FootPanelInner_%d" % i, cx, 1.98, foot_y - 0.315,
             panel_width - 0.15, 0.68, 0.045, 0.06, wood_light, 0.014)
    sphere("FootPanelMedallion_%d" % i, (cx, foot_y - 0.36, 1.98),
           (0.19, 0.045, 0.24), wood_light, 24, 12)

# Brass corner ornaments on the footboard and headboard lower junctions.
for x in (-1.80, 1.80):
    box("HeadCornerAccent_%s" % ("L" if x < 0 else "R"),
        (x, head_y - 0.225, 1.62), (0.24, 0.07, 0.12), metal, 0.025)
    box("FootCornerAccent_%s" % ("L" if x < 0 else "R"),
        (x, foot_y - 0.225, 1.54), (0.24, 0.07, 0.12), metal, 0.025)

# Ensure all geometry is selectable and no non-geometry scene objects remain.
for obj in list(bpy.data.objects):
    if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}:
        bpy.data.objects.remove(obj, do_unlink=True)

bpy.ops.object.select_all(action='DESELECT')
mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
if mesh_objects:
    bpy.context.view_layer.objects.active = mesh_objects[0]
    mesh_objects[0].select_set(True)