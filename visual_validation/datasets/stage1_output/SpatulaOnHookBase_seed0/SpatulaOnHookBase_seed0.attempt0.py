import bpy
import bmesh
import math
from mathutils import Vector

# ============ CLEAR SCENE ============
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for coll in [bpy.data.meshes, bpy.data.materials, bpy.data.curves,
             bpy.data.lights, bpy.data.cameras]:
    for b in list(coll):
        coll.remove(b)
bpy.context.scene.cursor.location = (0, 0, 0)

# ============ CONSTANTS ============
PANEL_W = 0.60
PANEL_H = 0.16
PANEL_D = 0.018
FRAME_W = 0.030
FRAME_D = 0.036
Y_FRONT = PANEL_D / 2

# ============ MATERIALS ============
def make_mat(name, color, roughness=0.6, metallic=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return mat

mat_frame = make_mat("DarkFrame", (0.05, 0.04, 0.035), 0.4)
mat_panel = make_mat("Panel", (0.50, 0.38, 0.25), 0.65)
mat_hook = make_mat("Hook", (0.18, 0.18, 0.20), 0.25, 0.85)
mat_wood = make_mat("HandleWood", (0.42, 0.28, 0.16), 0.55)
mat_dark = make_mat("HandleDark", (0.12, 0.10, 0.09), 0.40)
mat_red = make_mat("HandleRed", (0.60, 0.12, 0.08), 0.35)
mat_metal = make_mat("Metal", (0.82, 0.82, 0.85), 0.15, 0.90)
mat_sil_red = make_mat("SiliconeRed", (0.75, 0.12, 0.08), 0.50)
mat_sil_black = make_mat("SiliconeBlack", (0.08, 0.08, 0.08), 0.50)

def set_mat(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

def add_bevel(obj, width=0.003, segments=2):
    m = obj.modifiers.new("Bevel", 'BEVEL')
    m.width = width
    m.segments = segments

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def apply_all_modifiers(obj):
    activate(obj)
    for mod in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception:
            obj.modifiers.remove(mod)

# ============ BACKPLATE ============
def create_backplate():
    parts = []

    # Inner panel
    bpy.ops.mesh.primitive_cube_add(size=1)
    panel = bpy.context.active_object
    panel.name = "Panel"
    panel.scale = (PANEL_W - 2 * FRAME_W, PANEL_D, PANEL_H - 2 * FRAME_W)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    set_mat(panel, mat_panel)
    add_bevel(panel, 0.002, 2)
    parts.append(panel)

    # Frame border (4 pieces)
    frame_specs = [
        ((PANEL_W, FRAME_D, FRAME_W), (0, 0, PANEL_H / 2 - FRAME_W / 2)),
        ((PANEL_W, FRAME_D, FRAME_W), (0, 0, -PANEL_H / 2 + FRAME_W / 2)),
        ((FRAME_W, FRAME_D, PANEL_H - 2 * FRAME_W), (-PANEL_W / 2 + FRAME_W / 2, 0, 0)),
        ((FRAME_W, FRAME_D, PANEL_H - 2 * FRAME_W), (PANEL_W / 2 - FRAME_W / 2, 0, 0)),
    ]
    for idx, (scl, loc) in enumerate(frame_specs):
        bpy.ops.mesh.primitive_cube_add(size=1)
        obj = bpy.context.active_object
        obj.name = f"Frame_{idx}"
        obj.scale = scl
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.location = loc
        set_mat(obj, mat_frame)
        add_bevel(obj, 0.003, 2)
        parts.append(obj)

    # Decorative screws at corners
    screw_positions = [
        (-PANEL_W / 2 + FRAME_W / 2, PANEL_H / 2 - FRAME_W / 2),
        (PANEL_W / 2 - FRAME_W / 2, PANEL_H / 2 - FRAME_W / 2),
        (-PANEL_W / 2 + FRAME_W / 2, -PANEL_H / 2 + FRAME_W / 2),
        (PANEL_W / 2 - FRAME_W / 2, -PANEL_H / 2 + FRAME_W / 2),
    ]
    for idx, (sx, sz) in enumerate(screw_positions):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.005, depth=0.005, vertices=16,
            location=(sx, FRAME_D / 2 + 0.001, sz),
            rotation=(math.pi / 2, 0, 0)
        )
        screw = bpy.context.active_object
        screw.name = f"Screw_{idx}"
        set_mat(screw, mat_metal)
        parts.append(screw)

    return parts

# ============ HOOK ============
def create_hook(x_pos):
    z_attach = -PANEL_H / 2 + FRAME_W * 0.5

    curve_data = bpy.data.curves.new(name="HookCurve", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = 0.005
    curve_data.bevel_resolution = 5
    curve_data.resolution_u = 24
    curve_data.use_fill_caps = True

    spline = curve_data.splines.new(type='BEZIER')

    pts = [
        Vector((x_pos, Y_FRONT, z_attach)),
        Vector((x_pos, Y_FRONT, z_attach - 0.022)),
        Vector((x_pos, Y_FRONT + 0.012, z_attach - 0.040)),
        Vector((x_pos, Y_FRONT + 0.032, z_attach - 0.038)),
        Vector((x_pos, Y_FRONT + 0.044, z_attach - 0.022)),
    ]

    spline.bezier_points.add(len(pts) - 1)
    for i, pt in enumerate(pts):
        bp = spline.bezier_points[i]
        bp.co = pt
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'

    hook_obj = bpy.data.objects.new("Hook", curve_data)
    bpy.context.collection.objects.link(hook_obj)

    activate(hook_obj)
    bpy.ops.object.convert(target='MESH')
    set_mat(hook_obj, mat_hook)

    return hook_obj

# ============ SPATULA COMPONENTS ============
def create_handle(length, radius, mat, taper_top=1.2, taper_bot=0.85, oval=1.0):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=length, vertices=24,
        location=(0, 0, -length / 2)
    )
    handle = bpy.context.active_object
    handle.name = "Handle"

    bm = bmesh.new()
    bm.from_mesh(handle.data)
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        t = (v.co.z + length / 2) / length
        ergo = 1.0 + 0.08 * math.sin(math.pi * t)
        s = (taper_bot + (taper_top - taper_bot) * t) * ergo
        v.co.x *= s
        v.co.y *= s * oval
    bm.to_mesh(handle.data)
    bm.free()

    add_bevel(handle, 0.003, 3)
    set_mat(handle, mat)
    return handle

def create_ferrule(z_pos, radius, length=0.015):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=length, vertices=24,
        location=(0, 0, z_pos - length / 2)
    )
    f = bpy.context.active_object
    f.name = "Ferrule"
    set_mat(f, mat_metal)
    return f

def create_blade_metal(z_pos, length=0.11, width=0.075, slotted=False):
    bpy.ops.mesh.primitive_cube_add(size=1)
    blade = bpy.context.active_object
    blade.name = "Blade"
    blade.scale = (width, 0.003, length)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    blade.location = (0, 0, z_pos - length / 2)

    bm = bmesh.new()
    bm.from_mesh(blade.data)
    for v in bm.verts:
        if v.co.z < -length / 2 + 0.02:
            t = max(0.0, min(1.0, (-length / 2 - v.co.z) / 0.02))
            v.co.x *= (1.0 - 0.35 * t)
        if v.co.z > length / 2 - 0.008:
            v.co.x *= 0.88
    bm.to_mesh(blade.data)
    bm.free()

    if slotted:
        for i in range(3):
            bpy.ops.mesh.primitive_cube_add(size=1)
            slot = bpy.context.active_object
            slot.scale = (0.006, 0.012, 0.035)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            slot.location = ((i - 1) * 0.018, 0, z_pos - length * 0.6)

            mod = blade.modifiers.new(f"Slot{i}", 'BOOLEAN')
            mod.operation = 'DIFFERENCE'
            mod.object = slot

            activate(blade)
            bpy.ops.object.modifier_apply(modifier=f"Slot{i}")
            bpy.data.objects.remove(slot, do_unlink=True)

    add_bevel(blade, 0.0025, 3)
    set_mat(blade, mat_metal)
    return blade

def create_blade_silicone(z_pos, length=0.10, width=0.065, mat=mat_sil_red):
    bpy.ops.mesh.primitive_cube_add(size=1)
    blade = bpy.context.active_object
    blade.name = "Blade"
    blade.scale = (width, 0.006, length)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    blade.location = (0, 0, z_pos - length / 2)

    bm = bmesh.new()
    bm.from_mesh(blade.data)
    for v in bm.verts:
        if v.co.z < -length / 2 + 0.025:
            t = max(0.0, min(1.0, (-length / 2 - v.co.z) / 0.025))
            v.co.x *= (1.0 - 0.4 * t)
            v.co.y *= (1.0 + 0.5 * t)
    bm.to_mesh(blade.data)
    bm.free()

    sub = blade.modifiers.new("Subsurf", 'SUBSURF')
    sub.levels = 1
    sub.render_levels = 2

    add_bevel(blade, 0.005, 4)
    set_mat(blade, mat)
    return blade

# ============ SPATULA ASSEMBLY ============
def create_spatula(style=0):
    parts = []

    if style == 0:
        # Wooden handle + metal turner blade
        parts.append(create_handle(0.22, 0.013, mat_wood, 1.25, 0.80))
        parts.append(create_ferrule(-0.22, 0.011, 0.018))
        parts.append(create_blade_metal(-0.238, 0.11, 0.075))
    elif style == 1:
        # Dark handle + red silicone blade
        parts.append(create_handle(0.20, 0.012, mat_dark, 1.15, 0.85, 0.75))
        parts.append(create_ferrule(-0.20, 0.010, 0.012))
        parts.append(create_blade_silicone(-0.212, 0.10, 0.065, mat_sil_red))
    elif style == 2:
        # Red handle + slotted metal blade
        parts.append(create_handle(0.21, 0.012, mat_red, 1.20, 0.82))
        parts.append(create_ferrule(-0.21, 0.010, 0.015))
        parts.append(create_blade_metal(-0.225, 0.10, 0.07, slotted=True))
    elif style == 3:
        # Wooden handle + black silicone blade
        parts.append(create_handle(0.21, 0.013, mat_wood, 1.22, 0.82))
        parts.append(create_ferrule(-0.21, 0.011, 0.015))
        parts.append(create_blade_silicone(-0.225, 0.09, 0.06, mat_sil_black))

    # Apply modifiers on all parts before joining
    for p in parts:
        apply_all_modifiers(p)

    # Join all parts into single spatula object
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()

    # Apply transform so origin is at top of handle (z=0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    return parts[0]

# ============ MAIN ASSEMBLY ============

# Create backplate with frame and screws
backplate_parts = create_backplate()

# Create hooks and spatulas
num_hooks = 4
z_attach = -PANEL_H / 2 + FRAME_W * 0.5
margin = 0.07
spacing = (PANEL_W - 2 * margin) / (num_hooks - 1)
x_start = -PANEL_W / 2 + margin

styles = [0, 1, 2, 3]

for i in range(num_hooks):
    x = x_start + i * spacing

    # Create curved hook
    hook = create_hook(x)

    # Create spatula
    spatula = create_spatula(style=styles[i])
    spatula.name = f"Spatula_{i}"

    # Position spatula hanging from hook
    # Hook curve bottom is at approximately (x, Y_FRONT+0.022, z_attach-0.040)
    catch_y = Y_FRONT + 0.022
    catch_z = z_attach - 0.040
    catch_offset = 0.035  # hook catches handle 3.5cm below top

    spatula.location = (x, catch_y, catch_z + catch_offset)

    # Slight tilt for natural hanging appearance
    tilt_x = math.radians(3) + (i % 2) * math.radians(2)
    tilt_y = ((i + 1) % 3 - 1) * math.radians(3)
    spatula.rotation_euler = (tilt_x, tilt_y, 0)

# ============ CLEANUP ============
for block in list(bpy.data.meshes):
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in list(bpy.data.curves):
    if block.users == 0:
        bpy.data.curves.remove(block)