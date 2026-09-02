import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_bmesh_cylinder(bm, radius=0.1, depth=1.0, segments=12):
    """Helper to create a cylinder within an existing bmesh."""
    half_depth = depth / 2
    # Bottom ring
    bottom_verts = []
    for i in range(segments):
        angle = (i / segments) * 2 * math.pi
        bottom_verts.append(bm.verts.new((math.cos(angle) * radius, math.sin(angle) * radius, -half_depth)))
    # Top ring
    top_verts = []
    for i in range(segments):
        angle = (i / segments) * 2 * math.pi
        top_verts.append(bm.verts.new((math.cos(angle) * radius, math.sin(angle) * radius, half_depth)))
    
    bm.verts.ensure_lookup_table()
    # Side faces
    for i in range(segments):
        v1 = bottom_verts[i]
        v2 = bottom_verts[(i + 1) % segments]
        v3 = top_verts[(i + 1) % segments]
        v4 = top_verts[i]
        bm.faces.new((v1, v2, v3, v4))
    # Caps
    bm.faces.new(bottom_verts[::-1])
    bm.faces.new(top_verts)

def create_stalk(height=4.0, radius=0.1):
    """Creates a segmented corn stalk with nodes."""
    bm = bmesh.new()
    segments = 20
    rings = 8
    
    for i in range(segments + 1):
        z = (i / segments) * height
        # Node bulge: sinusoidal variance
        node_scale = 1.0 + 0.15 * math.cos(i * math.pi) if i < segments else 1.0
        # Taper slightly towards the top
        curr_radius = radius * node_scale * (1.0 - (z / (height * 5)))
        
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

def create_leaf(length=2.5, width=0.4):
    """Creates a single arching leaf."""
    bm = bmesh.new()
    res_l = 16
    res_w = 6
    
    verts = []
    for i in range(res_l + 1):
        u = i / res_l
        x = u * length
        # Arching shape: parabolic curve with a bit of lift and drop
        z = -0.5 * (u**2) * length + (0.2 * u)
        y_offset = 0.1 * math.sin(u * math.pi)
        
        for j in range(res_w + 1):
            v = j / res_w
            # Taper width: wide at base, narrow at tip
            w = (v - 0.5) * width * (1.0 - u * 0.8)
            verts.append(bm.verts.new((x, y_offset + w, z)))
            
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
    """Creates an ear of corn with cob and kernels."""
    bm = bmesh.new()
    cob_radius = 0.12
    cob_height = 0.6
    create_bmesh_cylinder(bm, radius=cob_radius, depth=cob_height, segments=12)
    
    # Kernel geometry: small rounded blocks around the cob
    kernel_size = 0.03
    rows = 12
    cols = 14
    for r in range(rows):
        z_off = -cob_height/2 + (r / (rows-1)) * cob_height
        for c in range(cols):
            angle = (c / cols) * 2 * math.pi
            kx = math.cos(angle) * (cob_radius + kernel_size*0.3)
            ky = math.sin(angle) * (cob_radius + kernel_size*0.3)
            
            s = kernel_size / 2
            v1 = bm.verts.new((kx-s, ky-s, z_off-s))
            v2 = bm.verts.new((kx+s, ky-s, z_off-s))
            v3 = bm.verts.new((kx+s, ky+s, z_off-s))
            v4 = bm.verts.new((kx-s, ky+s, z_off-s))
            v5 = bm.verts.new((kx-s, ky-s, z_off+s))
            v6 = bm.verts.new((kx+s, ky-s, z_off+s))
            v7 = bm.verts.new((kx+s, ky+s, z_off+s))
            v8 = bm.verts.new((kx-s, ky+s, z_off+s))
            bm.faces.new((v1, v2, v6, v5))
            bm.faces.new((v2, v3, v7, v6))
            bm.faces.new((v3, v4, v8, v7))
            bm.faces.new((v4, v1, v5, v8))
            bm.faces.new((v5, v6, v7, v8))
            bm.faces.new((v1, v4, v3, v2))

    mesh = bpy.data.meshes.new("EarMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("CornEar", mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    return obj

def create_husk(position, rotation):
    """Creates a husk leaf wrapping the ear."""
    bm = bmesh.new()
    res = 10
    for i in range(res + 1):
        u = i / res
        x = u * 0.8 
        z = -0.2 * (u**2) * 0.7
        for j in range(res + 1):
            v = j / res
            w = (v - 0.5) * 0.4 * (1.0 - u * 0.5)
            bm.verts.new((x, w, z))
            
    bm.verts.ensure_lookup_table()
    for i in range(res):
        for j in range(res):
            idx = i * (res + 1) + j
            bm.faces.new((
                bm.verts[idx], 
                bm.verts[idx+1], 
                bm.verts[(i+1)*(res+1)+j+1], 
                bm.verts[(i+1)*(res+1)+j]
            ))
    
    mesh = bpy.data.meshes.new("HuskMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Husk", mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = rotation
    return obj

def create_tassel(top_pos):
    """Creates a tassel at the top of the plant."""
    num_branches = 12
    for i in range(num_branches):
        angle = (i / num_branches) * 2 * math.pi
        h = random.uniform(0.5, 0.9)
        
        bm_b = bmesh.new()
        create_bmesh_cylinder(bm_b, radius=0.015, depth=h, segments=4)
        m_b = bpy.data.meshes.new("BranchMesh")
        bm_b.to_mesh(m_b)
        bm_b.free()
        
        obj_b = bpy.data.objects.new("TasselBranch", m_b)
        bpy.context.collection.objects.link(obj_b)
        
        # Position base at top of stalk (cylinder origin is center, so offset by h/2)
        obj_b.location = Vector(top_pos) + Vector((0, 0, h/2))
        rot_x = math.radians(random.uniform(30, 60))
        obj_b.rotation_euler = (rot_x, 0, angle)

def assemble_maize():
    clear_scene()
    stalk_h = 4.0
    stalk = create_stalk(height=stalk_h)
    
    # Leaves spiraling up the stalk
    num_leaves = 14
    for i in range(num_leaves):
        z = (i / num_leaves) * (stalk_h * 0.8)
        angle = (i / num_leaves) * 2 * math.pi * 2.6 # Spiraled layout
        leaf = create_leaf()
        leaf.location = (0, 0, z)
        leaf.rotation_euler = (math.radians(random.uniform(-50, -30)), 0, angle)
    
    # Ears of corn
    num_ears = 2
    for i in range(num_ears):
        z_ear = 1.6 + (i * 0.8)
        angle_ear = random.uniform(0, 2 * math.pi)
        pos_ear = (math.cos(angle_ear)*0.1, math.sin(angle_ear)*0.1, z_ear)
        
        rot_euler = (math.radians(30), 0, angle_ear + math.pi/2)
        ear = create_ear(position=pos_ear)
        ear.rotation_euler = rot_euler
        
        # Husks wrapping the ear
        for h in range(3):
            husk = create_husk(position=pos_ear, rotation=rot_euler)
            husk.rotation_euler.z += (h * 1.2)

    create_tassel(top_pos=(0, 0, stalk_h))

if __name__ == "__main__":
    assemble_maize()
