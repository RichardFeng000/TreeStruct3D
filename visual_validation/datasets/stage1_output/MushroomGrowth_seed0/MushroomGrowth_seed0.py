import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_mushroom():
    # Parameters for a "thick" stem and "broad" cap
    stem_radius_bottom = 0.35
    stem_radius_top = 0.22
    stem_height = 1.8
    stem_segments = 24
    stem_rings = 32
    
    cap_radius = 1.3
    cap_height = 0.6
    cap_segments = 32
    cap_rings = 20

    # Create a single BMesh for the entire mushroom to avoid alignment gaps
    bm = bmesh.new()

    # --- Stem Creation (Curved and Bumpy) ---
    stem_verts = []
    for i in range(stem_rings + 1):
        t = i / stem_rings
        z = t * stem_height
        
        # Curve: Shift X as it goes up to create an organic arc
        # Starts tilted at base (x offset starts moving immediately)
        curve_offset = 0.5 * math.sin(t * math.pi * 0.6) + (0.2 * t**2)
        
        # Radius interpolation
        r_base = stem_radius_bottom + (stem_radius_top - stem_radius_bottom) * t
        
        ring_verts = []
        for j in range(stem_segments):
            angle = (j / stem_segments) * 2 * math.pi
            # Add noise for "rough bumpy" surface
            noise = random.uniform(-0.06, 0.06) * (1.0 - 0.5 * t) # More bump at base
            r = r_base + noise
            
            x = curve_offset + r * math.cos(angle)
            y = r * math.sin(angle)
            # Slight Z-jitter for organic look
            z_jitter = random.uniform(-0.02, 0.02) if i > 0 and i < stem_rings else 0
            ring_verts.append(bm.verts.new((x, y, z + z_jitter)))
        stem_verts.append(ring_verts)

    # Stem faces
    for i in range(stem_rings):
        for j in range(stem_segments):
            v1 = stem_verts[i][j]
            v2 = stem_verts[i][(j + 1) % stem_segments]
            v3 = stem_verts[i + 1][(j + 1) % stem_segments]
            v4 = stem_verts[i + 1][j]
            bm.faces.new((v1, v2, v3, v4))

    # Stem base cap
    bm.faces.new([stem_verts[0][j] for j in range(stem_segments)])

    # --- Cap Creation (Broad and Organic) ---
    # Position the cap at the top center of the stem
    top_ring = stem_verts[-1]
    center_top = sum((v.co for v in top_ring), Vector((0, 0, 0))) / len(top_ring)
    
    cap_verts = []
    for i in range(cap_rings + 1):
        # Phi from 0 (top center) to pi/2 (bottom edge)
        phi = (i / cap_rings) * (math.pi / 2)
        
        r_current = cap_radius * math.sin(phi)
        z_offset = cap_height * math.cos(phi)
        
        ring_verts = []
        for j in range(cap_segments):
            theta = (j / cap_segments) * 2 * math.pi
            
            # Organic surface detail: noise on radius and height
            noise_r = random.uniform(0.9, 1.1) if i > 0 else 1.0
            noise_z = random.uniform(-0.04, 0.04) if i > 0 else 0
            
            x = center_top.x + r_current * math.cos(theta) * noise_r
            y = center_top.y + r_current * math.sin(theta) * noise_r
            # Cap builds "downward" relative to top vertex if we use cos from pi/2 back to 0,
            # but here z_offset goes from cap_height down to 0.
            # We want the bottom of the dome (i=cap_rings) to be at center_top.z
            # So we shift by -cap_height effectively.
            z = center_top.z + (z_offset - cap_height) + noise_z
            
            ring_verts.append(bm.verts.new((x, y, z)))
        cap_verts.append(ring_verts)

    # Cap faces (Dome)
    for i in range(cap_rings):
        for j in range(cap_segments):
            v1 = cap_verts[i][j]
            v2 = cap_verts[i][(j + 1) % cap_segments]
            v3 = cap_verts[i + 1][(j + 1) % cap_segments]
            v4 = cap_verts[i + 1][j]
            bm.faces.new((v1, v2, v3, v4))

    # Cap bottom face (Connecting it to the stem top)
    # We bridge the gap between the cap's lowest ring and the stem's top ring
    bottom_cap_ring = cap_verts[-1]
    top_stem_ring = stem_verts[-1]
    for j in range(stem_segments): # Use stem segments for bridging
        # Map indices if they differ, but here we can interpolate or just bridge closest
        idx_c = int((j / stem_segments) * cap_segments)
        idx_c_next = int(((j + 1) / stem_segments) * cap_segments) % cap_segments
        
        v1 = top_stem_ring[j]
        v2 = top_stem_ring[(j + 1) % stem_segments]
        v3 = bottom_cap_ring[idx_c_next]
        v4 = bottom_cap_ring[idx_c]
        try:
            bm.faces.new((v1, v2, v3, v4))
        except:
            pass

    # Finalize mesh
    mesh = bpy.data.meshes.new("Mushroom")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Mushroom", mesh)
    bpy.context.collection.objects.link(obj)

    # Tilt the entire assembly at the base for "growing" look
    obj.rotation_euler[1] = math.radians(15)

    # Smooth and Subdiv
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    
    for poly in obj.data.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    clear_scene()
    create_mushroom()
