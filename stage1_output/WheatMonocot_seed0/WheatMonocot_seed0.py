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
    stalk_color = (0.45, 0.3, 0.1, 1.0)
    grain_color = (0.8, 0.6, 0.2, 1.0)
    leaf_color = (0.3, 0.2, 0.1, 1.0)

    mat_stalk = create_material("Mat_Stalk", stalk_color)
    mat_grain = create_material("Mat_Grain", grain_color)
    mat_leaf = create_material("Mat_Leaf", leaf_color)

    # --- Main Stalk ---
    segments = 30
    height = 3.5
    radius = 0.02
    
    path_verts = []
    for i in range(segments + 1):
        t = i / segments
        z = t * height
        x = math.sin(t * 1.8) * 0.1
        y = math.cos(t * 1.2) * 0.1
        path_verts.append(Vector((x, y, z)))

    bm_stalk = bmesh.new()
    res = 8
    rings = []
    for i in range(segments + 1):
        center = path_verts[i]
        t_val = i / segments
        current_radius = radius * (1.0 - t_val * 0.4)
        
        ring = []
        for j in range(res):
            angle = (j / res) * 2 * math.pi
            vx = center.x + math.cos(angle) * current_radius
            vy = center.y + math.sin(angle) * current_radius
            vz = center.z
            ring.append(bm_stalk.verts.new(Vector((vx, vy, vz))))
        rings.append(ring)

    for i in range(segments):
        for j in range(res):
            v1 = rings[i][j]
            v2 = rings[i+1][j]
            v3 = rings[i+1][(j+1)%res]
            v4 = rings[i][(j+1)%res]
            bm_stalk.faces.new((v1, v2, v3, v4))

    # Close the bottom
    bottom_center = bm_stalk.verts.new(path_verts[0])
    for j in range(res):
        bm_stalk.faces.new((bottom_center, rings[0][j], rings[0][(j+1)%res]))

    stalk_mesh = bpy.data.meshes.new("StalkMesh")
    bm_stalk.to_mesh(stalk_mesh)
    stalk_obj = bpy.data.objects.new("WheatStalk", stalk_mesh)
    bpy.context.collection.objects.link(stalk_obj)
    stalk_obj.data.materials.append(mat_stalk)
    bm_stalk.free()

    # --- Leaves ---
    num_leaves = 10
    leaf_length = 1.6
    leaf_width = 0.04

    for i in range(num_leaves):
        t_pos = (i / num_leaves) * 0.7 # leaves only on bottom 70%
        z_idx = int(t_pos * segments)
        base_pos = path_verts[z_idx]
        angle = (i / num_leaves) * 2 * math.pi
        
        bm_l = bmesh.new()
        segments_l = 15
        l_verts_pairs = []
        for s in range(segments_l + 1):
            t = s / segments_l
            # Curve: arch out and then drop
            lx = base_pos.x + t * leaf_length * math.cos(angle)
            ly = base_pos.y + t * leaf_length * math.sin(angle)
            lz = base_pos.z + (t * 0.3) - (t**2 * 0.8)
            
            w = leaf_width * (1.0 - t*0.95)
            perp_angle = angle + math.pi/2
            ox = math.cos(perp_angle) * w * 0.5
            oy = math.sin(perp_angle) * w * 0.5
            
            v1 = bm_l.verts.new(Vector((lx + ox, ly + oy, lz)))
            v2 = bm_l.verts.new(Vector((lx - ox, ly - oy, lz)))
            l_verts_pairs.append((v1, v2))
            
        for s in range(segments_l):
            bm_l.faces.new((l_verts_pairs[s][0], l_verts_pairs[s+1][0], l_verts_pairs[s+1][1], l_verts_pairs[s][1]))
            
        leaf_mesh = bpy.data.meshes.new(f"LeafMesh_{i}")
        bm_l.to_mesh(leaf_mesh)
        leaf_obj = bpy.data.objects.new(f"Leaf_{i}", leaf_mesh)
        bpy.context.collection.objects.link(leaf_obj)
        leaf_obj.data.materials.append(mat_leaf)
        bm_l.free()

    # --- The Ear (Grain Head) ---
    grain_count = 40
    ear_start_idx = int(segments * 0.7)
    
    bm_h = bmesh.new()
    for g in range(grain_count):
        t_ear = g / grain_count
        idx = int(ear_start_idx + t_ear * (segments - ear_start_idx))
        idx = min(idx, segments)
        center = path_verts[idx]
        
        side = 1 if (g % 2 == 0) else -1
        # Grain offset slightly from central stalk
        offset_angle = math.pi/4 if side == 1 else 5*math.pi/4
        gx = center.x + math.cos(offset_angle) * 0.03
        gy = center.y + math.sin(offset_angle) * 0.03
        gz = center.z

        # Grain seed shape (elongated diamond/ellipsoid)
        s_res = 6
        seed_verts = []
        for i in range(s_res):
            theta = (i / s_res) * 2 * math.pi
            vx = gx + math.cos(theta) * 0.015
            vy = gy + math.sin(theta) * 0.015
            vz = gz
            seed_verts.append(bm_h.verts.new(Vector((vx, vy, vz))))
        
        top_v = bm_h.verts.new(Vector((gx, gy, gz + 0.04)))
        bot_v = bm_h.verts.new(Vector((gx, gy, gz - 0.02)))
        
        for i in range(s_res):
            bm_h.faces.new((top_v, seed_verts[i], seed_verts[(i+1)%s_res]))
            bm_h.faces.new((bot_v, seed_verts[(i+1)%s_res], seed_verts[i]))

        # Awn (bristle)
        awn_len = 0.2 + random.uniform(0, 0.2)
        # Point awns generally upwards and outwards
        awn_dir = Vector((side * 0.3, side * 0.2, 1.0)).normalized()
        awn_end = Vector((gx, gy, gz)) + awn_dir * awn_len
        
        a_res = 4
        a_rings = []
        for s in range(2):
            p = Vector((gx, gy, gz)) if s == 0 else awn_end
            ring = []
            for j in range(a_res):
                ang = (j / a_res) * 2 * math.pi
                br = 0.003
                vx = p.x + math.cos(ang) * br
                vy = p.y + math.sin(ang) * br
                vz = p.z
                ring.append(bm_h.verts.new(Vector((vx, vy, vz))))
            a_rings.append(ring)
        
        for j in range(a_res):
            bm_h.faces.new((a_rings[0][j], a_rings[1][j], a_rings[1][(j+1)%a_res], a_rings[0][(j+1)%a_res]))

    head_mesh = bpy.data.meshes.new("HeadMesh")
    bm_h.to_mesh(head_mesh)
    head_obj = bpy.data.objects.new("WheatHead", head_mesh)
    bpy.context.collection.objects.link(head_obj)
    head_obj.data.materials.append(mat_grain)
    bm_h.free()

if __name__ == "__main__":
    clear_scene()
    create_wheat_plant()
