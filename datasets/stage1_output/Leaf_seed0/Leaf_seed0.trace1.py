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
    max_width = 2.0
    segments = 80  # Longitudinal resolution
    v_depth = 0.5   # The depth of the 'V' shape cross-section
    curve_z_amp = 1.5 # Longitudinal curvature (Z axis)
    curve_x_amp = 0.8 # Slight side-to-side sway (X axis)
    midrib_height = 0.2

    # Create BMesh for the leaf blade
    bm = bmesh.new()
    
    # We will store vertex references to build faces and the midrib later
    verts_left = []
    verts_center = []
    verts_right = []

    for i in range(segments + 1):
        t = i / segments  # normalized length [0, 1]
        y = (t - 0.5) * length
        
        # Width taper: pointed tip at t=1, slightly rounded base at t=0
        # Use a function that starts narrow, widens quickly, then tapers to a sharp point
        width_factor = math.sin(math.pi * (t**0.7)) 
        current_half_width = (max_width / 2.0) * width_factor
        
        # Natural longitudinal curvature
        z_off = curve_z_amp * math.sin(math.pi * t)
        x_off = curve_x_amp * math.sin(math.pi * t * 1.2)
        
        # Create the three points of the cross-section: Left, Center, Right
        # The center is higher than the sides to create the 'V' shape
        v_c = bm.verts.new((x_off, y, z_off))
        v_l = bm.verts.new((x_off - current_half_width, y, z_off - v_depth * width_factor))
        v_r = bm.verts.new((x_off + current_half_width, y, z_off - v_depth * width_factor))
        
        verts_left.append(v_l)
        verts_center.append(v_c)
        verts_right.append(v_r)

    # Build the faces for the main blade
    for i in range(segments):
        # Face 1: Left to Center
        bm.faces.new((verts_left[i], verts_center[i], verts_center[i+1], verts_left[i+1]))
        # Face 2: Center to Right
        bm.faces.new((verts_center[i], verts_right[i], verts_right[i+1], verts_center[i+1]))

    # Create the midrib as a raised ridge for physical volume
    midrib_verts_top = []
    for i in range(segments + 1):
        v_c = verts_center[i]
        t = i / segments
        # Offset the top of the rib slightly to create volume
        # We use a small offset based on local curvature approximation
        offset_z = midrib_height * (1.0 - t*0.5) # Rib tapers off towards tip
        v_top = bm.verts.new((v_c.co.x, v_c.co.y, v_c.co.z + offset_z))
        midrib_verts_top.append(v_top)

    # Create the volume for the midrib by bridging center verts and top verts
    for i in range(segments):
        # Side faces of the rib
        bm.faces.new((verts_center[i], midrib_verts_top[i], midrib_verts_top[i+1], verts_center[i+1]))

    # Finalize mesh
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    mesh = bpy.data.meshes.new("LeafMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Leaf", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Add a Subdivision Surface modifier for organic smoothness
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    # Set smooth shading for the object
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    return obj

def main():
    clear_scene()
    leaf_obj = create_leaf()
    
    # Ensure the object is at origin and oriented as requested (three-quarter perspective)
    leaf_obj.location = (0, 0, 0)
    # Rotation to make it look natural from a 3/4 view
    leaf_obj.rotation_euler = (math.radians(-15), 0, math.radians(45))

if __name__ == "__main__":
    main()
