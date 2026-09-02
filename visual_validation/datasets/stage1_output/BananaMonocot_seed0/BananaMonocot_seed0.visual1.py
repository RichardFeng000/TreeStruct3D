import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_stalk():
    """Creates the pseudostem of the banana plant."""
    bm = bmesh.new()
    segments = 16
    height = 3.0
    radius = 0.3
    
    # Create a slightly tapered, organic cylinder
    verts = []
    for i in range(segments):
        angle = (math.pi * 2 * i) / segments
        verts.append(bm.verts.new(Vector((math.cos(angle)*radius, math.sin(angle)*radius, 0))))
    
    layers = 15
    current_verts = verts
    for layer in range(layers):
        z = (height / layers) * (layer + 1)
        taper = 1.0 - (layer / layers) * 0.2
        new_verts = []
        for i in range(segments):
            angle = (math.pi * 2 * i) / segments
            # Add organic bumpiness
            r = radius * taper + random.uniform(-0.03, 0.03)
            v = bm.verts.new(Vector((math.cos(angle)*r, math.sin(angle)*r, z)))
            new_verts.append(v)
        
        for i in range(segments):
            bm.faces.new((current_verts[i], current_verts[(i+1)%segments], new_verts[(i+1)%segments], new_verts[i]))
        current_verts = new_verts

    bm.faces.new(current_verts)
    mesh = bpy.data.meshes.new("Stalk")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Stalk", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_leaf(angle, height, scale=1.0):
    """Creates a large, broad banana leaf."""
    bm = bmesh.new()
    
    res_len = 24
    res_wid = 16
    length = 4.5 * scale
    width = 1.4 * scale # Significantly wider for "broad" appearance
    
    verts = []
    for i in range(res_len + 1):
        u = i / res_len
        # Broad paddle shape: starts narrow, widens quickly, then tapers slowly
        current_w = math.sin(u * math.pi * 0.8 + 0.2) * width
        row = []
        for j in range(res_wid + 1):
            v_val = (j / res_wid) - 0.5
            x = u * length
            y = v_val * current_w
            # Subtle central fold
            z = abs(v_val) * 0.2 * (1.0 - u) 
            row.append(bm.verts.new(Vector((x, y, z))))
        verts.append(row)

    for i in range(res_len):
        for j in range(res_wid):
            bm.faces.new((verts[i][j], verts[i+1][j], verts[i+1][j+1], verts[i][j+1]))

    # Warp the leaf: curve outward and then droop heavily
    for v in bm.verts:
        ox, oy, oz = v.co
        # 1. Outward arc
        arc_angle = ox * 0.3
        v.co.x = ox * math.cos(arc_angle) - oy * math.sin(arc_angle)
        v.co.y = ox * math.sin(arc_angle) + oy * math.cos(arc_angle)
        # 2. Heavy tropical droop
        v.co.z -= (ox**2) * 0.4

    mesh = bpy.data.meshes.new("Leaf")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Leaf", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Position at stalk height and rotate
    obj.location = Vector((0, 0, height))
    obj.rotation_euler[2] = angle
    # Angle it away from the center
    obj.rotation_euler[1] = math.radians(-30)
    
    return obj

def create_cigar_shoot():
    """The tightly rolled emerging central shoot."""
    bm = bmesh.new()
    segments = 12
    height = 1.5
    radius = 0.2
    
    verts = []
    for i in range(segments):
        angle = (math.pi * 2 * i) / segments
        verts.append(bm.verts.new(Vector((math.cos(angle)*radius, math.sin(angle)*radius, 0))))
        
    top_verts = []
    for i in range(segments):
        angle = (math.pi * 2 * i) / segments
        r_top = radius * 0.3
        top_verts.append(bm.verts.new(Vector((math.cos(angle)*r_top, math.sin(angle)*r_top, height))))
        
    for i in range(segments):
        bm.faces.new((verts[i], verts[(i+1)%segments], top_verts[(i+1)%segments], top_verts[i]))
        
    center_top = bm.verts.new(Vector((0, 0, height + 0.1)))
    for i in range(segments):
        bm.faces.new((top_verts[i], top_verts[(i+1)%segments], center_top))

    mesh = bpy.data.meshes.new("CigarShoot")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("CigarShoot", mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = Vector((0, 0, 3.0))
    return obj

def assemble_plant():
    clear_scene()
    create_stalk()
    
    num_leaves = 7
    for i in range(num_leaves):
        angle = (math.pi * 2 * i) / num_leaves
        # Distribute leaves along the upper half of the stalk
        h = 0.8 + (i / num_leaves) * 1.8
        scale = 0.8 + (i / num_leaves) * 0.4
        create_leaf(angle, h, scale=scale)
        
    create_cigar_shoot()

if __name__ == "__main__":
    assemble_plant()
