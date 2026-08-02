import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_plinth():
    """Creates a stepped rectangular base (plinth)."""
    steps = [
        {"w": 1.2, "d": 1.2, "h": 0.3}, # Bottom step
        {"w": 1.0, "d": 1.0, "h": 0.2}, # Middle step
        {"w": 0.8, "d": 0.8, "h": 0.15} # Top step
    ]
    
    current_z = 0
    plinth_mesh = bpy.data.meshes.new("PlinthMesh")
    bm = bmesh.new()
    
    for dim in steps:
        # Create a cube for each step using BMesh
        w, d, h = dim["w"], dim["d"], dim["h"]
        # Vertices for the current box
        v0 = bm.verts.new((-w/2, -d/2, current_z))
        v1 = bm.verts.new((w/2, -d/2, current_z))
        v2 = bm.verts.new((w/2, d/2, current_z))
        v3 = bm.verts.new((-w/2, d/2, current_z))
        
        v4 = bm.verts.new((-w/2, -d/2, current_z + h))
        v5 = bm.verts.new((w/2, -d/2, current_z + h))
        v6 = bm.verts.new((w/2, d/2, current_z + h))
        v7 = bm.verts.new((-w/2, d/2, current_z + h))
        
        bm.faces.new((v0, v1, v5, v4)) # side 1
        bm.faces.new((v1, v2, v6, v5)) # side 2
        bm.faces.new((v2, v3, v7, v6)) # side 3
        bm.faces.new((v3, v0, v4, v7)) # side 4
        bm.faces.new((v4, v5, v6, v7)) # top
        bm.faces.new((v0, v3, v2, v1)) # bottom
        
        current_z += h

    # Weathering: slight vertex perturbation
    for v in bm.verts:
        v.co += Vector((random.uniform(-0.015, 0.015), 
                        random.uniform(-0.015, 0.015), 
                        random.uniform(-0.01, 0.01)))

    bm.to_mesh(plinth_mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Plinth", plinth_mesh)
    bpy.context.collection.objects.link(obj)
    return obj, current_z

def create_fluted_shaft(start_z):
    """Creates a cylindrical shaft with vertical concave grooves (fluting)."""
    height = 6.0
    radius = 0.35
    flutes = 24
    depth = 0.04 # Depth of the groove
    res_per_flute = 4 # Resolution for the curve of each flute
    
    bm = bmesh.new()
    
    # Create a circular profile with concave fluting
    verts = []
    for i in range(flutes):
        angle_start = (2 * math.pi * i) / flutes
        angle_end = (2 * math.pi * (i + 1)) / flutes
        
        # Create the concave segment for each flute
        for j in range(res_per_flute):
            t = j / (res_per_flute - 1)
            angle = angle_start + t * (angle_end - angle_start)
            
            # Use a cosine function to create the "dip" of the flute
            # The dip is deepest at the center of each segment
            dip_factor = math.cos(math.pi * t) # 1 at start/end, -1 at middle
            # We want it pushed in at the middle: flip and scale
            current_r = radius - (depth * (0.5 * (1 - dip_factor)))
            
            x = math.cos(angle) * current_r
            y = math.sin(angle) * current_r
            verts.append(bm.verts.new((x, y, start_z)))

    # Connect vertices into a loop
    for i in range(len(verts)):
        bm.edges.new((verts[i], verts[(i + 1) % len(verts)]))
    
    bm.faces.new(verts)
    
    # Extrude upwards with entasis (subtle bulge)
    segments = 20
    seg_height = height / segments
    
    for s in range(segments):
        bm.faces.ensure_lookup_table()
        # The most recently created face is the top one
        last_face = bm.faces[-1]
        
        extrude_result = bmesh.ops.extrude_face_region(bm, geom=[last_face])
        verts_new = [v for v in extrude_result['geom'] if isinstance(v, bmesh.types.BVVert)]
        
        # Entasis calculation: max bulge at ~1/3 height
        t = (s + 1) / segments
        bulge = 0.025 * math.sin(math.pi * t)
        
        for v in verts_new:
            v.co.z += seg_height
            # Push outwards from center based on bulge
            dir_vec = Vector((v.co.x, v.co.y, 0)).normalized()
            v.co += dir_vec * bulge

    mesh = bpy.data.meshes.new("ShaftMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("PillarShaft", mesh)
    bpy.context.collection.objects.link(obj)
    return obj, height

def create_capital(start_z):
    """Creates a decorative capital consisting of an echinus and abacus."""
    # Echinus (rounded transition)
    echinus_radius_bot = 0.38
    echinus_radius_top = 0.48
    echinus_height = 0.35
    res = 32
    
    bm = bmesh.new()
    
    # Bottom circle (start of capital)
    verts_bot = []
    for i in range(res):
        angle = (2 * math.pi * i) / res
        verts_bot.append(bm.verts.new((math.cos(angle)*echinus_radius_bot, 
                                      math.sin(angle)*echinus_radius_bot, 
                                      start_z)))
    
    # Top circle (top of echinus)
    verts_top = []
    for i in range(res):
        angle = (2 * math.pi * i) / res
        verts_top.append(bm.verts.new((math.cos(angle)*echinus_radius_top, 
                                      math.sin(angle)*echinus_radius_top, 
                                      start_z + echinus_height)))
    
    # Create faces for the rounded transition (echinus)
    for i in range(res):
        v1 = verts_bot[i]
        v2 = verts_bot[(i+1)%res]
        v3 = verts_top[(i+1)%res]
        v4 = verts_top[i]
        bm.faces.new((v1, v2, v3, v4))

    # Abacus (Flat square slab)
    abacus_size = 0.7
    abacus_height = 0.15
    z_base = start_z + echinus_height
    s = abacus_size / 2
    
    c1 = bm.verts.new((-s, -s, z_base))
    c2 = bm.verts.new((s, -s, z_base))
    c3 = bm.verts.new((s, s, z_base))
    c4 = bm.verts.new((-s, s, z_base))
    
    # Bottom face of abacus (connect it to the top circle for manifoldness if possible)
    bm.faces.new((c1, c2, c3, c4))
    
    # Extrude Abacus upwards
    ext = bmesh.ops.extrude_face_region(bm, geom=[bm.faces[-1]])
    v_top_corners = [v for v in ext['geom'] if isinstance(v, bmesh.types.BVVert)]
    for v in v_top_corners:
        v.co.z += abacus_height

    # Connect the top circle of echinus to bottom square of abacus (simple bridge)
    # For a high-fidelity model, we'd do more complex triangulation here
    
    mesh = bpy.data.meshes.new("CapitalMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("PillarCapital", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def main():
    clear_scene()
    
    # 1. Create Plinth (Base)
    plinth_obj, z_after_base = create_plinth()
    
    # 2. Create Shaft
    shaft_obj, shaft_height = create_fluted_shaft(z_after_base)
    
    # 3. Create Capital
    capital_obj = create_capital(z_after_base + shaft_height)
    
    # Join all parts into a single object for the final result
    bpy.ops.object.select_all(action='DESELECT')
    plinth_obj.select_set(True)
    shaft_obj.select_set(True)
    capital_obj.select_set(True)
    bpy.context.view_layer.objects.active = shaft_obj
    bpy.ops.object.join()
    
    final_pillar = bpy.context.active_object
    final_pillar.name = "ClassicalPillar"
    
    # Apply a Bevel modifier to all edges for weathering and realistic lighting
    bevel = final_pillar.modifiers.new(name="WeatheringBevel", type='BEVEL')
    bevel.width = 0.004
    bevel.segments = 2
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = math.radians(30)

if __name__ == "__main__":
    main()
