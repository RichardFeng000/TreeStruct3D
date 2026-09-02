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
    num_segments = 48
    segment_length_min = 3.5
    segment_length_max = 5.5
    segment_width_base = 0.15
    segment_width_tip = 0.03
    fan_spread_angle = 170 * (math.pi / 180) # radians
    droop_amount = 1.2 # how much the segments curve downwards

    # Create a BMesh for the entire leaf assembly
    bm = bmesh.new()

    # --- Stem Construction ---
    # Tapered cylinder for the petiole (stem)
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
        
        # Length variation
        length = random.uniform(segment_length_min, segment_length_max)
        if i == 0 or i == num_segments - 1:
            length *= 0.8 # edges slightly shorter

        num_points = 12 # Resolution along the leaf length
        seg_verts_left = []
        seg_verts_right = []
        
        for p in range(num_points + 1):
            t = p / num_points # normalized distance [0, 1]
            
            # Radial direction on XY plane
            dir_vec = Vector((math.cos(angle), math.sin(angle), 0))
            perp_vec = Vector((-dir_vec.y, dir_vec.x, 0))
            
            # Taper width from base to tip
            current_width = segment_width_base * (1.0 - t * 0.85)
            if current_width < segment_width_tip:
                current_width = segment_width_tip

            # Curve logic: 
            # Z starts at stem_height and drops more significantly as t increases
            # We also add a slight "splay" so the leaf expands outwards before dropping
            z_pos = stem_height - (t**2) * droop_amount * 2.0
            
            # Calculate position based on radial direction and distance
            # Slightly modify length to create a more natural arc
            dist = t * length
            pos = center_point + dir_vec * dist
            pos.z = z_pos

            # Add slight organic noise (jitter) to the path
            if 0 < t < 1:
                noise_val = random.uniform(-0.08, 0.08)
                pos += perp_vec * noise_val * math.sin(t * math.pi)

            # Create vertex pair for the width of the strip
            v_l = bm.verts.new(pos + perp_vec * (current_width / 2))
            v_r = bm.verts.new(pos - perp_vec * (current_width / 2))
            seg_verts_left.append(v_l)
            seg_verts_right.append(v_r)

        # Create faces for the segment strip
        for p in range(num_points):
            bm.faces.new((
                seg_verts_left[p], 
                seg_verts_left[p+1], 
                seg_verts_right[p+1], 
                seg_verts_right[p]
            ))

    # Create Mesh and Object correctly
    mesh = bpy.data.meshes.new("FanPalmLeafMesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("FanPalmLeaf", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Slight tilt to make it look more dynamic
    obj.rotation_euler[0] = math.radians(-10) 
    obj.rotation_euler[2] = math.radians(random.uniform(-15, 15))
    
    return obj

def apply_refinements(obj):
    """Adds smooth shading and subdivision for an organic look."""
    # Smooth Shading
    for poly in obj.data.polygons:
        poly.use_smooth = True

    # Subdivision Surface
    subdiv = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subdiv.levels = 1
    subdiv.render_levels = 2
    
    # Optional: Add a very slight thicken for better rendering if needed, 
    # but requested is "narrow radiating segments" (blades).

if __name__ == "__main__":
    clear_scene()
    palm_leaf = create_fan_palm()
    apply_refinements(palm_leaf)
