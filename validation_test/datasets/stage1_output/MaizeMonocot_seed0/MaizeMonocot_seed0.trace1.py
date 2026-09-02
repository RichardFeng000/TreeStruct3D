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
    segments = 12
    rings = 20
    
    verts = []
    for i in range(rings + 1):
        z = (i / rings) * height
        taper = 1.0 - (z / (height * 4)) # Slight taper upwards
        node_scale = 1.0 + 0.03 * math.sin(i * 0.8)
        curr_radius = radius * node_scale * taper
        
        ring = []
        for j in range(segments):
            angle = (j / segments) * 2 * math.pi
            x = math.cos(angle) * curr_radius
            y = math.sin(angle) * curr_radius
            ring.append(bm.verts.new((x, y, z)))
        verts.append(ring)
    
    for i in range(rings):
        for j in range(segments):
            v1 = verts[i][j]
            v2 = verts[i][(j + 1) % segments]
            v3 = verts[i+1][(j + 1) % segments]
            v4 = verts[i+1][j]
            bm.faces.new((v1, v2, v3, v4))
            
    mesh = bpy.data.meshes.new("StalkMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("CornStalk", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_leaf(length=2.5, width=0.6):
    bm = bmesh.new()
    res_l = 12
    res_w = 4
    
    verts = []
    for i in range(res_l + 1):
        u = i / res_l
        # Spine: Curved arching downwards
        x = u * length
        y_drift = 0.1 * math.sin(u * math.pi)
        z = - (u**2) * 1.5 # Arch downward
        
        # Taper width: starts narrow, wide in middle, ends pointed
        taper = math.sin(u * math.pi) * width
        if u < 0.1: taper = (u/0.1) * 0.2 # Narrow base
        
        row = []
        for j in range(res_w + 1):
            v = j / res_w
            offset = (v - 0.5) * taper
            row.append(bm.verts.new((x, y_drift + offset, z)))
        verts.append(row)
            
    for i in range(res_l):
        for j in range(res_w):
            bm.faces.new((
                verts[i][j], 
                verts[i][j+1], 
                verts[i+1][j+1], 
                verts[i+1][j]
            ))
    
    mesh = bpy.data.meshes.new("LeafMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Leaf", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_ear():
    # Cob core
    cob_bm = bmesh.new()
    cob_r, cob_h = 0.15, 0.6
    segs = 12
    
    bottom_ring = [cob_bm.verts.new((math.cos(i/segs*2*math.pi)*cob_r, math.sin(i/segs*2*math.pi)*cob_r, -cob_h/2)) for i in range(segs)]
    top_ring = [cob_bm.verts.new((math.cos(i/segs*2*math.pi)*cob_r, math.sin(i/segs*2*math.pi)*cob_r, cob_h/2)) for i in range(segs)]
    for i in range(segs):
        cob_bm.faces.new((bottom_ring[i], bottom_ring[(i+1)%segs], top_ring[(i+1)%segs], top_ring[i]))
    
    cob_mesh = bpy.data.meshes.new("CobMesh")
    cob_bm.to_mesh(cob_mesh)
    cob_bm.free()
    cob_obj = bpy.data.objects.new("CornCob", cob_mesh)
    bpy.context.collection.objects.link(cob_obj)

    # Husks
    for h in range(3):
        husk_bm = bmesh.new()
        res = 10
        for i in range(res + 1):
            u = i / res
            z = (u - 0.5) * cob_h * 1.2
            # Peeling effect: bottom tight, top opens
            peel = u**2 * 0.3
            for j in range(res + 1):
                v = j / res
                w = (v - 0.5) * 0.6 # husk width
                dist_from_center = cob_r + peel
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
        h_obj.rotation_euler.z = math.radians(h * 120)
        h_obj.parent = cob_obj

    return cob_obj

def create_tassel_branch():
    bm = bmesh.new()
    segs = 8
    radius = 0.02
    height = random.uniform(0.4, 0.8)
    
    verts = []
    for i in range(segs + 1):
        u = i / segs
        # Curved branch path
        x = math.sin(u * math.pi/2) * (height * 0.3)
        y = math.cos(u * math.pi/2) * (height * 0.1)
        z = u * height
        
        ring = []
        for j in range(6):
            angle = (j / 6) * 2 * math.pi
            vx = x + math.cos(angle) * radius
            vy = y + math.sin(angle) * radius
            ring.append(bm.verts.new((vx, vy, z)))
        verts.append(ring)
        
    for i in range(segs):
        for j in range(6):
            bm.faces.new((verts[i][j], verts[i][(j+1)%6], verts[i+1][(j+1)%6], verts[i+1][j]))
            
    mesh = bpy.data.meshes.new("TasselBranchMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("TasselBranch", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def assemble_maize():
    clear_scene()
    stalk_h = 4.0
    stalk_r = 0.15
    stalk = create_stalk(height=stalk_h, radius=stalk_r)
    
    # Leaves - spiral arrangement
    num_leaves = 16
    for i in range(num_leaves):
        z = (i / num_leaves) * (stalk_h * 0.75) + 0.4
        angle = (i / num_leaves) * 2 * math.pi * 2.5 # Golden angle approx
        leaf = create_leaf()
        # Position leaf at the stalk surface
        leaf.location = (math.cos(angle)*stalk_r, math.sin(angle)*stalk_r, z)
        leaf.rotation_euler = (0, 0, angle)
        # Randomize pitch and roll slightly
        leaf.rotation_euler.x = math.radians(random.uniform(-15, 15))
        leaf.rotation_euler.y = math.radians(random.uniform(-10, 10))
    
    # Ears of corn - placed mid-stalk
    num_ears = 2
    for i in range(num_ears):
        z_ear = 1.5 + (i * 0.6)
        angle_ear = math.pi * (i * 1.4)
        pos_ear = (math.cos(angle_ear)*stalk_r, math.sin(angle_ear)*stalk_r, z_ear)
        ear = create_ear()
        ear.location = pos_ear
        # Orient ear to point outwards and slightly up
        ear.rotation_euler = (math.radians(20), 0, angle_ear + math.pi/2)

    # Tassel - top cluster of branches
    num_branches = 30
    for i in range(num_branches):
        branch = create_tassel_branch()
        branch.location = (0, 0, stalk_h)
        angle = (i / num_branches) * 2 * math.pi
        # Distribute branches outward from center
        phi = random.uniform(math.radians(30), math.radians(60))
        branch.rotation_euler = (phi, 0, angle)

if __name__ == "__main__":
    assemble_maize()
