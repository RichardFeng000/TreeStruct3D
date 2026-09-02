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
    max_width = 5.0  # Increased width for better ovate proportions
    segments = 150   # Higher resolution for sharper teeth
    teeth_count = 40 # Number of tooth-pairs (peaks)
    tooth_amplitude = 0.6 # Significantly increased for "prominent" serration
    curvature_longitudinal = 1.2 
    midrib_height = 0.4
    petiole_length = 3.0
    petiole_radius = 0.2

    mesh = bpy.data.meshes.new("SerratedLeaf")
    obj = bpy.data.objects.new("SerratedLeaf", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    # Generate Blade Vertices
    # We create a central midrib and two side edges
    mid_verts = []
    edge_left_verts = []
    edge_right_verts = []

    for i in range(segments + 1):
        t = i / segments # 0 to 1
        y = t * length
        
        # Ovate Shape: wider at bottom, tapering to a point (approx peak at t=0.3)
        width_factor = math.sin(t * math.pi) * (1.0 - t * 0.5)
        current_half_width = width_factor * (max_width / 2.0)
        
        # Serration Logic: Sharp triangle wave for distinct "teeth"
        # f(x) = abs((x % 2) - 1) creates a zig-zag between 0 and 1
        tooth_phase = t * teeth_count
        saw_val = abs((tooth_phase % 2.0) - 1.0)
        
        # Dampen at very base and tip so it starts/ends cleanly
        dampen = math.sin(t * math.pi)
        serration_offset = saw_val * tooth_amplitude * dampen

        # Z-Curvature: Gentle arch + Midrib ridge
        z_curve = math.sin(t * math.pi) * curvature_longitudinal
        mid_z = z_curve + midrib_height
        edge_z = z_curve # Edges sit lower than the midrib

        # Central Ridge
        v_mid = bm.verts.new(Vector((0, y, mid_z)))
        mid_verts.append(v_mid)

        # Outer Edges with serration offset
        v_el = bm.verts.new(Vector((-current_half_width - serration_offset, y, edge_z)))
        v_er = bm.verts.new(Vector((current_half_width + serration_offset, y, edge_z)))
        edge_left_verts.append(v_el)
        edge_right_verts.append(v_er)

    # Create Blade Faces
    for i in range(segments):
        # Left side face
        bm.faces.new((mid_verts[i], edge_left_verts[i], edge_left_verts[i+1], mid_verts[i+1]))
        # Right side face
        bm.faces.new((mid_verts[i], mid_verts[i+1], edge_right_verts[i+1], edge_right_verts[i]))

    # Petiole (Stem) Construction
    stem_res = 8
    stem_segments = 12
    ring_verts_start = []
    for i in range(stem_res):
        angle = (2 * math.pi / stem_res) * i
        # Positioned at the base of the leaf blade (y=0)
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
        bm.faces.new((bottom_v, prev_ring[next_i], prev_ring[i]))

    # Clean bridge from Stem Ring to Leaf Blade Base
    # Connect the ring vertices to the first few vertices of the blade logically
    for i in range(stem_res):
        next_i = (i + 1) % stem_res
        v1 = ring_verts_start[i]
        v2 = ring_verts_start[next_i]
        # Connect to midrib start and nearest edge starts
        bm.faces.new((v1, v2, mid_verts[0]))

    bm.to_mesh(mesh)
    bm.free()

    for poly in mesh.polygons:
        poly.use_smooth = True
    
    return obj

def main():
    clear_scene()
    leaf_obj = create_serrated_leaf()
    # 3/4 Perspective Rotation
    leaf_obj.rotation_euler = (math.radians(-20), 0, math.radians(45))
    leaf_obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
