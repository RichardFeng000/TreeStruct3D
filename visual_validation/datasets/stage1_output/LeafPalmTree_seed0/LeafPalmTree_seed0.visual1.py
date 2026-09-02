import bpy
import bmesh
import math
import numpy as np

def clear_scene():
    """Clears the default scene of all objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_palm_frond():
    """Generates a procedural pinnate palm frond with corrected geometry and bending."""
    # Parameters
    num_segments = 60  
    rachis_length = 15.0
    max_leaflet_len = 5.0
    leaflet_width_base = 0.4 # Increased width for visibility
    curvature_strength = 0.07 
    num_leaflets_per_side = 45 
    
    bm = bmesh.new()

    # 1. Generate Rachis Path
    rachis_points = []
    for i in range(num_segments):
        t = i / (num_segments - 1)
        y = t * rachis_length
        z = -curvature_strength * (y ** 2)
        x = 0.8 * math.sin(t * 2) # Natural sway
        rachis_points.append(np.array([x, y, z]))

    # Generate Rachis Tube
    rings = []
    ring_res = 8
    radius_start = 0.25
    radius_end = 0.05
    
    for i in range(num_segments):
        p = rachis_points[i]
        t = i / (num_segments - 1)
        r = radius_start + t * (radius_end - radius_start)
        
        # Local frame for the ring
        if i < num_segments - 1:
            tangent = rachis_points[i+1] - p
        else:
            tangent = p - rachis_points[i-1]
        tangent /= np.linalg.norm(tangent)
        
        # Create orthonormal basis
        up = np.array([0, 0, 1]) if abs(tangent[2]) < 0.9 else np.array([0, 1, 0])
        right = np.cross(tangent, up)
        right /= np.linalg.norm(right)
        actual_up = np.cross(right, tangent)
        
        ring = []
        for j in range(ring_res):
            angle = (2 * math.pi * j) / ring_res
            v_pos = p + r * (math.cos(angle) * right + math.sin(angle) * actual_up)
            ring.append(bm.verts.new(tuple(v_pos)))
        rings.append(ring)

    for i in range(len(rings) - 1):
        r1, r2 = rings[i], rings[i+1]
        for j in range(ring_res):
            bm.faces.new((r1[j], r1[(j + 1) % ring_res], r2[(j + 1) % ring_res], r2[j]))

    # 2. Generate Leaflets (Symmetrical, Pointed, and Local Bending)
    for i in range(num_leaflets_per_side):
        t = (i / (num_leaflets_per_side - 1)) * 0.95
        idx = int(t * (num_segments - 1))
        p = rachis_points[idx]
        
        # Local frame for leaflet orientation
        if idx < num_segments - 1:
            tan = rachis_points[idx+1] - p
        else:
            tan = p - rachis_points[idx-1]
        tan /= np.linalg.norm(tan)
        
        # The 'side' vector is perpendicular to tangent and generally horizontal
        world_up = np.array([0, 0, 1])
        right = np.cross(tan, world_up)
        if np.linalg.norm(right) < 1e-4: # Handle vertical segments
            right = np.array([1, 0, 0])
        right /= np.linalg.norm(right)
        local_up = np.cross(right, tan)

        # Length taper: shorter at base and tip, longest in lower middle
        len_factor = 1.0 - abs(t - 0.35) / 0.65
        current_len = max(0.4, max_leaflet_len * len_factor)
        
        for side in [-1, 1]:
            leaf_seg = 6
            prev_vpair = None
            side_vec = right * side
            
            for s in range(leaf_seg + 1):
                st = s / leaf_seg
                dist = st * current_len
                
                # Leaflet geometry: extends along side_vec, then droops relative to local frame
                # Bending is a mix of the original 'right' vector and a downward gravity pull
                droop_dir = (local_up * -0.5) + (np.array([0, 0, -1]) * 0.8)
                droop_dir /= np.linalg.norm(droop_dir)
                
                pos = p + side_vec * dist + droop_dir * (st**2 * 2.0)
                
                # Taper width to a point
                w = (leaflet_width_base * (1.0 - st)) / 2.0
                # Width is along the 'local_up' direction for the blade thickness/flatness
                v1_pos = pos - local_up * w
                v2_pos = pos + local_up * w
                
                v1 = bm.verts.new(tuple(v1_pos))
                v2 = bm.verts.new(tuple(v2_pos))
                
                if prev_vpair:
                    bm.faces.new((prev_vpair[0], prev_vpair[1], v2, v1))
                prev_vpair = (v1, v2)

    # Finalize Mesh
    mesh = bpy.data.meshes.new("PalmFrondMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("PalmFrond", mesh)
    bpy.context.collection.objects.link(obj)
    bm.free()

    # Global rotation for better viewing angle
    obj.rotation_euler[0] = math.radians(-15)
    return obj

def main():
    clear_scene()
    frond = create_palm_frond()
    for poly in frond.data.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    main()
