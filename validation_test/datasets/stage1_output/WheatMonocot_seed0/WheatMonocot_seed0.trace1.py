import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_wheat_plant():
    # Colors (Warm amber/golden-brown)
    stalk_color = (0.5, 0.35, 0.1, 1.0)
    grain_color = (0.8, 0.6, 0.2, 1.0)
    leaf_color = (0.4, 0.3, 0.1, 1.0)

    mat_stalk = create_material("Mat_Stalk", stalk_color)
    mat_grain = create_material("Mat_Grain", grain_color)
    mat_leaf = create_material("Mat_Leaf", leaf_color)

    # --- Main Stalk ---
    stalk_obj = bpy.data.objects.new("WheatStalk", None)
    bpy.context.collection.objects.link(stalk_obj)
    bm = bmesh.new()

    segments = 25
    height = 3.0
    radius = 0.018
    
    # Generate stalk path with slight curve
    path_verts = []
    for i in range(segments + 1):
        t = i / segments
        z = t * height
        x = math.sin(t * 2.0) * 0.08
        y = math.cos(t * 1.5) * 0.08
        path_verts.append(Vector((x, y, z)))

    # Create tube around path
    res = 8
    rings = []
    for i in range(segments + 1):
        center = path_verts[i]
        # Taper stalk slightly as it goes up
        current_radius = radius * (1.0 - t * 0.4) if 't' in locals() else radius
        # Re-calculate t for safety inside loop
        t_val = i / segments
        current_radius = radius * (1.0 - t_val * 0.5)
        
        ring = []
        for j in range(res):
            angle = (j / res) * 2 * math.pi
            vx = center.x + math.cos(angle) * current_radius
            vy = center.y + math.sin(angle) * current_radius
            vz = center.z
            ring.append(bm.verts.new(Vector((vx, vy, vz))))
        rings.append(ring)

    # Bridge the rings to form faces
    for i in range(segments):
        for j in range(res):
            v1 = rings[i][j]
            v2 = rings[i+1][j]
            v3 = rings[i+1][(j+1)%res]
            v4 = rings[i][(j+1)%res]
            bm.faces.new((v1, v2, v3, v4))

    # Cap the bottom
    bottom_center = bm.verts.new(Vector((path_verts[0].x, path_verts[0].y, path_verts[0].z)))
    for j in range(res):
        bm.faces.new((bottom_center, rings[0][j], rings[0][(j+1)%res]))

    stalk_mesh = bpy.data.meshes.new("StalkMesh")
    bm.to_mesh(stalk_mesh)
    stalk_obj.data = stalk_mesh
    bm.free()
    stalk_obj.data.materials.append(mat_stalk)

    # --- Leaves ---
    num_leaves = 8
    leaf_length = 1.4
    leaf_width = 0.03

    for i in range(num_leaves):
        z_pos = (i / num_leaves) * height * 0.6
        angle = (i / num_leaves) * 2 * math.pi
        # Offset from stalk center slightly
        base_pos = path_verts[int((i/num_leaves)*segments)]
        
        leaf_obj = bpy.data.objects.new(f"Leaf_{i}", None)
        bpy.context.collection.objects.link(leaf_obj)
        bm_l = bmesh.new()
        
        segments_l = 12
        l_verts_pairs = []
        for s in range(segments_l + 1):
            t = s / segments_l
            # Curve the leaf outward and then down
            # Parabolic arch: z increases slightly then drops
            lx = base_pos.x + t * leaf_length * math.cos(angle)
            ly = base_pos.y + t * leaf_length * math.sin(angle)
            lz = base_pos.z + (t * 0.2) - (t**2 * 0.7)
            
            # Taper the width of the leaf ribbon
            w = leaf_width * (1.0 - t*0.9)
            
            # Create a thin strip by offsetting vertices slightly on a plane perpendicular to curve
            perp_angle = angle + math.pi/2
            ox = math.cos(perp_angle) * w
            oy = math.sin(perp_angle) * w
            
            v1 = bm_l.verts.new(Vector((lx + ox, ly + oy, lz)))
            v2 = bm_l.verts.new(Vector((lx - ox, ly - oy, lz)))
            l_verts_pairs.append((v1, v2))
            
        for s in range(segments_l):
            bm_l.faces.new((l_verts_pairs[s][0], l_verts_pairs[s+1][0], l_verts_pairs[s+1][1], l_verts_pairs[s][1]))
            
        leaf_mesh = bpy.data.meshes.new(f"LeafMesh_{i}")
        bm_l.to_mesh(leaf_mesh)
        leaf_obj.data = leaf_mesh
        bm_l.free()
        leaf_obj.data.materials.append(mat_leaf)

    # --- The Ear (Grain head) ---
    grain_count = 36
    ear_start_z_idx = int(segments * 0.7)
    ear_end_z_idx = segments
    
    head_obj = bpy.data.objects.new("WheatHead", None)
    bpy.context.collection.objects.link(head_obj)
    bm_h = bmesh.new()

    # Sample points along the top part of the stalk path for grains
    for g in range(grain_count):
        # Distribution factor
        t_ear = g / grain_count
        idx = int(ear_start_z_idx + t_ear * (ear_end_z_idx - ear_start_z_idx))
        idx = min(idx, segments)
        center = path_verts[idx]
        
        # Alternate sides for grains
        side = 1 if (g % 2 == 0) else -1
        angle_offset = math.pi/4
        
        gx = center.x + side * 0.035 * math.cos(angle_offset)
        gy = center.y + side * 0.035 * math.sin(angle_offset)
        gz = center.z

        # Create a small seed-like shape (elongated ellipsoid)
        seed_res = 6
        seed_verts = []
        for i in range(seed_res):
            theta = (i / seed_res) * 2 * math.pi
            vx = gx + math.cos(theta) * 0.012
            vy = gy + math.sin(theta) * 0.012
            vz = gz
            seed_verts.append(bm_h.verts.new(Vector((vx, vy, vz))))
        
        top_v = bm_h.verts.new(Vector((gx, gy, gz + 0.03)))
        bot_v = bm_h.verts.new(Vector((gx, gy, gz - 0.02)))
        
        for i in range(seed_res):
            bm_h.faces.new((top_v, seed_verts[i], seed_verts[(i+1)%seed_res]))
            bm_h.faces.new((bot_v, seed_verts[(i+1)%seed_res], seed_verts[i]))

        # Create the Awn (long bristle) - represented as a thin tube for better rendering
        awn_len = 0.25 + random.uniform(0, 0.15)
        awn_dir = Vector((side * 0.4, side * 0.3, 0.8)).normalized()
        awn_end = Vector((gx, gy, gz)) + awn_dir * awn_len
        
        # Awn as a thin cylinder
        awn_res = 4
        a_rings = []
        for s in range(2): # start and end of bristle
            p = Vector((gx, gy, gz)) if s == 0 else awn_end
            ring = []
            for j in range(awn_res):
                ang = (j / awn_res) * 2 * math.pi
                # Bristle radius is very small
                br = 0.003
                vx = p.x + math.cos(ang) * br
                vy = p.y + math.sin(ang) * br
                vz = p.z
                ring.append(bm_h.verts.new(Vector((vx, vy, vz))))
            a_rings.append(ring)
        
        for j in range(awn_res):
            bm_h.faces.new((a_rings[0][j], a_rings[1][j], a_rings[1][(j+1)%awn_res], a_rings[0][(j+1)%awn_res]))

    head_mesh = bpy.data.meshes.new("HeadMesh")
    bm_h.to_mesh(head_mesh)
    head_obj.data = head_mesh
    bm_h.free()
    head_obj.data.materials.append(mat_grain)

if __name__ == "__main__":
    clear_scene()
    create_wheat_plant()
