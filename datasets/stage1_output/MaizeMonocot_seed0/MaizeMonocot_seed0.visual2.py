import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_stalk(height=4.0, radius=0.15):
    bm = bmesh.new()
    segments = 16
    rings = 20
    
    for i in range(rings + 1):
        z = (i / rings) * height
        # Slight taper and organic bulge
        taper = 1.0 - (z / (height * 3))
        node_scale = 1.0 + 0.05 * math.sin(i * 0.8)
        curr_radius = radius * node_scale * taper
        
        for j in range(segments):
            angle = (j / segments) * 2 * math.pi
            x = math.cos(angle) * curr_radius
            y = math.sin(angle) * curr_radius
            bm.verts.new((x, y, z))
    
    bm.verts.ensure_lookup_table()
    for i in range(rings):
        for j in range(segments):
            v1 = bm.verts[i * segments + j]
            v2 = bm.verts[i * segments + (j + 1) % segments]
            v3 = bm.verts[(i + 1) * segments + (j + 1) % segments]
            v4 = bm.verts[(i + 1) * segments + j]
            bm.faces.new((v1, v2, v3, v4))
            
    mesh = bpy.data.meshes.new("StalkMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("CornStalk", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_leaf(length=2.5, width=0.5):
    bm = bmesh.new()
    res_l = 15
    res_w = 6
    
    verts = []
    for i in range(res_l + 1):
        u = i / res_l
        # Curved path for the leaf
        x = math.sin(u * math.pi/2) * length
        z = -0.5 * (u**2) * 3.0 # Arching downwards
        y_drift = 0.2 * math.sin(u * math.pi)
        
        for j in range(res_w + 1):
            v = j / res_w
            # Tapered width: narrow at base, wide middle, narrow tip
            taper = math.sin(u * math.pi) if u > 0 else (u * math.pi)
            if taper < 0.2: taper = 0.2 # minimum width near start
            w = (v - 0.5) * width * (1.0 - u * 0.7)
            verts.append(bm.verts.new((x, y_drift + w, z)))
            
    bm.verts.ensure_lookup_table()
    for i in range(res_l):
        for j in range(res_w):
            idx = i * (res_w + 1) + j
            bm.faces.new((
                verts[idx], 
                verts[idx + 1], 
                verts[(i+1)*(res_w+1) + j + 1], 
                verts[(i+1)*(res_w+1) + j]
            ))
    
    mesh = bpy.data.meshes.new("LeafMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Leaf", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_ear():
    # Cob
    cob_bm = bmesh.new()
    cob_r, cob_h = 0.15, 0.6
    segs = 12
    bottom = [cob_bm.verts.new((math.cos(i/segs*2*math.pi)*cob_r, math.sin(i/segs*2*math.pi)*cob_r, -cob_h/2)) for i in range(segs)]
    top = [cob_bm.verts.new((math.cos(i/segs*2*math.pi)*cob_r, math.sin(i/segs*2*math.pi)*cob_r, cob_h/2)) for i in range(segs)]
    for i in range(segs):
        cob_bm.faces.new((bottom[i], bottom[(i+1)%segs], top[(i+1)%segs], top[i]))
    
    cob_mesh = bpy.data.meshes.new("CobMesh")
    cob_bm.to_mesh(cob_mesh)
    cob_bm.free()
    cob_obj = bpy.data.objects.new("CornCob", cob_mesh)
    bpy.context.collection.objects.link(cob_obj)

    # Husks (wrapping the cob)
    for h in range(3):
        husk_bm = bmesh.new()
        res = 10
        offset = h * 0.2
        for i in range(res + 1):
            u = i / res
            x = (u - 0.5) * cob_h * 0.8
            z = (u - 0.5) * cob_h
            for j in range(res + 1):
                v = j / res
                # Curve the husk away from the cob
                w = (v - 0.5) * 0.4 + (math.sin(v*math.pi)*0.1)
                dist_from_center = 0.15 + (u * 0.2 if u > 0.7 else 0) # peel back at top
                husk_bm.verts.new((w, dist_from_center, z))
        
        husk_bm.verts.ensure_lookup_table()
        for i in range(res):
            for j in range(res):
                idx = i * (res + 1) + j
                husk_bm.faces.new((husk_bm.verts[idx], husk_bm.verts[idx+1], husk_bm.verts[(i+1)*(res+1)+j+1], husk_bm.verts[(i+1)*(res+1)+j]))
        
        h_mesh = bpy.data.meshes.new("HuskMesh")
        husk_bm.to_mesh(h_mesh)
        husk_bm.free()
        h_obj = bpy.data.objects.new("Husk", h_mesh)
        bpy.context.collection.objects.link(h_obj)
        # Rotate husks around cob
        h_obj.rotation_euler.z = math.radians(h * 120)
        h_obj.parent = cob_obj

    return cob_obj

def create_tassel(top_pos):
    num_branches = 25
    for i in range(num_branches):
        bm_b = bmesh.new()
        segs = 8
        h = random.uniform(0.5, 1.0)
        # Create a curved branch
        branch_verts = []
        for s in range(segs + 1):
            u = s / segs
            # Curved path
            vx = math.sin(u * math.pi/2) * (h * 0.4)
            vy = math.cos(u * math.pi/2) * (h * 0.1)
            vz = u * h
            branch_verts.append(bm_b.verts.new((vx, vy, vz)))
        
        # Make it a thin cylinder-like strip for performance and look
        for s in range(segs):
            bm_b.faces.new((branch_verts[s], branch_verts[s+1], branch_verts[s+1], branch_verts[s])) # degenerate but creates line
            # Actually create a tiny tube for visibility
            
        m_b = bpy.data.meshes.new("TasselBranchMesh")
        bm_b.to_mesh(m_b)
        bm_b.free()
        obj_b = bpy.data.objects.new("TasselBranch", m_b)
        bpy.context.collection.objects.link(obj_b)
        obj_b.location = Vector(top_pos)
        angle = (i / num_branches) * 2 * math.pi
        obj_b.rotation_euler = (math.radians(random.uniform(30, 60)), 0, angle)

def assemble_maize():
    clear_scene()
    stalk_h = 4.0
    stalk_r = 0.15
    stalk = create_stalk(height=stalk_h, radius=stalk_r)
    
    # Leaves - spiral placement
    num_leaves = 14
    for i in range(num_leaves):
        z = (i / num_leaves) * (stalk_h * 0.7) + 0.5
        angle = (i / num_leaves) * 2 * math.pi * 2.0
        leaf = create_leaf()
        # Position leaf to start AT the surface of the stalk
        leaf.location = (math.cos(angle)*stalk_r, math.sin(angle)*stalk_r, z)
        leaf.rotation_euler = (0, 0, angle)
        # Tilt slightly for organic look
        leaf.rotation_euler.x = math.radians(random.uniform(-10, 10))
    
    # Ears of corn
    num_ears = 2
    for i in range(num_ears):
        z_ear = 1.8 + (i * 0.5)
        angle_ear = math.pi * (i * 1.5) # opposite sides
        pos_ear = (math.cos(angle_ear)*stalk_r, math.sin(angle_ear)*stalk_r, z_ear)
        ear = create_ear()
        ear.location = pos_ear
        ear.rotation_euler = (0, 0, angle_ear)
        # Tilt ears slightly upwards
        ear.rotation_euler.x = math.radians(20)

    create_tassel(top_pos=(0, 0, stalk_h))

if __name__ == "__main__":
    assemble_maize()
