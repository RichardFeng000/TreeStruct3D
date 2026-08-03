import bpy
import bmesh
import math

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_leaf():
    # Parameters for a more slender, organic leaf geometry
    length = 20.0        # Increased length for "elongated" look
    max_width = 1.8      # Slightly narrower
    segments = 120       # Higher resolution for smoother curves
    rib_width = 0.12     # Narrower rib ridge base
    rib_height = 0.5     # Increased height to make midrib "visible"
    v_depth = 0.8        # Deeper trough for better definition
    curve_z_amp = 2.0    # Longitudinal curvature
    curve_x_amp = 1.2    # Side-to-side organic sway

    bm = bmesh.new()
    
    verts_l_edge = []
    verts_rib_l = []
    verts_rib_top = []
    verts_rib_r = []
    verts_r_edge = []

    for i in range(segments + 1):
        t = i / segments  # normalized length [0, 1]
        y = (t - 0.5) * length
        
        # Asymmetric width: wider at base (t=0), tapering to a sharp point (t=1)
        # Using a power function to shift the widest part towards the base
        width_factor = math.sin(math.pi * (t**0.7)) 
        current_half_width = (max_width / 2.0) * width_factor
        
        # Natural organic curvature along the length
        z_off = curve_z_amp * math.sin(math.pi * t)
        x_off = curve_x_amp * math.sin(math.pi * t * 1.1)
        
        # Rib tapers as it reaches the tip
        current_rib_w = (rib_width / 2.0) * (1.0 - t**1.5)
        current_rib_h = rib_height * (1.0 - t**1.5)
        
        # Define the "trough" or V-shape of the blade edges
        edge_z_offset = v_depth * width_factor * math.sin(math.pi * t)

        # Create 5 points for each cross section to define midrib and blade
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

    # Build the faces (quads) for the leaf structure
    for i in range(segments):
        s = i
        n = i + 1
        
        # Left blade surface: Outer edge to inner rib base
        bm.faces.new((verts_l_edge[s], verts_rib_l[s], verts_rib_l[n], verts_l_edge[n]))
        
        # Left midrib ridge: Rib base to top of rib
        bm.faces.new((verts_rib_l[s], verts_rib_top[s], verts_rib_top[n], verts_rib_l[n]))
        
        # Right midrib ridge: Top of rib to rib base
        bm.faces.new((verts_rib_top[s], verts_rib_r[s], verts_rib_r[n], verts_rib_top[n]))
        
        # Right blade surface: Inner rib base to outer edge
        bm.faces.new((verts_rib_r[s], verts_r_edge[s], verts_r_edge[n], verts_rib_r[n]))

    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    mesh = bpy.data.meshes.new("LeafMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Leaf", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Apply subdivision for organic smoothness and to blend the rib ridge naturally
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3
    
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    return obj

def main():
    clear_scene()
    leaf_obj = create_leaf()
    
    # Position and orientation for a clear three-quarter perspective view
    leaf_obj.location = (0, 0, 0)
    leaf_obj.rotation_euler = (math.radians(-15), 0, math.radians(45))

if __name__ == "__main__":
    main()
