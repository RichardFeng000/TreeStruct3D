import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_serrated_leaf():
    # --- Parameters ---
    length = 12.0
    max_width = 3.5
    segments = 120  # Higher resolution for better serration definition
    teeth_count = 30 # Number of teeth per side
    tooth_amplitude = 0.25 # Depth of the jaggedness
    curvature_longitudinal = 1.8 # Arch along length
    midrib_height = 0.3
    midrib_width = 0.15
    petiole_length = 2.5
    petiole_radius = 0.15

    mesh = bpy.data.meshes.new("SerratedLeaf")
    obj = bpy.data.objects.new("SerratedLeaf", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    # 1. Generate Blade Vertices
    # We create two strips for the midrib (forming a ridge) and two for the edges
    mid_left_verts = []
    mid_right_verts = []
    edge_left_verts = []
    edge_right_verts = []

    for i in range(segments + 1):
        t = i / segments # 0 to 1
        y = t * length
        
        # Elongated Ovate Shape: width peaks around t=0.35 - 0.45
        # Using a function that stays wider for longer than a simple sine
        width_factor = math.sin(t * math.pi) * (1.0 - t * 0.2)
        current_half_width = width_factor * (max_width / 2.0)
        
        # Serration Logic: Sawtooth wave
        # Use a modulo function to create the jagged points
        tooth_phase = t * teeth_count
        saw_val = tooth_phase % 1.0
        # Create a sharp peak and a slope back (classic sawtooth)
        # We amplify this towards the middle, dampen at tip and base
        serration_offset = saw_val * tooth_amplitude
        dampen = math.sin(t * math.pi) # No serrations at extreme start/end
        actual_offset = serration_offset * dampen

        # Z-Curvature (longitudinal arch)
        z_curve = math.sin(t * math.pi) * curvature_longitudinal
        
        # Midrib Ridge: two parallel lines slightly raised
        v_ml = bm.verts.new(Vector((-midrib_width/2, y, z_curve + midrib_height)))
        v_mr = bm.verts.new(Vector((midrib_width/2, y, z_curve + midrib_height)))
        mid_left_verts.append(v_ml)
        mid_right_verts.append(v_mr)

        # Outer Edges: curved down from the ridge and jagged
        edge_z = z_curve - 0.1 # Blade surface dips slightly below midrib
        v_el = bm.verts.new(Vector((-current_half_width - actual_offset, y, edge_z)))
        v_er = bm.verts.new(Vector((current_half_width + actual_offset, y, edge_z)))
        edge_left_verts.append(v_el)
        edge_right_verts.append(v_er)

    # 2. Create Blade Faces
    for i in range(segments):
        # Midrib top face (the ridge)
        bm.faces.new((mid_left_verts[i], mid_left_verts[i+1], mid_right_verts[i+1], mid_right_verts[i]))
        
        # Left side: from midrib left to edge left
        bm.faces.new((mid_left_verts[i], edge_left_verts[i], edge_left_verts[i+1], mid_left_verts[i+1]))
        
        # Right side: from midrib right to edge right
        bm.faces.new((mid_right_verts[i], mid_right_verts[i+1], edge_right_verts[i+1], edge_right_verts[i]))

    # 3. Petiole (Stem)
    stem_res = 8
    stem_segments = 10
    ring_verts_start = []
    for i in range(stem_res):
        angle = (2 * math.pi / stem_res) * i
        v = bm.verts.new(Vector((math.cos(angle)*petiole_radius, 0, math.sin(angle)*petiole_radius)))
        ring_verts_start.append(v)

    prev_ring = ring_verts_start
    for j in range(1, stem_segments + 1):
        curr_y = -j * (petiole_length / stem_segments)
        curr_ring = []
        taper = 1.0 - (j / stem_segments) * 0.3
        for i in range(stem_res):
            angle = (2 * math.pi / stem_res) * i
            v = bm.verts.new(Vector((math.cos(angle)*petiole_radius*taper, curr_y, math.sin(angle)*petiole_radius*taper)))
            curr_ring.append(v)
        
        for i in range(stem_res):
            next_i = (i + 1) % stem_res
            bm.faces.new((prev_ring[i], prev_ring[next_i], curr_ring[next_i], curr_ring[i]))
        prev_ring = curr_ring

    # Cap the bottom of the stem
    bottom_v = bm.verts.new(Vector((0, -petiole_length, 0)))
    for i in range(stem_res):
        next_i = (i + 1) % stem_res
        bm.faces.new((bottom_v, prev_ring[i], prev_ring[next_i]))

    # Bridge Stem to Blade base
    # Connect top ring of stem to midrib start and edges start
    for i in range(stem_res):
        next_i = (i + 1) % stem_res
        # Bridge to midrib ridge
        bm.faces.new((ring_verts_start[i], ring_verts_start[next_i], mid_right_verts[0], mid_left_verts[0])) # simplistic bridge

    bm.to_mesh(mesh)
    bm.free()

    # Shading and subtle smoothing (Subdiv would kill the serrations, so we use Smooth Shading instead)
    for poly in mesh.polygons:
        poly.use_smooth = True
    
    return obj

def main():
    clear_scene()
    leaf_obj = create_serrated_leaf()
    # Three-quarter perspective rotation
    leaf_obj.rotation_euler = (math.radians(-15), 0, math.radians(45))
    leaf_obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
