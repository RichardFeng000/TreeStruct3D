import bpy
import bmesh
import math

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_leaf():
    # Parameters for the leaf geometry
    length = 15.0
    max_width = 2.4
    segments = 100  # Longitudinal resolution
    rib_width = 0.15 # Width of the central rib ridge
    rib_height = 0.25 # Height of the midrib above the blade
    v_depth = 0.6    # Depth of the leaf dip (the V-shape)
    curve_z_amp = 1.8 # Longitudinal curvature (Z axis)
    curve_x_amp = 1.0 # Side-to-side sway (X axis)

    bm = bmesh.new()
    
    # Vertex arrays for cross-sections
    verts_l_edge = []
    verts_rib_l = []
    verts_rib_top = []
    verts_rib_r = []
    verts_r_edge = []

    for i in range(segments + 1):
        t = i / segments  # normalized length [0, 1]
        y = (t - 0.5) * length
        
        # Width taper: pointed tip at t=1, narrow base at t=0
        # Using a smooth sine-based envelope for the organic blade shape
        width_factor = math.sin(math.pi * t**0.8) 
        current_half_width = (max_width / 2.0) * width_factor
        
        # Natural longitudinal curvature
        z_off = curve_z_amp * math.sin(math.pi * t)
        x_off = curve_x_amp * math.sin(math.pi * t * 1.2)
        
        # The rib also tapers towards the tip
        current_rib_w = (rib_width / 2.0) * (1.0 - t**2)
        current_rib_h = rib_height * (1.0 - t**2)
        
        # Z-dip for the blade edges to create a subtle V-shape/trough
        edge_z_offset = v_depth * width_factor * math.sin(math.pi * t)

        # Create 5 points for each cross section
        v_top = bm.verts.new((x_off, y, z_off + current_rib_h))
        v_rl = bm.verts.new((x_off - current_rib_w, y, z_off))
        v_rr = bm.verts.new((x_off + current_rib_w, y, z_off))
        v_l = bm.verts.new((x_off - current_half_width, y, z_off - edge_z_offset))
        v_r = bm.verts.new((x_off + current_half_width, y, z_off - edge_z_offset))
        
        verts_l_edge.append(v_l)
        verts_rib_l.append(v_rl)
        verts_rib_top.append(v_top)
        verts_rib_r.append(v_rr)
        verts_r_edge.append(v_r)

    # Build the faces for the leaf
    for i in range(segments):
        # Indices for current and next slice
        s = i
        n = i + 1
        
        # Left side of blade: LeftEdge -> RibLeft
        bm.faces.new((verts_l_edge[s], verts_rib_l[s], verts_rib_l[n], verts_l_edge[n]))
        
        # Left side of rib ridge: RibLeft -> RibTop
        bm.faces.new((verts_rib_l[s], verts_rib_top[s], verts_rib_top[n], verts_rib_l[n]))
        
        # Right side of rib ridge: RibTop -> RibRight
        bm.faces.new((verts_rib_top[s], verts_rib_r[s], verts_rib_r[n], verts_rib_top[n]))
        
        # Right side of blade: RibRight -> RightEdge
        bm.faces.new((verts_rib_r[s], verts_r_edge[s], verts_r_edge[n], verts_rib_r[n]))

    # Finalize mesh
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    mesh = bpy.data.meshes.new("LeafMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Leaf", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Subdivision for organic smoothness
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    return obj

def main():
    clear_scene()
    leaf_obj = create_leaf()
    
    # Position and orientation for a three-quarter perspective
    leaf_obj.location = (0, 0, 0)
    leaf_obj.rotation_euler = (math.radians(-20), 0, math.radians(45))

if __name__ == "__main__":
    main()
