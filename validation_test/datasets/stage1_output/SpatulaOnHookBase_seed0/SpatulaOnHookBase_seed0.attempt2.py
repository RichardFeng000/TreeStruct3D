import bpy
import bmesh
import math
from mathutils import Vector

# Clear scene
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for mesh in list(bpy.data.meshes):
    bpy.data.meshes.remove(mesh)
for curve in list(bpy.data.curves):
    bpy.data.curves.remove(curve)
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat)

def deselect_all():
    for obj in bpy.context.selected_objects:
        obj.select_set(False)

def add_bevel(obj, width=0.003, segments=3):
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(30)

def create_backplate_with_frame():
    objects = []
    
    # Inner panel
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    panel = bpy.context.active_object
    panel.name = "BackplatePanel"
    panel.scale = (0.54, 0.01, 0.11)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    add_bevel(panel, 0.002, 2)
    objects.append(panel)
    
    # Frame params
    fy, fd, fw, fh, bw = 0.006, 0.022, 0.62, 0.16, 0.016
    
    frame_specs = [
        ("FrameTop", (0, fy, fh/2 - bw/2), (fw, fd, bw)),
        ("FrameBottom", (0, fy, -fh/2 + bw/2), (fw, fd, bw)),
        ("FrameLeft", (-fw/2 + bw/2, fy, 0), (bw, fd, fh - 2*bw)),
        ("FrameRight", (fw/2 - bw/2, fy, 0), (bw, fd, fh - 2*bw)),
    ]
    
    for name, loc, scale in frame_specs:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        add_bevel(obj, 0.003, 3)
        objects.append(obj)
    
    # Decorative screws at corners
    screw_pos = [
        (-fw/2 + bw/2, fy + fd/2 + 0.001, fh/2 - bw/2),
        (fw/2 - bw/2, fy + fd/2 + 0.001, fh/2 - bw/2),
        (-fw/2 + bw/2, fy + fd/2 + 0.001, -fh/2 + bw/2),
        (fw/2 - bw/2, fy + fd/2 + 0.001, -fh/2 + bw/2),
    ]
    
    for i, pos in enumerate(screw_pos):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.005, depth=0.003, location=pos, vertices=16)
        screw = bpy.context.active_object
        screw.name = f"Screw_{i}"
        screw.rotation_euler = (math.pi/2, 0, 0)
        objects.append(screw)
    
    # Decorative center medallion on top frame
    bpy.ops.mesh.primitive_cylinder_add(radius=0.008, depth=0.004, location=(0, fy + fd/2 + 0.001, fh/2 - bw/2), vertices=24)
    medallion = bpy.context.active_object
    medallion.name = "Medallion"
    medallion.rotation_euler = (math.pi/2, 0, 0)
    add_bevel(medallion, 0.001, 2)
    objects.append(medallion)
    
    return objects

def create_hook(x_pos, z_base=-0.058):
    curve_data = bpy.data.curves.new(name='HookCurve', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = 0.005
    curve_data.bevel_resolution = 8
    curve_data.use_fill_caps = True
    curve_data.resolution_u = 24
    
    spline = curve_data.splines.new('BEZIER')
    spline.bezier_points.add(4)
    
    pts = [
        ((x_pos, 0.01, z_base), 
         (x_pos, 0.01, z_base + 0.008), 
         (x_pos, 0.02, z_base - 0.002)),
        ((x_pos, 0.038, z_base - 0.018), 
         (x_pos, 0.03, z_base - 0.01), 
         (x_pos, 0.045, z_base - 0.025)),
        ((x_pos, 0.055, z_base - 0.038), 
         (x_pos, 0.055, z_base - 0.028), 
         (x_pos, 0.055, z_base - 0.048)),
        ((x_pos, 0.042, z_base - 0.026), 
         (x_pos, 0.055, z_base - 0.038), 
         (x_pos, 0.035, z_base - 0.018)),
        ((x_pos, 0.026, z_base - 0.01), 
         (x_pos, 0.032, z_base - 0.016), 
         (x_pos, 0.02, z_base - 0.004)),
    ]
    
    for i, (co, lh, rh) in enumerate(pts):
        bp = spline.bezier_points[i]
        bp.co = co
        bp.handle_left = lh
        bp.handle_right = rh
        bp.handle_left_type = 'FREE'
        bp.handle_right_type = 'FREE'
    
    hook_obj = bpy.data.objects.new('Hook', curve_data)
    bpy.context.collection.objects.link(hook_obj)
    return hook_obj

def create_spatula(x_pos, spatula_type=0, angle=0.06):
    objects = []
    
    rest_y = 0.05
    rest_z = -0.088
    handle_length = 0.30
    handle_radius = 0.011
    
    handle_top = Vector((x_pos, rest_y, rest_z))
    direction = Vector((0, math.sin(angle), -math.cos(angle)))
    handle_bottom = handle_top + direction * handle_length
    rot_x = math.atan2(direction.y, -direction.z)
    
    # Handle
    mid = (handle_top + handle_bottom) / 2
    bpy.ops.mesh.primitive_cylinder_add(radius=handle_radius, depth=handle_length, location=mid, vertices=24)
    handle = bpy.context.active_object
    handle.name = "SpatulaHandle"
    handle.rotation_euler = (rot_x, 0, 0)
    
    # Hanging hole on some spatulas
    if spatula_type % 2 == 0:
        hole_pos = handle_top - direction * 0.02
        bpy.ops.mesh.primitive_cylinder_add(radius=0.003, depth=handle_radius * 3, location=hole_pos, vertices=16)
        hang_hole = bpy.context.active_object
        hang_hole.rotation_euler = (0, math.pi/2, 0)
        
        deselect_all()
        handle.select_set(True)
        bpy.context.view_layer.objects.active = handle
        
        mod = handle.modifiers.new(name='HangHole', type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = hang_hole
        bpy.ops.object.modifier_apply(modifier='HangHole')
        bpy.data.objects.remove(hang_hole, do_unlink=True)
    
    add_bevel(handle, 0.0015, 3)
    objects.append(handle)
    
    # Handle top cap
    bpy.ops.mesh.primitive_uv_sphere_add(radius=handle_radius * 1.25, location=handle_top, segments=16, ring_count=10)
    cap = bpy.context.active_object
    cap.name = "HandleCap"
    objects.append(cap)
    
    # Grip rings on handle for detail
    for r_idx in range(3):
        ring_t = 0.25 + r_idx * 0.06
        ring_pos = handle_top + direction * (handle_length * ring_t)
        bpy.ops.mesh.primitive_torus_add(
            location=ring_pos,
            major_radius=handle_radius * 1.08,
            minor_radius=0.0015,
            major_segments=20,
            minor_segments=6
        )
        ring = bpy.context.active_object
        ring.name = f"GripRing_{r_idx}"
        ring.rotation_euler = (rot_x, 0, 0)
        objects.append(ring)
    
    # Neck/transition
    neck_pos = handle_bottom + direction * 0.008
    bpy.ops.mesh.primitive_cube_add(size=1, location=neck_pos)
    neck = bpy.context.active_object
    neck.name = "SpatulaNeck"
    neck.scale = (0.013, 0.005, 0.012)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    neck.rotation_euler = (rot_x, 0, 0)
    add_bevel(neck, 0.002, 2)
    objects.append(neck)
    
    # Head
    head_center = handle_bottom + direction * 0.038
    
    if spatula_type == 0:
        # Solid flat spatula
        bpy.ops.mesh.primitive_cube_add(size=1, location=head_center)
        head = bpy.context.active_object
        head.name = "SpatulaHead"
        head.scale = (0.07, 0.004, 0.05)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        head.rotation_euler = (rot_x, 0, 0)
        add_bevel(head, 0.002, 4)
        objects.append(head)
        
    elif spatula_type == 1:
        # Slotted spatula
        bpy.ops.mesh.primitive_cube_add(size=1, location=head_center)
        head = bpy.context.active_object
        head.name = "SpatulaHead"
        head.scale = (0.075, 0.004, 0.05)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        head.rotation_euler = (rot_x, 0, 0)
        
        for i in range(3):
            offset = (i - 1) * 0.022
            bpy.ops.mesh.primitive_cube_add(size=1, location=(head_center.x + offset, head_center.y, head_center.z))
            slot = bpy.context.active_object
            slot.scale = (0.005, 0.015, 0.035)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            
            deselect_all()
            head.select_set(True)
            bpy.context.view_layer.objects.active = head
            
            mod = head.modifiers.new(name=f'Slot_{i}', type='BOOLEAN')
            mod.operation = 'DIFFERENCE'
            mod.object = slot
            bpy.ops.object.modifier_apply(modifier=f'Slot_{i}')
            bpy.data.objects.remove(slot, do_unlink=True)
        
        add_bevel(head, 0.0015, 3)
        objects.append(head)
        
    elif spatula_type == 2:
        # Spatula with hole in head
        bpy.ops.mesh.primitive_cube_add(size=1, location=head_center)
        head = bpy.context.active_object
        head.name = "SpatulaHead"
        head.scale = (0.065, 0.004, 0.045)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        head.rotation_euler = (rot_x, 0, 0)
        
        hole_pos = head_center + direction * 0.005
        bpy.ops.mesh.primitive_cylinder_add(radius=0.009, depth=0.02, location=hole_pos, vertices=24)
        hole = bpy.context.active_object
        hole.rotation_euler = (math.pi/2 + rot_x, 0, 0)
        
        deselect_all()
        head.select_set(True)
        bpy.context.view_layer.objects.active = head
        
        mod = head.modifiers.new(name='Hole', type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = hole
        bpy.ops.object.modifier_apply(modifier='Hole')
        bpy.data.objects.remove(hole, do_unlink=True)
        
        add_bevel(head, 0.0015, 3)
        objects.append(head)
    
    elif spatula_type == 3:
        # Tapered spatula head (wider at bottom)
        bpy.ops.mesh.primitive_cube_add(size=1, location=head_center)
        head = bpy.context.active_object
        head.name = "SpatulaHead"
        head.scale = (0.06, 0.004, 0.05)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        bm = bmesh.new()
        bm.from_mesh(head.data)
        bm.verts.ensure_lookup_table()
        for v in bm.verts:
            if v.co.z < 0:
                v.co.x *= 1.25
        bm.to_mesh(head.data)
        bm.free()
        
        head.rotation_euler = (rot_x, 0, 0)
        add_bevel(head, 0.002, 4)
        objects.append(head)
    
    return objects

# Build the scene
backplate_objects = create_backplate_with_frame()

num_hooks = 4
hook_spacing = 0.13
hook_start_x = -(num_hooks - 1) * hook_spacing / 2
angles = [0.035, 0.055, 0.042, 0.068]

# Create hooks and spatulas
hooks = []
spatulas = []

for i in range(num_hooks):
    x = hook_start_x + i * hook_spacing
    hook = create_hook(x)
    hooks.append(hook)
    spatula_type = i % 4
    spatula_objects = create_spatula(x, spatula_type=spatula_type, angle=angles[i])
    spatulas.extend(spatula_objects)
    
    # Parent spatula to hook
    for obj in spatula_objects:
        obj.parent = hook

# Move hooks to attach to bottom frame
for hook in hooks:
    hook.location.y += 0.01  # align with bottom frame edge

# Set camera and lighting for visibility
bpy.ops.object.camera_add(location=(0.8, -0.5, 0.3), rotation=(1.2, 0.3, 2.8))
cam = bpy.context.active_object
cam.data.lens = 50
bpy.context.scene.camera = cam

# Add a simple light
bpy.ops.object.light_add(type='SUN', location=(0, -1, 1))
light = bpy.context.active_object
light.data.energy = 5.0

# Ensure all objects are visible and selected for render
for obj in bpy.data.objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = bpy.data.objects[0]

# Add materials for contrast
mat_dark = bpy.data.materials.new(name="DarkFrame")
mat_dark.use_nodes = True
mat_dark.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.1, 0.1, 0.1, 1)
mat_metal = bpy.data.materials.new(name="MetalHook")
mat_metal.use_nodes = True
mat_metal.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.7, 0.7, 0.7, 1)
mat_metal.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0
mat_metal.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.2

for obj in backplate_objects:
    if "Frame" in obj.name or "Screw" in obj.name or "Medallion" in obj.name:
        obj.data.materials.append(mat_dark)
    else:
        obj.data.materials.append(mat_metal)

for obj in bpy.data.objects:
    if "Hook" in obj.name:
        obj.data.materials.append(mat_metal)
    elif "Spatula" in obj.name:
        obj.data.materials.append(mat_metal)