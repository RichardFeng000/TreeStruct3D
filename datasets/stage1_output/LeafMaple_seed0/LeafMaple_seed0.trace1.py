import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_maple_leaf():
    # 1. Define the rough outline of a maple leaf (Palmate shape)
    # Coordinates as (x, y). Maple leaves usually have 5 main lobes.
    # We define tips and the inner "valleys" between them.
    outline_points = [
        (0.0, 0.0),             # Base
        (-0.2, 0.1),            # Gap 1 (Bottom Left)
        (-1.4, 0.3),            # Tip 1 (Lower Left)
        (-0.5, 0.4),            # Gap 2
        (-1.6, 1.2),            # Tip 2 (Upper Left)
        (-0.4, 0.8),            # Gap 3
        (0.0, 2.0),             # Tip 3 (Center Top)
        (0.4, 0.8),             # Gap 4
        (1.6, 1.2),             # Tip 4 (Upper Right)
        (0.5, 0.4),             # Gap 5
        (1.4, 0.3),             # Tip 5 (Lower Right)
        (0.2, 0.1),             # Gap 6
        (0.0, 0.0),             # Close loop at base
    ]

    # Interpolate points for a smooth high-res outline
    res = 12 
    smooth_outline = []
    for i in range(len(outline_points) - 1):
        p1 = Vector(outline_points[i])
        p2 = Vector(outline_points[i+1])
        for j in range(res):
            t = j / res
            smooth_outline.append(p1.lerp(p2, t))

    # Create Mesh and BMesh
    mesh = bpy.data.meshes.new("MapleLeaf")
    obj = bpy.data.objects.new("MapleLeaf", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    # 2. Apply serration (sharp teeth) along the perimeter
    final_outline = []
    for i in range(len(smooth_outline)):
        p = smooth_outline[i]
        
        # Calculate tangent to find normal for offset
        prev_p = smooth_outline[i-1] if i > 0 else smooth_outline[-1]
        next_p = smooth_outline[(i+1)%len(smooth_outline)]
        edge_dir = (next_p - prev_p).normalized()
        normal = Vector((-edge_dir.y, edge_dir.x, 0))
        
        # Only apply serration outside the base area (stem attachment)
        if p.length > 0.3:
            # High frequency sine wave for "teeth"
            serration_amp = 0.04 * (1.0 + random.random() * 0.5)
            offset = normal * (math.sin(i * 1.2) * serration_amp)
            final_outline.append(p + offset)
        else:
            final_outline.append(p)

    # Create perimeter vertices in BMesh
    perimeter_verts = [bm.verts.new((v.x, v.y, 0)) for v in final_outline]
    
    # 3. Build the internal surface geometry (Fan method + Subdivision)
    center_vert = bm.verts.new((0, 0, 0))
    for i in range(len(perimeter_verts)):
        v1 = perimeter_verts[i]
        v2 = perimeter_verts[(i+1)%len(perimeter_verts)]
        bm.faces.new((center_vert, v1, v2))

    # Subdivide heavily to allow for organic deformations and veins
    for _ in range(4): 
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1)

    # 4. Apply Undulations, Fold, and Veins
    bm.verts.ensure_lookup_table()
    
    # Define the main veins radiating to tips
    lobe_tips = [
        Vector((-1.4, 0.3, 0)), 
        Vector((-1.6, 1.2, 0)), 
        Vector((0.0, 2.0, 0)), 
        Vector((1.6, 1.2, 0)), 
        Vector((1.4, 0.3, 0))
    ]

    for v in bm.verts:
        pos = v.co
        x, y = pos.x, pos.y
        dist_sq = x*x + y*y
        
        # Base organic curvature (center is slightly higher)
        z_base = 0.15 * math.exp(-dist_sq / 2.0)
        
        # Subtle undulating noise/waves across the leaf surface
        wave = 0.03 * math.sin(x * 3.5) * math.cos(y * 3.5)
        
        # Fold: curl the edges slightly down and bend for 3/4 perspective
        fold = 0.1 * (x**2) * 0.3 - 0.05 * dist_sq * 0.1
        
        # Vein elevation: calculate distance to lines from center to tips
        vein_contribution = 0.0
        for tip in lobe_tips:
            # Line segment (0,0) -> tip
            line_vec = tip
            # Project vertex onto line
            proj_t = (pos.dot(line_vec)) / line_vec.length_squared()
            proj_t = max(0, min(1, proj_t)) # clamp to segment
            closest_point = line_vec * proj_t
            dist_to_vein = (pos - closest_point).length
            
            if dist_to_vein < 0.1:
                # Create a ridge effect for the vein
                vein_contribution += (0.1 - dist_to_vein) * 0.8
        
        v.co.z = z_base + wave + fold + vein_contribution

    # 5. Construct the Petiole Stem
    stem_segments = 12
    stem_rings = 12
    radius = 0.06
    length = 1.8
    
    stem_verts = []
    for i in range(stem_segments + 1):
        # Vertical progress (negative Z)
        z = - (i / stem_segments) * length
        # Add a gentle curve to the stem
        x_offset = 0.25 * math.sin((i/stem_segments) * math.pi * 0.6)
        y_offset = 0.1 * (i/stem_segments)
        
        ring = []
        for j in range(stem_rings):
            angle = (j / stem_rings) * 2 * math.pi
            vx = x_offset + radius * math.cos(angle)
            vy = y_offset + radius * math.sin(angle)
            ring.append(bm.verts.new((vx, vy, z)))
        stem_verts.append(ring)

    # Build stem tube faces
    for i in range(stem_segments):
        for j in range(stem_rings):
            v1 = stem_verts[i][j]
            v2 = stem_verts[i][(j+1)%stem_rings]
            v3 = stem_verts[i+1][(j+1)%stem_rings]
            v4 = stem_verts[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    # Close the bottom of the stem (cap)
    bottom_ring = stem_verts[-1]
    bm.faces.new(bottom_ring)

    # Connect stem top to leaf base center point
    top_ring = stem_verts[0]
    for j in range(stem_rings):
        v1 = top_ring[j]
        v2 = top_ring[(j+1)%stem_rings]
        bm.faces.new((center_vert, v1, v2))

    # Finalize BMesh and Mesh
    bm.to_mesh(mesh)
    bm.free()

    # Set object rotation for a dynamic three-quarter perspective view
    obj.rotation_euler = (math.radians(-15), 0, math.radians(30))
    obj.location = (0, 0, 0)

if __name__ == "__main__":
    clear_scene()
    create_maple_leaf()
