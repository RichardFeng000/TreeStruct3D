import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_banana_plant():
    # Parameters
    stem_height = 2.8
    stem_radius_bottom = 0.15
    stem_radius_top = 0.08
    leaf_length = 5.0
    leaf_width = 1.6
    res_u = 100  # Lengthwise resolution (higher for midrib detail)
    res_v = 60   # Widthwise resolution (higher for venation)

    mesh = bpy.data.meshes.new("BananaPlant")
    obj = bpy.data.objects.new("BananaPlant", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # --- 1. Create Petiole (Stem) ---
    stem_segments = 16
    stem_rings = 20
    stem_verts = []
    for i in range(stem_rings):
        z = (i / (stem_rings - 1)) * stem_height
        r = stem_radius_bottom + (stem_radius_top - stem_radius_bottom) * (i / (stem_rings - 1))
        # Natural subtle curve
        offset_x = 0.2 * math.sin(z * 0.5)
        offset_y = 0.1 * (z / stem_height)**2
        
        ring_verts = []
        for j in range(stem_segments):
            angle = (j / stem_segments) * 2 * math.pi
            v = bm.verts.new((offset_x + r * math.cos(angle), offset_y + r * math.sin(angle), z))
            ring_verts.append(v)
        stem_verts.append(ring_verts)

    for i in range(stem_rings - 1):
        for j in range(stem_segments):
            v1 = stem_verts[i][j]
            v2 = stem_verts[i][(j + 1) % stem_segments]
            v3 = stem_verts[i+1][(j + 1) % stem_segments]
            v4 = stem_verts[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    # --- 2. Create Leaf Blade ---
    top_ring = stem_verts[-1]
    stem_top_center = sum((Vector(v.co) for v in top_ring), Vector()) / stem_segments
    
    leaf_verts = []
    for i in range(res_u):
        u = i / (res_u - 1) # 0 to 1
        row = []
        # Leaf width: oval shape
        width_factor = math.sin(math.pi * u)
        current_half_width = (leaf_width / 2) * width_factor
        
        for j in range(res_v):
            # v from -1 to 1 across the width
            v_coord = (j / (res_v - 1)) * 2 - 1
            
            # X: Length of leaf, following a gentle arch
            x_pos = u * leaf_length
            y_pos = v_coord * current_half_width
            
            # Z: Height and curvature (arch)
            z_arch = -2.0 * (u**2) + 1.5 * u # Quadratic arch peaking then dropping
            
            # Prominent Midrib: a strong central ridge
            midrib_strength = 0.25
            dist_from_center = abs(v_coord)
            # Use a sharper peak for the midrib (Lorentzian-like shape)
            z_midrib = midrib_strength / (1 + dist_from_center * 12) * (1 - u*0.3)
            
            # Fine parallel venation: visible ribs along length
            venation_freq = 18
            venation_amp = 0.05 # Increased for visibility
            z_veins = venation_amp * math.sin(v_coord * venation_freq) * (u**0.7)
            
            # Longitudinal fold: the leaf curves slightly like a trough
            z_fold = 0.2 * (v_coord**2) * (1 - u*0.5)

            final_x = stem_top_center.x + x_pos + 0.1 * u
            final_y = stem_top_center.y + y_pos
            final_z = stem_top_center.z + z_arch + z_midrib + z_veins + z_fold
            
            row.append(bm.verts.new((final_x, final_y, final_z)))
        leaf_verts.append(row)

    for i in range(res_u - 1):
        for j in range(res_v - 1):
            bm.faces.new((
                leaf_verts[i][j], 
                leaf_verts[i+1][j], 
                leaf_verts[i+1][j+1], 
                leaf_verts[i][j+1]
            ))

    # Connection: bridge leaf base to stem top
    for j in range(res_v):
        v_leaf = leaf_verts[0][j]
        idx = int(( (j / (res_v - 1)) * stem_segments )) % stem_segments
        v_stem = top_ring[idx]
        bm.edges.new((v_leaf, v_stem))

    bm.to_mesh(mesh)
    bm.free()

    # Polish
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
    
    solidify = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify.thickness = 0.02
    
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1

def main():
    clear_scene()
    create_banana_plant()

if __name__ == "__main__":
    main()
