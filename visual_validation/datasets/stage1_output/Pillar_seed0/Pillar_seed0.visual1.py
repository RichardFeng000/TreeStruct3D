import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def apply_weathering(bm, intensity=0.02, chip_chance=0.1, chip_intensity=0.08):
    """Applies random jitter and simulates chipped edges on a bmesh."""
    for v in bm.verts:
        # General erosion/wear
        v.co += Vector((random.uniform(-intensity, intensity), 
                        random.uniform(-intensity, intensity), 
                        random.uniform(-intensity, intensity)))
        
        # Simulate occasional larger chips or cracks on corners
        if random.random() < chip_chance:
            chip = Vector((random.uniform(-chip_intensity, chip_intensity), 
                          random.uniform(-chip_intensity, chip_intensity), 
                          random.uniform(-chip_intensity, chip_intensity)))
            v.co += chip

def create_plinth():
    """Creates a stepped rectangular base (plinth) with weathering."""
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
        
        bm.faces.new((v0, v1, v5, v4)) 
        bm.faces.new((v1, v2, v6, v5)) 
        bm.faces.new((v2, v3, v7, v6)) 
        bm.faces.new((v3, v0, v4, v7)) 
        bm.faces.new((v4, v5, v6, v7)) 
        bm.faces.new((v0, v3, v2, v1)) 
        
        current_z += h

    apply_weathering(bm)

    bm.to_mesh(plinth_mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Plinth", plinth_mesh)
    bpy.context.collection.objects.link(obj)
    return obj, current_z

def create_fluted_shaft(start_z):
    """Creates a cylindrical shaft with concave grooves and subtle weathering."""
    height = 6.0
    base_radius = 0.35
    flutes = 24
    depth = 0.07 # Increased depth for better visibility
    res_per_flute = 4 
    segments = 40 # Higher vertical resolution for smoother entasis/wear
    seg_height = height / segments
    
    bm = bmesh.new()
    
    def create_ring(z, scale):
        ring_verts = []
        for i in range(flutes):
            angle_start = (2 * math.pi * i) / flutes
            angle_end = (2 * math.pi * (i + 1)) / flutes
            
            for j in range(res_per_flute):
                t = j / (res_per_flute - 1)
                angle = angle_start + t * (angle_end - angle_start)
                # Concave dip for the fluting
                current_r = base_radius - (depth * (1 - abs(math.cos(math.pi * t))))
                x = math.cos(angle) * current_r * scale
                y = math.sin(angle) * current_r * scale
                # Add very slight organic jitter to shaft for weathering
                jitter = 0.005
                v = bm.verts.new((x + random.uniform(-jitter, jitter), 
                                  y + random.uniform(-jitter, jitter), z))
                ring_verts.append(v)
        return ring_verts

    all_rings = []
    for s in range(segments + 1):
        z = start_z + (s * seg_height)
        t = s / segments
        bulge = 1.0 + 0.04 * math.sin(math.pi * t) # Entasis bulge
        all_rings.append(create_ring(z, bulge))

    for s in range(segments):
        r_bot = all_rings[s]
        r_top = all_rings[s+1]
        num_v = len(r_bot)
        for i in range(num_v):
            bm.faces.new((r_bot[i], r_bot[(i + 1) % num_v], r_top[(i + 1) % num_v], r_top[i]))

    # Top and bottom caps
    bm.faces.new(all_rings[0]) 
    bm.faces.new(all_rings[-1][::-1]) 

    mesh = bpy.data.meshes.new("ShaftMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("PillarShaft", mesh)
    bpy.context.collection.objects.link(obj)
    return obj, height

def create_capital(start_z):
    """Creates a decorative capital with an echinus and abacus, weathered."""
    echinus_radius_bot = 0.38
    echinus_radius_top = 0.48
    echinus_height = 0.4
    res = 32
    
    bm = bmesh.new()
    
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

    # Abacus (Flat square slab)
    abacus_size = 0.85
    abacus_height = 0.2
    z_base = start_z + echinus_height
    s_half = abacus_size / 2
    
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

    apply_weathering(bm)

    mesh = bpy.data.meshes.new("CapitalMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("PillarCapital", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def main():
    clear_scene()
    
    plinth_obj, z_after_base = create_plinth()
    shaft_obj, shaft_height = create_fluted_shaft(z_after_base)
    capital_obj = create_capital(z_after_base + shaft_height)
    
    bpy.ops.object.select_all(action='DESELECT')
    plinth_obj.select_set(True)
    shaft_obj.select_set(True)
    capital_obj.select_set(True)
    bpy.context.view_layer.objects.active = shaft_obj
    bpy.ops.object.join()
    
    final_pillar = bpy.context.active_object
    final_pillar.name = "ClassicalPillar"
    
    # Bevel adds to the weathered look by softening edges slightly
    bevel = final_pillar.modifiers.new(name="WeatheringBevel", type='BEVEL')
    bevel.width = 0.01
    bevel.segments = 2
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = math.radians(30)

if __name__ == "__main__":
    main()
