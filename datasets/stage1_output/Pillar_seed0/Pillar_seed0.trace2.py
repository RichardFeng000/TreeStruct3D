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
    """Creates a stepped rectangular base (plinth) with slight weathering jitter."""
    steps = [
        {"w": 1.2, "d": 1.2, "h": 0.3}, # Bottom step
        {"w": 1.0, "d": 1.0, "h": 0.2}, # Middle step
        {"w": 0.8, "d": 0.8, "h": 0.15} # Top step
    ]
    
    current_z = 0
    plinth_mesh = bpy.data.meshes.new("PlinthMesh")
    bm = bmesh.new()
    
    for dim in steps:
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

    # Weathering: slight vertex perturbation for a worn look
    for v in bm.verts:
        v.co += Vector((random.uniform(-0.01, 0.01), 
                        random.uniform(-0.01, 0.01), 
                        random.uniform(-0.005, 0.005)))

    bm.to_mesh(plinth_mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Plinth", plinth_mesh)
    bpy.context.collection.objects.link(obj)
    return obj, current_z

def create_fluted_shaft(start_z):
    """Creates a cylindrical shaft with vertical concave grooves and entasis."""
    height = 6.0
    base_radius = 0.35
    flutes = 24
    depth = 0.04 # Depth of the flute groove
    res_per_flute = 4 
    segments = 30
    seg_height = height / segments
    
    bm = bmesh.new()
    
    # Helper to create a fluted ring at a specific Z and radius scale
    def create_ring(z, scale):
        ring_verts = []
        for i in range(flutes):
            angle_start = (2 * math.pi * i) / flutes
            angle_end = (2 * math.pi * (i + 1)) / flutes
            
            for j in range(res_per_flute):
                t = j / (res_per_flute - 1)
                angle = angle_start + t * (angle_end - angle_start)
                # Concave dip: cosine function creates a curve that dips inward
                dip = depth * (0.5 * (1 + math.cos(math.pi * (t*2-1)))) if res_per_flute > 1 else 0
                # Simple approach for concave effect: center of segment is pushed in
                current_r = base_radius - (depth * (1 - abs(math.cos(math.pi * t))))
                
                x = math.cos(angle) * current_r * scale
                y = math.sin(angle) * current_r * scale
                ring_verts.append(bm.verts.new((x, y, z)))
        return ring_verts

    # Create the rings along the height to implement Entasis
    all_rings = []
    for s in range(segments + 1):
        z = start_z + (s * seg_height)
        # Entasis: subtle bulge. Max at approx 1/3 of shaft height
        t = s / segments
        bulge = 1.0 + 0.05 * math.sin(math.pi * t)
        all_rings.append(create_ring(z, bulge))

    # Bridge the rings to create the vertical faces
    for s in range(segments):
        r_bot = all_rings[s]
        r_top = all_rings[s+1]
        num_v = len(r_bot)
        for i in range(num_v):
            bm.faces.new((r_bot[i], r_bot[(i + 1) % num_v], r_top[(i + 1) % num_v], r_top[i]))

    # Caps for the cylinder (Top and Bottom)
    bm.faces.new(all_rings[0]) # bottom cap (reversed order if needed, but not critical here)
    bm.faces.new(all_rings[-1][::-1]) # top cap

    mesh = bpy.data.meshes.new("ShaftMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("PillarShaft", mesh)
    bpy.context.collection.objects.link(obj)
    return obj, height

def create_capital(start_z):
    """Creates a decorative capital consisting of an echinus and abacus."""
    # 1. Echinus (The rounded transition piece)
    echinus_radius_bot = 0.38
    echinus_radius_top = 0.48
    echinus_height = 0.4
    res = 32
    
    bm = bmesh.new()
    
    # Create rounded transition
    verts_bot = []
    for i in range(res):
        angle = (2 * math.pi * i) / res
        verts_bot.append(bm.verts.new((math.cos(angle)*echinus_radius_bot, 
                                      math.sin(angle)*echinus_radius_bot, 
                                      start_z)))
    
    verts_top = []
    for i in range(res):
        angle = (2 * math.pi * i) / res
        verts_top.append(bm.verts.new((math.cos(angle)*echinus_radius_top, 
                                      math.sin(angle)*echinus_radius_top, 
                                      start_z + echinus_height)))
    
    for i in range(res):
        bm.faces.new((verts_bot[i], verts_bot[(i+1)%res], verts_top[(i+1)%res], verts_top[i]))

    # 2. Abacus (Flat square slab)
    abacus_size = 0.8
    abacus_height = 0.2
    z_base = start_z + echinus_height
    s_half = abacus_size / 2
    
    # Create a cube for the abacus
    v0 = bm.verts.new((-s_half, -s_half, z_base))
    v1 = bm.verts.new((s_half, -s_half, z_base))
    v2 = bm.verts.new((s_half, s_half, z_base))
    v3 = bm.verts.new((-s_half, s_half, z_base))
    
    v4 = bm.verts.new((-s_half, -s_half, z_base + abacus_height))
    v5 = bm.verts.new((s_half, -s_half, z_base + abacus_height))
    v6 = bm.verts.new((s_half, s_half, z_base + abacus_height))
    v7 = bm.verts.new((-s_half, s_half, z_base + abacus_height))
    
    bm.faces.new((v0, v1, v5, v4)) 
    bm.faces.new((v1, v2, v6, v5)) 
    bm.faces.new((v2, v3, v7, v6)) 
    bm.faces.new((v3, v0, v4, v7)) 
    bm.faces.new((v4, v5, v6, v7)) 
    bm.faces.new((v0, v3, v2, v1))

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
    
    # Apply a Bevel modifier to simulate weathered edges and realistic lighting
    bevel = final_pillar.modifiers.new(name="WeatheringBevel", type='BEVEL')
    bevel.width = 0.005
    bevel.segments = 2
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = math.radians(30)

if __name__ == "__main__":
    main()
