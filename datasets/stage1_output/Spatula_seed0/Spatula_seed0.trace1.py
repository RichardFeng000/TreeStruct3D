import bpy
import bmesh
import math

def clear_scene():
    """Clears default Blender scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_spatula_material():
    """Creates a dark blue-gray material."""
    mat = bpy.data.materials.new(name="SpatulaMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    # Dark blue-gray color: roughly (0.1, 0.15, 0.2)
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.1, 0.15, 0.2, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.4
        bsdf.inputs['Metallic'].default_value = 0.1
    return mat

def build_spatula():
    # Dimensions
    handle_radius = 0.4
    handle_length = 25.0
    head_width = 7.0
    head_depth = 12.0
    head_thickness = 0.3
    transition_length = 4.0
    
    # Create mesh and object
    mesh = bpy.data.meshes.new("SpatulaMesh")
    obj = bpy.data.objects.new("Spatula", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # 1. Create the handle (starting from bottom at origin)
    # Fix: remove 'location' keyword from create_circle as it is not supported in some versions/ops
    bmesh.ops.create_circle(bm, segments=32, radius=handle_radius)
    
    # Extrude handle up
    res = bmesh.ops.extrude_face(bm, vec=(0, 0, handle_length))
    verts_top = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    
    # 2. Transition from circular handle to rectangular head
    steps = 8
    step_height = transition_length / steps
    
    current_verts = verts_top
    for i in range(steps):
        res = bmesh.ops.extrude_face(bm, vec=(0, 0, step_height))
        new_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
        
        # Progress from 0 to 1
        t = (i + 1) / steps
        curr_w = handle_radius * 2 + (head_width - handle_radius * 2) * t
        curr_d = handle_radius * 2 + (head_depth - handle_radius * 2) * t
        
        # Reshape the vertices to map from circle to rounded rectangle
        for v in new_verts:
            x, y, z = v.co
            angle = math.atan2(y, x)
            # Use a modified circular mapping for the rectangular shape
            s_x = math.sin(angle)
            s_y = math.cos(angle)
            
            # Approximate rounded rectangle: 
            # we use an interpolation between circle and box
            # For simplicity, we map normalized x/y based on a signum-like approach
            # but smoothed for the 'rounded' look.
            
            # Scale to target dimensions
            v.co.x = s_x * (curr_w / 2)
            v.co.y = s_y * (curr_d / 2)
            
        current_verts = new_verts

    # 3. Create the head thickness
    res = bmesh.ops.extrude_face(bm, vec=(0, 0, head_thickness))
    head_top_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    
    # Add a slight crown/curve to the working surface
    for v in head_top_verts:
        # Dist from center of width (X)
        dist_from_center = abs(v.co.x) / (head_width / 2)
        # Gentle arc across the width, peak at center
        v.co.z += 0.2 * (1 - dist_from_center**2)

    # Finalize BMesh
    bm.to_mesh(mesh)
    bm.free()

    # Bevel for clean squared-off edges
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.15
    bevel.segments = 3
    
    # Subdivision Surface for smoothness
    subsurf = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf.levels = 2

    # Smooth shading
    for poly in mesh.polygons:
        poly.use_smooth = True

    # Assign material
    mat = create_spatula_material()
    obj.data.materials.append(mat)
    
    return obj

def main():
    clear_scene()
    spatula_obj = build_spatula()
    
    # Position object to be centered vertically at the origin
    total_height = 25.0 + 4.0 + 0.3
    spatula_obj.location.z = -total_height / 2

if __name__ == "__main__":
    main()
