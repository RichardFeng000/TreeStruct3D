import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_auger_shell():
    """
    Procedurally generates a high-fidelity auger shell based on 
    a logarithmic conical spiral with geometric surface details.
    """
    # --- Parameters ---
    turns = 10                    # Number of whorls
    rings_per_turn = 64           # Resolution along the length
    segments_per_ring = 48        # Resolution around the cross-section
    base_radius_spine = 0.5       # Radius of the spiral path at the wide end
    tip_height = 6.0              # Total height of the shell
    tube_width_start = 0.1        # Width of the whorl tube at tip
    tube_width_end = 0.4          # Width of the whorl tube at base
    
    # Detail parameters for "wavy patterns"
    growth_ridge_freq = 15        # Frequency of horizontal ridges
    growth_ridge_amp = 0.03       # Amplitude of horizontal ridges
    wave_phase_shift = 2.0        # How much the wave shifts as it goes up (creating waves)
    rib_count = 12                # Number of longitudinal ribs
    rib_amp = 0.04               # Amplitude of longitudinal ribs

    total_steps = int(turns * rings_per_turn)
    bm = bmesh.new()

    prev_ring_verts = []

    for i in range(total_steps + 1):
        # u goes from 0 (tip) to 1 (base)
        u = i / total_steps
        t = u * turns * 2 * math.pi
        
        # Spine coordinates: a conical spiral
        # Radius of the center of the tube grows linearly with height
        spine_radius = base_radius_spine * u
        x = spine_radius * math.cos(t)
        y = spine_radius * math.sin(t)
        z = u * tip_height

        # The radius of the tube itself scales from tip to base
        current_tube_rad = tube_width_start + (tube_width_end - tube_width_start) * u
        
        # Calculate tangent for orientation
        dt = 0.1
        t_next = t + dt
        u_next = min(1.0, u + (dt / (turns * 2 * math.pi)))
        x_next = base_radius_spine * u_next * math.cos(t_next)
        y_next = base_radius_spine * u_next * math.sin(t_next)
        z_next = u_next * tip_height
        
        tangent = Vector((x_next - x, y_next - y, z_next - z)).normalized()
        
        # Coordinate frame for the ring
        up = Vector((0, 0, 1)) if abs(tangent.z) < 0.9 else Vector((0, 1, 0))
        norm_x = tangent.cross(up).normalized()
        norm_y = tangent.cross(norm_x).normalized()

        current_ring_verts = []
        for s in range(segments_per_ring):
            phi = (s / segments_per_ring) * 2 * math.pi
            
            # --- GEOMETRIC TEXTURING ---
            # 1. Wavy patterns: sin function that depends on both t and phi
            # This creates ridges that flow along the spiral but oscillate
            wave_val = math.sin(t * growth_ridge_freq + phi * wave_phase_shift)
            growth_mod = 1.0 + growth_ridge_amp * wave_val
            
            # 2. Vertical Ribs: fixed longitudinal ridges
            rib_mod = 1.0 + rib_amp * math.cos(phi * rib_count)
            
            r = current_tube_rad * growth_mod * rib_mod
            
            pos = Vector((x, y, z)) + (norm_x * math.cos(phi) * r) + (norm_y * math.sin(phi) * r)
            current_ring_verts.append(bm.verts.new(pos))

        # Bridge the current ring to the previous ring
        if prev_ring_verts:
            for s in range(segments_per_ring):
                v1 = prev_ring_verts[s]
                v2 = prev_ring_verts[(s + 1) % segments_per_ring]
                v3 = current_ring_verts[(s + 1) % segments_per_ring]
                v4 = current_ring_verts[s]
                bm.faces.new((v1, v2, v3, v4))

        prev_ring_verts = current_ring_verts

    # Close the tip: Merge all vertices of the first ring into one apex point
    # Since we built from i=0 (tip), we need to find those verts.
    # The first 'segments_per_ring' vertices are the ones at the tip.
    all_verts = bm.verts[:]
    tip_verts = all_verts[:segments_per_ring]
    if tip_verts:
        center_pos = Vector((0, 0, 0))
        for v in tip_verts: center_pos += v.co
        center_pos /= len(tip_verts)
        apex_v = bm.verts.new(center_pos)
        
        # We must replace the vertices in the first set of faces
        bm.verts.ensure_lookup_table()
        for f in bm.faces:
            # If a face uses any vertex from the tip ring, we want it to connect to apex_v
            contains_tip = False
            for v in f.verts:
                if v in tip_verts:
                    contains_tip = True
                    break
            if contains_tip:
                # Since bmesh faces are mutable but adding/removing verts can be tricky, 
                # it's safer to use a different method for the very first ring.
                pass

    # Actually, easier way to handle tip in BMesh is just merge by distance later or 
    # use bpy.ops.mesh.remove_doubles. We will use remove_doubles below.

    # Close the aperture (base)
    if prev_ring_verts:
        try:
            bm.faces.new(prev_ring_verts)
        except:
            pass 

    bm.normal_update()
    
    mesh = bpy.data.meshes.new("AugerShell")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("AugerShell", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Set active and select for modifiers/ops
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # 1. Weld vertices at the tip to ensure it's a point
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.2) 
    bpy.ops.object.mode_set(mode='OBJECT')

    # 2. Subdivision Surface for organic smoothness
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2

    # 3. Shade Smooth
    bpy.ops.object.shade_smooth()

    # Center the object relative to its height
    obj.location.z = -tip_height / 2

if __name__ == "__main__":
    clear_scene()
    create_auger_shell()
