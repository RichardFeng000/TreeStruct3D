import bpy
import bmesh
import math
import random
from mathutils import Vector, Euler

def clear_scene():
    """Removes all default objects from the scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def generate_reed_ear():
    clear_scene()
    
    # Parameters
    num_florets = 320
    spike_height = 2.5
    stem_radius = 0.015
    golden_angle = math.radians(137.5)
    bend_intensity = 0.2
    
    # Materials
    pale_green = (0.45, 0.65, 0.35, 1.0)
    mat = create_material("ReedGreen", pale_green)
    
    # We will use a single BMesh for the entire object to ensure efficiency
    main_bm = bmesh.new()
    
    # Define the path of the central axis (rachis)
    def get_path_pos(t):
        """Returns position and tangent at normalized time t [0, 1]"""
        z = t * spike_height
        # Gentle curve for "angled posture"
        x = math.sin(t * math.pi * 0.5) * bend_intensity
        y = math.cos(t * math.pi * 0.2) * (bend_intensity * 0.3)
        pos = Vector((x, y, z))
        # Simple tangent approximation
        dt = 0.01
        z2 = (t + dt) * spike_height
        x2 = math.sin((t+dt) * math.pi * 0.5) * bend_intensity
        y2 = math.cos((t+dt) * math.pi * 0.2) * (bend_intensity * 0.3)
        tan = (Vector((x2, y2, z2)) - pos).normalized()
        return pos, tan

    # 1. Create the Stem (Rachis)
    segments_z = 40
    rings = 8
    stem_verts = []
    for i in range(segments_z + 1):
        t = i / segments_z
        pos, tan = get_path_pos(t)
        
        # Create a coordinate frame for the ring
        # Find an arbitrary perpendicular vector
        up = Vector((0, 0, 1)) if abs(tan.z) < 0.9 else Vector((0, 1, 0))
        right = tan.cross(up).normalized()
        true_up = right.cross(tan).normalized()
        
        ring_verts = []
        for j in range(rings):
            angle = (2 * math.pi / rings) * j
            v_pos = pos + (right * math.cos(angle) * stem_radius) + (true_up * math.sin(angle) * stem_radius)
            ring_verts.append(main_bm.verts.new(v_pos))
        stem_verts.append(ring_verts)

    # Bridge the rings of the stem
    for i in range(segments_z):
        curr_ring = stem_verts[i]
        next_ring = stem_verts[i+1]
        for j in range(rings):
            nj = (j + 1) % rings
            main_bm.faces.new((curr_ring[j], curr_ring[nj], next_ring[nj], next_ring[j]))

    # 2. Create the Florets (Scale-like seeds)
    for i in range(num_florets):
        t = i / num_florets
        pos, tan = get_path_pos(t)
        
        # Phyllotaxis distribution
        phi = i * golden_angle
        
        # Scale: slightly taper the whole ear towards the top
        size_scale = 1.0 - (t * 0.5)
        
        # Local coordinate system for the floret
        up_vec = Vector((0, 0, 1)) if abs(tan.z) < 0.9 else Vector((0, 1, 0))
        right_axis = tan.cross(up_vec).normalized()
        up_axis = right_axis.cross(tan).normalized()
        
        # Rotate axes by phi for distribution around stem
        rot_mat = Euler((0, 0, phi), 'XYZ').to_matrix()
        # Since we are in world space, we need to rotate relative to the tangent
        # A better way: construct a local basis and multiply
        local_right = (right_axis * math.cos(phi)) + (up_axis * math.sin(phi))
        local_up = (-right_axis * math.sin(phi)) + (up_axis * math.cos(phi))
        
        # Floret geometry: a small pointed scale
        # It's like a small teardrop shell extending outwards and upwards
        floret_len = 0.12 * size_scale
        floret_width = 0.04 * size_scale
        
        # Create vertices for the floret (simplified as a tapered wedge)
        # Base points (attached to stem)
        v0 = main_bm.verts.new(pos + local_right * stem_radius)
        v1 = main_bm.verts.new(pos - local_right * stem_radius)
        
        # Mid point (the widest part of the scale)
        mid_dist = floret_len * 0.4
        mid_pos = pos + (local_right * mid_dist) + (tan * 0.05)
        v2 = main_bm.verts.new(mid_pos + local_up * floret_width)
        v3 = main_bm.verts.new(mid_pos - local_up * floret_width)
        
        # Tip point
        tip_pos = pos + (local_right * floret_len) + (tan * 0.15)
        v4 = main_bm.verts.new(tip_pos)
        
        # Create faces for the scale
        main_bm.faces.new((v0, v2, v3, v1)) # Base to mid
        main_bm.faces.new((v2, v4, v3))     # Mid to tip

    # Finalize and link to scene
    mesh_data = bpy.data.meshes.new("ReedEar")
    main_bm.to_mesh(mesh_data)
    main_bm.free()
    
    obj = bpy.data.objects.new("ReedEar", mesh_data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    
    # Final posture adjustment: lean the whole thing slightly
    obj.rotation_euler = Euler((0.1, 0, 0), 'XYZ')

if __name__ == "__main__":
    generate_reed_ear()
