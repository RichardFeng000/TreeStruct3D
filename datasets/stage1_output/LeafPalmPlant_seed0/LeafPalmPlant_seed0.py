import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_fan_palm():
    # Parameters
    stem_height = 6.0
    stem_radius_base = 0.12
    stem_radius_top = 0.08
    num_segments = 52
    segment_length_min = 4.0
    segment_length_max = 6.0
    segment_width_base = 0.22 # Slightly wider base for a more natural look
    segment_width_tip = 0.04
    fan_spread_angle = 175 * (math.pi / 180) # Broader fan
    
    # BMesh for the entire leaf assembly
    bm = bmesh.new()

    # --- Stem Construction ---
    segments_stem = 16
    rings_stem = 20
    
    verts_base = []
    for i in range(segments_stem):
        angle = (2 * math.pi * i) / segments_stem
        x = math.cos(angle) * stem_radius_base
        y = math.sin(angle) * stem_radius_base
        verts_base.append(bm.verts.new(Vector((x, y, 0))))

    verts_top = []
    for i in range(segments_stem):
        angle = (2 * math.pi * i) / segments_stem
        x = math.cos(angle) * stem_radius_top
        y = math.sin(angle) * stem_radius_top
        verts_top.append(bm.verts.new(Vector((x, y, stem_height))))

    for i in range(segments_stem):
        v1 = verts_base[i]
        v2 = verts_base[(i + 1) % segments_stem]
        v3 = verts_top[(i + 1) % segments_stem]
        v4 = verts_top[i]
        bm.faces.new((v1, v2, v3, v4))

    # --- Blade Construction (The Fan) ---
    center_point = Vector((0, 0, stem_height))
    
    start_angle = -fan_spread_angle / 2
    end_angle = fan_spread_angle / 2
    
    for i in range(num_segments):
        # Angle for this specific segment
        t_angle = (i / (num_segments - 1)) if num_segments > 1 else 0.5
        angle = start_angle + t_angle * (end_angle - start_angle)
        
        length = random.uniform(segment_length_min, segment_length_max)
        if i == 0 or i == num_segments - 1:
            length *= 0.85

        # Give each segment a slightly different droop factor to avoid the "umbrella" look
        droop_factor = random.uniform(0.6, 1.4)
        num_points = 12
        seg_verts_left = []
        seg_verts_right = []
        
        for p in range(num_points + 1):
            t = p / num_points # normalized distance [0, 1]
            
            dir_vec = Vector((math.cos(angle), math.sin(angle), 0))
            perp_vec = Vector((-dir_vec.y, dir_vec.x, 0))
            
            current_width = segment_width_base * (1.0 - t * 0.8)
            if current_width < segment_width_tip:
                current_width = segment_width_tip

            # New Z-curve logic: stays flatter near the base, droops more at tips
            # This creates a "fan" rather than a "dome"
            z_offset = -(t**2.5) * (1.5 * droop_factor)
            
            dist = t * length
            pos = center_point + dir_vec * dist
            pos.z += z_offset

            # Organic noise - jitter the path slightly
            if 0 < t < 1:
                noise_val = random.uniform(-0.1, 0.1)
                pos += perp_vec * noise_val * math.sin(t * math.pi)
                pos.z += random.uniform(-0.05, 0.05)

            v_l = bm.verts.new(pos + perp_vec * (current_width / 2))
            v_r = bm.verts.new(pos - perp_vec * (current_width / 2))
            seg_verts_left.append(v_l)
            seg_verts_right.append(v_r)

        for p in range(num_points):
            bm.faces.new((
                seg_verts_left[p], 
                seg_verts_left[p+1], 
                seg_verts_right[p+1], 
                seg_verts_right[p]
            ))

    mesh = bpy.data.meshes.new("FanPalmLeafMesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("FanPalmLeaf", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Slight tilt for dynamic composition
    obj.rotation_euler[0] = math.radians(-5) 
    obj.rotation_euler[2] = math.radians(random.uniform(-10, 10))
    
    return obj

def apply_refinements(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True

    subdiv = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subdiv.levels = 1
    subdiv.render_levels = 2

if __name__ == "__main__":
    clear_scene()
    palm_leaf = create_fan_palm()
    apply_refinements(palm_leaf)
