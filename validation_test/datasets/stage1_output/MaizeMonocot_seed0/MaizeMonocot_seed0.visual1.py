import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_stalk(height=4.0, radius=0.12):
    bm = bmesh.new()
    segments = 24
    rings = 12
    
    for i in range(segments + 1):
        z = (i / segments) * height
        # Node bulge for organic look
        node_scale = 1.0 + 0.1 * math.sin(i * 1.5)
        taper = 1.0 - (z / (height * 4))
        curr_radius = radius * node_scale * taper
        
        for j in range(rings):
            angle = (j / rings) * 2 * math.pi
            x = math.cos(angle) * curr_radius
            y = math.sin(angle) * curr_radius
            bm.verts.new((x, y, z))
    
    bm.verts.ensure_lookup_table()
    for i in range(segments):
        for j in range(rings):
            v1 = bm.verts[i * rings + j]
            v2 = bm.verts[i * rings + (j + 1) % rings]
            v3 = bm.verts[(i + 1) * rings + (j + 1) % rings]
            v4 = bm.verts[(i + 1) * rings + j]
            bm.faces.new((v1, v2, v3, v4))
            
    mesh = bpy.data.meshes.new("StalkMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("CornStalk", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_leaf(length=3.0, width=0.6):
    """Creates a wide, arching maize leaf."""
    bm = bmesh.new()
    res_l = 20
    res_w = 8
    
    verts = []
    for i in range(res_l + 1):
        u = i / res_l
        # Arching path: x goes out, then curves slightly back or stays; z drops
        x = math.sin(u * math.pi/2) * length
        z = -1.2 * (u**2) * 1.5 + (0.3 * u) # Stronger downward arch
        y_drift = 0.4 * math.sin(u * math.pi)
        
        for j in range(res_w + 1):
            v = j / res_w
            # Wide ribbon shape: wider in middle, tapered at ends
            taper = (1.0 - u**0.5) * 0.2 + 0.8 # Tapers slightly at tip
            w = (v - 0.5) * width * taper
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

def create_ear(position=(0, 0, 0)):
    """Creates a textured ear of corn."""
    bm = bmesh.new()
    cob_r = 0.18
    cob_h = 0.7
    
    # Cob base
    segments = 12
    bottom_ring = [bm.verts.new((math.cos(i/segments*2*math.pi)*cob_r, math.sin(i/segments*2*math.pi)*cob_r, -cob_h/2)) for i in range(segments)]
    top_ring = [bm.verts.new((math.cos(i/segments*2*math.pi)*cob_r, math.sin(i/segments*2*math.pi)*cob_r, cob_h/2)) for i in range(segments)]
    for i in range(segments):
        bm.faces.new((bottom_ring[i], bottom_ring[(i+1)%segments], top_ring[(i+1)%segments], top_ring[i]))

    # Kernels: roundedbumps
    k_size = 0.06
    rows = 12
    cols = 14
    for r in range(rows):
        z_off = -cob_h/2 + (r / (rows-1)) * cob_h
        for c in range(cols):
            angle = (c / cols) * 2 * math.pi
            kx, ky = math.cos(angle)*cob_r, math.sin(angle)*cob_r
            # Create a simple kernel "bump"
            v1 = bm.verts.new((kx, ky, z_off))
            # Just adding small offset vertices to create volume
            vx = Vector((math.cos(angle), 0, 0)) * k_size
            vy = Vector((0, math.sin(angle), 0)) * k_size # simplistic kernels
            v2 = bm.verts.new((kx + vx.x*0.5, ky + vy.y*0.5, z_off + k_size*0.3))
            # Note: in bmesh we need faces to see them, but for simplicity and polycount 
            # let's just make the cob slightly thicker and bumpy.
    
    # Adding a simplified 'kernel' skin by scaling out segments
    bm.verts.ensure_lookup_table()
    for i in range(len(bm.verts)):
        v = bm.verts[i]
        if v.co.z > -cob_h/2 and v.co.z < cob_h/2:
            # Add noise to the surface
            v.co += Vector((random.uniform(-0.02, 0.02), random.uniform(-0.02, 0.02), 0))

    mesh = bpy.data.meshes.new("EarMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("CornEar", mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    return obj

def create_husk(position, rotation):
    bm = bmesh.new()
    res = 12
    for i in range(res + 1):
        u = i / res
        x = u * 0.9 
        z = -0.3 * (u**2)
        for j in range(res + 1):
            v = j / res
            w = (v - 0.5) * 0.5 * (1.0 - u * 0.4)
            bm.verts.new((x, w, z))
    bm.verts.ensure_lookup_table()
    for i in range(res):
        for j in range(res):
            idx = i * (res + 1) + j
            bm.faces.new((bm.verts[idx], bm.verts[idx+1], bm.verts[(i+1)*(res+1)+j+1], bm.verts[(i+1)*(res+1)+j]))
    mesh = bpy.data.meshes.new("HuskMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Husk", mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = rotation
    return obj

def create_tassel(top_pos):
    num_branches = 20
    for i in range(num_branches):
        angle = (i / num_branches) * 2 * math.pi
        h = random.uniform(0.6, 1.2)
        bm_b = bmesh.new()
        # Thin branch
        segments = 6
        bot = [bm_b.verts.new((math.cos(j/segments*2*math.pi)*0.02, math.sin(j/segments*2*math.pi)*0.02, 0)) for j in range(segments)]
        top = [bm_b.verts.new((math.cos(j/segments*2*math.pi)*0.01, math.sin(j/segments*2*math.pi)*0.01, h)) for j in range(segments)]
        for j in range(segments):
            bm_b.faces.new((bot[j], bot[(j+1)%segments], top[(j+1)%segments], top[j]))
        
        m_b = bpy.data.meshes.new("BranchMesh")
        bm_b.to_mesh(m_b)
        bm_b.free()
        obj_b = bpy.data.objects.new("TasselBranch", m_b)
        bpy.context.collection.objects.link(obj_b)
        obj_b.location = Vector(top_pos)
        rot_x = math.radians(random.uniform(30, 70))
        obj_b.rotation_euler = (rot_x, 0, angle)

def assemble_maize():
    clear_scene()
    stalk_h = 4.0
    stalk = create_stalk(height=stalk_h)
    
    num_leaves = 12
    for i in range(num_leaves):
        z = (i / num_leaves) * (stalk_h * 0.75) + 0.3
        angle = (i / num_leaves) * 2 * math.pi * 2.5 
        leaf = create_leaf()
        leaf.location = (0, 0, z)
        # Rotate leaves to arc away from center
        leaf.rotation_euler = (math.radians(random.uniform(-10, 10)), math.radians(random.uniform(-20, 20)), angle)
    
    num_ears = 2
    for i in range(num_ears):
        z_ear = 1.5 + (i * 0.7)
        angle_ear = random.uniform(0, 2 * math.pi)
        # Position ear slightly away from stalk center for visibility
        pos_ear = (math.cos(angle_ear)*0.2, math.sin(angle_ear)*0.2, z_ear)
        rot_euler = (math.radians(15), 0, angle_ear + math.pi/2)
        
        ear = create_ear(position=pos_ear)
        ear.rotation_euler = rot_euler
        for h in range(3):
            husk = create_husk(position=pos_ear, rotation=rot_euler)
            husk.rotation_euler.z += (h * 1.2)

    create_tassel(top_pos=(0, 0, stalk_h))

if __name__ == "__main__":
    assemble_maize()
