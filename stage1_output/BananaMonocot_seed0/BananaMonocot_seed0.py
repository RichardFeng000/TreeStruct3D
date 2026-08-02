import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_stalk():
    """Creates a thick, organic pseudostem for the banana plant."""
    bm = bmesh.new()
    segments = 16
    height = 3.5
    base_radius = 0.5
    top_radius = 0.3
    
    # Create rings of vertices to form a tapered cylinder
    layers = 20
    verts_per_layer = []
    for layer in range(layers + 1):
        z = (height / layers) * layer
        r = base_radius - (base_radius - top_radius) * (layer / layers)
        # Add slight organic noise to radius
        r += random.uniform(-0.04, 0.04) if 0 < layer < layers else 0
        
        ring = []
        for i in range(segments):
            angle = (2 * math.pi * i) / segments
            v = bm.verts.new(Vector((math.cos(angle) * r, math.sin(angle) * r, z)))
            ring.append(v)
        verts_per_layer.append(ring)

    # Create faces between rings
    for layer in range(layers):
        curr = verts_per_layer[layer]
        nxt = verts_per_layer[layer+1]
        for i in range(segments):
            bm.faces.new((curr[i], curr[(i+1)%segments], nxt[(i+1)%segments], nxt[i]))

    # Cap the bottom and top
    bm.faces.new(verts_per_layer[0])
    bm.faces.new(reversed(verts_per_layer[-1]))

    mesh = bpy.data.meshes.new("Stalk")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Stalk", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_leaf(angle, height, scale=1.0):
    """Creates a large, broad banana leaf with a central midrib and organic droop."""
    bm = bmesh.new()
    
    res_len = 32
    res_wid = 20
    length = 6.0 * scale
    max_width = 2.0 * scale
    
    # Create a broad paddle shape geometry
    verts = []
    for i in range(res_len + 1):
        u = i / res_len # length parameter [0, 1]
        # Broad leaf profile: grows wide quickly, stays wide, then tapers slightly
        width_factor = math.sin(u * math.pi) * max_width if u < 1 else 0
        if u < 0.2: # start narrower at the stem attachment
            width_factor *= (u / 0.2)
            
        row = []
        for j in range(res_wid + 1):
            v_val = (j / res_wid) - 0.5 # width parameter [-0.5, 0.5]
            x = u * length
            y = v_val * width_factor
            # Central midrib fold: slight V-shape cross section
            z = abs(v_val) * 0.1 * (1.0 - u*0.5)
            row.append(bm.verts.new(Vector((x, y, z))))
        verts.append(row)

    for i in range(res_len):
        for j in range(res_wid):
            bm.faces.new((verts[i][j], verts[i+1][j], verts[i+1][j+1], verts[i][j+1]))

    # Apply organic bending: Outward then downward
    for v in bm.verts:
        ox, oy, oz = v.co
        # Bend the length of the leaf (x-axis) into a curve
        t = ox / length
        bend_angle = t * 1.2 # total bend angle
        v.co.z += math.sin(bend_angle) * 0.5 - (t * 0.8) # Arc up then droop down
        # The "droop" effect on the edges relative to the center
        if abs(oy) > 0.1:
            v.co.z -= t * abs(oy) * 0.4

    mesh = bpy.data.meshes.new("Leaf")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Leaf", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Positioning: Rotate around Z for distribution, and offset from center
    obj.location = Vector((0, 0, height))
    obj.rotation_euler[2] = angle
    # Tilt leaf outward slightly at the base
    obj.rotation_euler[1] = math.radians(-20)
    
    return obj

def create_cigar_shoot():
    """The tightly rolled emerging central shoot at the top."""
    bm = bmesh.new()
    segments = 16
    height = 1.8
    radius = 0.25
    
    # Create a tapered cylinder representing the rolled leaf
    verts_bot = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        verts_bot.append(bm.verts.new(Vector((math.cos(angle)*radius, math.sin(angle)*radius, 0))))
        
    verts_top = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        r_top = radius * 0.4
        verts_top.append(bm.verts.new(Vector((math.cos(angle)*r_top, math.sin(angle)*r_top, height))))
        
    for i in range(segments):
        bm.faces.new((verts_bot[i], verts_bot[(i+1)%segments], verts_top[(i+1)%segments], verts_top[i]))
        
    # Top cap
    center_top = bm.verts.new(Vector((0, 0, height)))
    for i in range(segments):
        bm.faces.new((verts_top[i], verts_top[(i+1)%segments], center_top))

    mesh = bpy.data.meshes.new("CigarShoot")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("CigarShoot", mesh)
    bpy.context.collection.objects.link(obj)
    # Position atop the stalk (stalk height is 3.5)
    obj.location = Vector((0, 0, 3.5))
    return obj

def assemble_plant():
    clear_scene()
    create_stalk()
    
    num_leaves = 8
    for i in range(num_leaves):
        # Spiral distribution: angle and height increase together
        angle = (2 * math.pi * i) / num_leaves
        h = 1.0 + (i / num_leaves) * 2.2 # Distribute from mid to top of stalk
        scale = 0.7 + (i / num_leaves) * 0.5 # Upper leaves are generally larger
        create_leaf(angle, h, scale=scale)
        
    create_cigar_shoot()

if __name__ == "__main__":
    assemble_plant()
