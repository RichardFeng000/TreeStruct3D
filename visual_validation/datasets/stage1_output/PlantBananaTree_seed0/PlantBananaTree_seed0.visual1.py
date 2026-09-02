import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_banana_plant():
    # Parameters
    stem_height = 2.5
    stem_radius_bottom = 0.12
    stem_radius_top = 0.06
    leaf_length = 4.5
    leaf_width = 1.3
    res_u = 80  # Lengthwise resolution
    res_v = 40  # Widthwise resolution

    mesh = bpy.data.meshes.new("BananaPlant")
    obj = bpy.data.objects.new("BananaPlant", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # --- 1. Create Petiole (Stem) ---
    stem_segments = 12
    stem_rings = 16
    stem_verts = []
    for i in range(stem_rings):
        z = (i / (stem_rings - 1)) * stem_height
        # Tapering
        r = stem_radius_bottom + (stem_radius_top - stem_radius_bottom) * (i / (stem_rings - 1))
        # Natural curve of the stem
        offset_x = 0.15 * (z / stem_height)**2
        offset_y = 0.1 * math.sin(z * 0.8)
        
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
    # Find top center of stem for attachment
    top_ring = stem_verts[-1]
    stem_top_center = sum((Vector(v.co) for v in top_ring), Vector()) / stem_segments
    
    leaf_verts = []
    for i in range(res_u):
        u = i / (res_u - 1) # 0 to 1
        row = []
        # Leaf width varies as a function of length (oval/ellipsoid)
        width_factor = math.sin(math.pi * u)
        current_half_width = (leaf_width / 2) * width_factor
        
        for j in range(res_v):
            # v from -1 to 1 across the width
            v_coord = (j / (res_v - 1)) * 2 - 1
            
            # X: Length of leaf, following a gentle arch
            x_pos = u * leaf_length
            y_pos = v_coord * current_half_width
            
            # Z: Height and curvature
            # A: Arching downwards from the stem top
            z_arch = -1.2 * (u**2) + 0.5 * math.sin(math.pi * u)
            
            # B: Prominent midrib (central ridge)
            midrib_strength = 0.12
            dist_from_center = abs(v_coord)
            z_midrib = midrib_strength * math.exp(-dist_from_center * 5) * (1 - u*0.5)
            
            # C: Fine parallel venation (longitudinal ridges)
            # We create a subtle sine wave across the width to simulate parallel veins
            venation_freq = 15
            venation_amp = 0.02
            z_veins = venation_amp * math.sin(v_coord * venation_freq * math.pi) * (u**0.5)
            
            # D: Longitudinal fold (cylindrical curve of the leaf blade)
            z_fold = 0.15 * (v_coord**2) * (1 - u)

            final_x = stem_top_center.x + x_pos + 0.1 * u # Slight extension from stem
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

    # Bridge stem top to leaf base for connectivity
    # Connect the first row of leaf vertices to a few points on the stem's top ring
    for j in range(res_v):
        v_leaf = leaf_verts[0][j]
        # Find nearest vertex on stem top ring to avoid overlaps
        v_stem = top_ring[int(( (j / (res_v - 1)) * stem_segments )) % stem_segments]
        bm.edges.new((v_leaf, v_stem))

    bm.to_mesh(mesh)
    bm.free()

    # Final Polish: Smooth shading and slight thickness simulation via modifiers
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
    
    solidify = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify.thickness = 0.015
    
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1

def main():
    clear_scene()
    create_banana_plant()

if __name__ == "__main__":
    main()
