import bpy
import bmesh
import math
from mathutils import Vector, Quaternion

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, glossy=0.3, mottled=False):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = glossy

    if mottled:
        # Create a simple noise-based mottled effect for the carapace
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 10.0
        noise.inputs['Detail'].default_value = 2.0
        
        color_ramp = nodes.new('ShaderNodeValToRGB')
        color_ramp.color_ramp.elements[0].color = (0.1, 0.02, 0.01, 1) # Darker red-brown
        color_ramp.color_ramp.elements[1].color = color
        
        links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
        links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
        
    return mat

def create_segment(name, length, radius_start, radius_end, start_pos, direction, material):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    
    segs = 12
    v_start = []
    for i in range(segs):
        a = (2 * math.pi * i) / segs
        v_start.append(bm.verts.new(Vector((math.cos(a) * radius_start, math.sin(a) * radius_start, 0))))
    
    v_end = []
    for i in range(segs):
        a = (2 * math.pi * i) / segs
        v_end.append(bm.verts.new(Vector((math.cos(a) * radius_end, math.sin(a) * radius_end, length))))
    
    for i in range(segs):
        n = (i + 1) % segs
        bm.faces.new((v_start[i], v_start[n], v_end[n], v_end[i]))
    
    bm.faces.new(v_start)
    bm.faces.new(v_end[::-1])
    
    bm.to_mesh(mesh)
    bm.free()
    
    # Align local Z to the target direction vector
    rot_quat = Vector((0, 0, 1)).rotation_difference(direction)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = rot_quat
    obj.location = start_pos
    obj.active_material = material
    return obj

def create_pincer_tip(name, length, radius, start_pos, direction, material):
    # Create a more tapered and curved pincer tip
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    
    segs = 12
    # Tapered cone shape
    v_start = []
    for i in range(segs):
        a = (2 * math.pi * i) / segs
        v_start.append(bm.verts.new(Vector((math.cos(a) * radius, math.sin(a) * radius, 0))))
    
    # Pointed tip
    v_end = [bm.verts.new(Vector((0, 0, length)))]
    
    for i in range(segs):
        n = (i + 1) % segs
        bm.faces.new((v_start[i], v_start[n], v_end[0]))
    
    bm.faces.new(v_start)
    
    bm.to_mesh(mesh)
    bm.free()
    
    rot_quat = Vector((0, 0, 1)).rotation_difference(direction)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = rot_quat
    obj.location = start_pos
    obj.active_material = material
    return obj

def build_crab():
    clear_scene()
    
    # Materials
    mat_shell = create_material("Shell", (0.3, 0.1, 0.05, 1), glossy=0.2, mottled=True)
    mat_legs = create_material("Legs", (0.6, 0.3, 0.1, 1))
    mat_claw_red = create_material("ClawRed", (0.7, 0.1, 0.1, 1))
    mat_claw_white = create_material("ClawWhite", (0.9, 0.9, 0.9, 1))
    mat_eye = create_material("Eye", (0.9, 0.9, 0.9, 1))

    # Carapace: Low profile and rounded
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0))
    carapace = bpy.context.active_object
    carapace.scale = (1.3, 1.0, 0.3) # Wide and flat
    bpy.ops.object.transform_apply(scale=True)
    
    # Organic shaping via BMesh
    bm = bmesh.new()
    bm.from_mesh(carapace.data)
    for v in bm.verts:
        if v.co.y > 0: # Front taper
            v.co.x *= (1.0 - 0.2 * v.co.y)
        if v.co.z < 0: # Flatten bottom more aggressively
            v.co.z = -0.3
    bm.to_mesh(carapace.data)
    bm.free()
    
    bpy.context.view_layer.objects.active = carapace
    bpy.ops.object.modifier_add(type='SUBSURF')
    carapace.modifiers["Subdivision"].levels = 2
    bpy.ops.object.shade_smooth()
    carapace.data.materials.append(mat_shell)

    # Eye stalks - thicker and positioned at the front
    for side in [-1, 1]:
        pos = Vector((0.3 * side, 0.85, 0.2))
        dir = Vector((0.1 * side, 0.2, 0.4)).normalized()
        create_segment("EyeStalk", 0.25, 0.06, 0.06, pos, dir, mat_eye)
        # Eyeballs
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=pos + dir * 0.25)
        bpy.context.active_object.data.materials.append(mat_eye)

    # Walking Legs: Shifted inwards to ensure connection
    leg_coords = [
        (0.8, 0.4), (1.1, 0.0), (1.0, -0.4), (0.7, -0.8), # Right
        (-0.8, 0.4), (-1.1, 0.0), (-1.0, -0.4), (-0.7, -0.8) # Left
    ]
    
    for i, (lx, ly) in enumerate(leg_coords):
        side = 1 if lx > 0 else -1
        start_pos = Vector((lx * 0.8, ly * 0.8, 0))
        # Segment 1: Outward and slightly down
        d1 = Vector((side * 0.6, 0.2, -0.2)).normalized()
        s1 = create_segment(f"Leg_{i}_1", 0.4, 0.12, 0.08, start_pos, d1, mat_legs)
        # Segment 2: Bending outward
        e1 = start_pos + d1 * 0.4
        d2 = Vector((side * 0.7, -0.1, -0.3)).normalized()
        s2 = create_segment(f"Leg_{i}_2", 0.5, 0.08, 0.05, e1, d2, mat_legs)
        # Segment 3: Downward to ground
        e2 = e1 + d2 * 0.5
        d3 = Vector((side * 0.2, -0.4, -0.7)).normalized()
        s3 = create_segment(f"Leg_{i}_3", 0.6, 0.05, 0.03, e2, d3, mat_legs)

    # Chelipeds (Claws)
    claw_configs = [
        {"side": 1, "scale": 1.7, "dominant": True},  # Right: dominant
        {"side": -1, "scale": 1.0, "dominant": False} # Left
    ]
    
    for cfg in claw_configs:
        s = cfg["side"]
        sc = cfg["scale"]
        start_pos = Vector((0.6 * s, 0.5, 0))
        
        # Arm Segment 1
        d1 = Vector((s * 0.6, 0.4, 0.3)).normalized()
        arm1 = create_segment("ClawArm1", 0.7 * sc, 0.2 * sc, 0.15 * sc, start_pos, d1, mat_claw_red)
        
        # Arm Segment 2
        e1 = start_pos + d1 * (0.7 * sc)
        d2 = Vector((s * 0.8, 0.4, -0.1)).normalized()
        arm2 = create_segment("ClawArm2", 0.6 * sc, 0.15 * sc, 0.15 * sc, e1, d2, mat_claw_red)
        
        # Pincer Tips (The "fingers")
        e2 = e1 + d2 * (0.6 * sc)
        
        # Fixed finger (Red)
        pdir1 = Vector((s * 1.1, 0.5, 0.1)).normalized()
        create_pincer_tip("FingerFixed", 0.6 * sc, 0.15 * sc, e2, pdir1, mat_claw_red)
        
        # Movable finger (White - slightly open)
        pdir2 = Vector((s * 0.9, 0.8, 0.4)).normalized()
        create_pincer_tip("FingerMovable", 0.5 * sc, 0.13 * sc, e2, pdir2, mat_claw_white)

if __name__ == "__main__":
    build_crab()
