import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_vase():
    # --- Parameters ---
    height = 6.0
    segments_h = 64  # Vertical resolution
    segments_v = 128 # Circumference resolution
    num_ridges = 24   # Number of vertical flutes
    
    # Profile points: (radius, z)
    profile = [
        (0.0, 0.0),     # Center bottom
        (1.5, 0.1),     # Base edge
        (2.8, 2.0),     # Bulbous belly
        (0.8, 4.0),     # Neck
        (1.6, 5.5),     # Flared rim top
    ]

    def get_profile_radius(z):
        """Interpolates radius based on height z."""
        for i in range(len(profile) - 1):
            r1, z1 = profile[i]
            r2, z2 = profile[i+1]
            if z1 <= z <= z2:
                t = (z - z1) / (z2 - z1)
                return r1 + t * (r2 - r1)
        return profile[-1][0]

    def get_flute_amplitude(z):
        """Calculates the strength of fluting at height z."""
        # Fluting is strongest in the bulbous part, weaker at neck and rim
        if z < 0.5: return 0.05 * (z / 0.5) # Fade in from bottom
        if z > 4.0: return 0.1 * (1.0 - (z - 4.0) / (5.5 - 4.0)) # Fade out at top
        # Bell curve centered around the bulbous part (z=2.0)
        return 0.3 * math.exp(-((z - 2.0)**2) / 2.0)

    # --- Create Vase Mesh ---
    mesh = bpy.data.meshes.new("VaseMesh")
    obj = bpy.data.objects.new("DecorativeVase", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # Generate vertices in rings
    rings = []
    for i in range(segments_h + 1):
        z = (i / segments_h) * height
        r_base = get_profile_radius(z)
        amp = get_flute_amplitude(z)
        
        current_ring = []
        for j in range(segments_v):
            theta = (j / segments_v) * 2 * math.pi
            
            # Create fluting using a cosine wave for smooth ridges
            # We use cos(num_ridges * theta) to create the peaks and valleys
            flute_offset = amp * math.cos(num_ridges * theta)
            r = r_base + flute_offset
            
            # Special handling for scalloped base (bottom ring)
            if i == 0:
                # The very center bottom is a single point, but our loop creates a ring.
                # We'll collapse this later or handle it here.
                r = 0.0
            elif i == 1:
                # Scalloped effect at the base
                scallop_amp = 0.2
                r += scallop_amp * math.cos(num_ridges * theta)

            x = r * math.cos(theta)
            y = r * math.sin(theta)
            v = bm.verts.new(Vector((x, y, z)))
            current_ring.append(v)
        rings.append(current_ring)

    # Merge bottom ring into a single vertex to close the mesh
    bottom_vert = bm.verts.new(Vector((0, 0, 0)))
    for v in rings[0]:
        bm.verts.remove(v)
    rings[0] = [bottom_vert] * segments_v

    # Create faces
    for i in range(segments_h):
        for j in range(segments_v):
            v1 = rings[i][j]
            v2 = rings[i][(j + 1) % segments_v]
            v3 = rings[i+1][(j + 1) % segments_v]
            v4 = rings[i+1][j]
            
            # Avoid creating degenerate faces at the bottom point
            if v1 != v2:
                bm.faces.new((v1, v2, v3, v4))

    # Close the top rim (the flared opening)
    # We leave it open as a vase usually is, but we can add thickness with a modifier later.
    # To make the "rim" look like glass, we ensure high resolution.
    
    bm.to_mesh(mesh)
    bm.free()

    # --- Ornamental Ring at Base ---
    # A rough torus-like ring around the bottom
    ring_mesh = bpy.data.meshes.new("OrnamentRing")
    ring_obj = bpy.data.objects.new("OrnamentRing", ring_mesh)
    bpy.context.collection.objects.link(ring_obj)
    
    bm_ring = bmesh.new()
    # Create a torus by sweeping a small circle along a large circle
    major_r = 1.6
    minor_r = 0.15
    res_major = 64
    res_minor = 12
    
    for i in range(res_major):
        theta = (i / res_major) * 2 * math.pi
        cx = major_r * math.cos(theta)
        cy = major_r * math.sin(theta)
        
        ring_slice = []
        for j in range(res_minor):
            phi = (j / res_minor) * 2 * math.pi
            # Offset the torus slightly above z=0
            # Add "roughness" by jittering vertices
            jitter = random.uniform(-0.03, 0.03)
            
            lx = minor_r * math.cos(phi) + jitter
            ly = 0 # Fixed plane for the cross-section slice relative to center
            lz = minor_r * math.sin(phi) + 0.15 + jitter
            
            # Rotate local coords to align with the torus path
            vx = cx + lx * math.cos(theta)
            vy = cy + lx * math.sin(theta)
            vz = lz
            
            v = bm_ring.verts.new(Vector((vx, vy, vz)))
            ring_slice.append(v)
        rings_data = ring_slice # reuse var name for brevity
        
        # Connect slice to previous slice
        if i > 0:
            prev_slice = rings_prev
            for k in range(res_minor):
                bm_ring.faces.new((
                    prev_slice[k], 
                    ring_slice[k], 
                    ring_slice[(k+1)%res_minor], 
                    prev_slice[(k+1)%res_minor]
                ))
        rings_prev = ring_slice

    # Close the torus loop
    prev_slice = rings_prev # This is the last slice
    # The first slice was not saved, let's rebuild logic or just save it.
    # Since we are in a script, I'll simply restart the ring creation with an array for slices.

    bm_ring.free()
    # Let's redo the torus properly using BMesh operators to avoid index errors
    bm_ring = bmesh.new()
    bmesh.ops.create_circle(bm_ring, segments=res_major, radius=major_r)
    # This only creates vertices. We want a volume. 
    # Using the simple method: build it from scratch again but store slices.

def create_ornamental_ring():
    major_r = 1.6
    minor_r = 0.12
    res_major = 80
    res_minor = 16
    
    mesh = bpy.data.meshes.new("OrnamentRing")
    obj = bpy.data.objects.new("OrnamentRing", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    
    slices = []
    for i in range(res_major):
        theta = (i / res_major) * 2 * math.pi
        cx, cy = major_r * math.cos(theta), major_r * math.sin(theta)
        
        current_slice = []
        for j in range(res_minor):
            phi = (j / res_minor) * 2 * math.pi
            # Add roughness/ornamentation via sin waves and random noise
            roughness = 0.05 * math.sin(10 * theta) + random.uniform(-0.02, 0.02)
            r_eff = minor_r + roughness
            
            vx = cx + r_eff * math.cos(phi) * math.cos(theta)
            vy = cy + r_eff * math.cos(phi) * math.sin(theta)
            vz = 0.2 + r_eff * math.sin(phi) # Lifted off ground
            
            v = bm.verts.new(Vector((vx, vy, vz)))
            current_slice.append(v)
        slices.append(current_slice)

    for i in range(res_major):
        s1 = slices[i]
        s2 = slices[(i + 1) % res_major]
        for j in range(res_minor):
            bm.faces.new((s1[j], s1[(j+1)%res_minor], s2[(j+1)%res_minor], s2[j]))

    bm.to_mesh(mesh)
    bm.free()
    return obj

def apply_modifiers(obj):
    # Add Subdivision Surface for smoothness
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    # Shade smooth
    for poly in obj.data.polygons:
        poly.use_smooth = True

def main():
    clear_scene()
    
    # Create Vase Body
    vase_obj = create_vase() # This function was logic-heavy, let's ensure it works
    
    # Since I defined the vase body in a separate block above but didn't return obj 
    # (I just linked it), I will call a refined version.

def execute():
    clear_scene()
    
    # --- Vase Body Construction ---
    height = 6.0
    segments_h, segments_v = 64, 128
    num_ridges = 24
    profile = [(0.0, 0.0), (1.5, 0.1), (2.8, 2.0), (0.8, 4.0), (1.6, 5.5)]

    def get_r(z):
        for i in range(len(profile)-1):
            r1, z1 = profile[i]; r2, z2 = profile[i+1]
            if z1 <= z <= z2: return r1 + (z-z1)/(z2-z1)*(r2-r1)
        return profile[-1][0]

    def get_amp(z):
        if z < 0.5: return 0.05 * (z / 0.5)
        if z > 4.0: return 0.1 * (1.0 - (z-4.0)/(5.5-4.0))
        return 0.3 * math.exp(-((z-2.0)**2)/2.0)

    mesh = bpy.data.meshes.new("VaseBody")
    vase_obj = bpy.data.objects.new("Vase", mesh)
    bpy.context.collection.objects.link(vase_obj)
    bm = bmesh.new()
    
    rings = []
    for i in range(segments_h + 1):
        z = (i / segments_h) * height
        r_base, amp = get_r(z), get_amp(z)
        current_ring = []
        for j in range(segments_v):
            theta = (j/segments_v)*2*math.pi
            r = r_base + amp * math.cos(num_ridges * theta)
            if i == 0: r = 0.0
            elif i == 1: r += 0.2 * math.cos(num_ridges * theta) # Scalloping base
            current_ring.append(bm.verts.new(Vector((r*math.cos(theta), r*math.sin(theta), z))))
        rings.append(current_ring)

    # Bottom point merge
    bottom_v = rings[0][0]
    for v in rings[0][1:]:
        bm.verts.remove(v)
    rings[0] = [bottom_v] * segments_v

    for i in range(segments_h):
        for j in range(segments_v):
            v1, v2 = rings[i][j], rings[i][(j+1)%segments_v]
            v3, v4 = rings[i+1][(j+1)%segments_v], rings[i+1][j]
            if v1 != v2: bm.faces.new((v1, v2, v3, v4))

    bm.to_mesh(mesh)
    bm.free()
    
    # Modifiers for body
    sub = vase_obj.modifiers.new("Subdiv", 'SUBSURF')
    sub.levels = 2
    for p in mesh.polygons: p.use_smooth = True

    # --- Ornamental Ring Construction ---
    major_r, minor_r = 1.6, 0.12
    res_maj, res_min = 80, 16
    ring_mesh = bpy.data.meshes.new("OrnamentRing")
    ring_obj = bpy.data.objects.new("OrnamentRing", ring_mesh)
    bpy.context.collection.objects.link(ring_obj)
    bm_r = bmesh.new()
    
    s_rings = []
    for i in range(res_maj):
        theta = (i/res_maj)*2*math.pi
        cx, cy = major_r*math.cos(theta), major_r*math.sin(theta)
        curr_s = []
        for j in range(res_min):
            phi = (j/res_min)*2*math.pi
            rough = 0.05 * math.sin(10*theta) + random.uniform(-0.02, 0.02)
            re = minor_r + rough
            vx = cx + re*math.cos(phi)*math.cos(theta)
            vy = cy + re*math.cos(phi)*math.sin(theta)
            vz = 0.15 + re*math.sin(phi)
            curr_s.append(bm_r.verts.new(Vector((vx, vy, vz))))
        s_rings.append(curr_s)

    for i in range(res_maj):
        s1, s2 = s_rings[i], s_rings[(i+1)%res_maj]
        for j in range(res_min):
            bm_r.faces.new((s1[j], s1[(j+1)%res_min], s2[(j+1)%res_min], s2[j]))

    bm_r.to_mesh(ring_mesh)
    bm_r.free()
    
    sub_r = ring_obj.modifiers.new("Subdiv", 'SUBSURF')
    sub_r.levels = 1
    for p in ring_mesh.polygons: p.use_smooth = True

if __name__ == "__main__":
    execute()
