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
    if bsdf:
        # Dark blue-gray color
        bsdf.inputs['Base Color'].default_value = (0.1, 0.15, 0.2, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.3
        bsdf.inputs['Metallic'].default_value = 0.1
    return mat

def build_spatula():
    # Dimensions
    handle_radius = 0.4
    handle_length = 20.0
    head_width = 7.0
    head_depth = 12.0
    head_thickness = 0.3
    transition_length = 5.0
    
    # Create mesh and object
    mesh = bpy.data.meshes.new("SpatulaMesh")
    obj = bpy.data.objects.new("Spatula", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # 1. Create the handle base (circular)
    # Use create_circle then fill to get a face for extrusion
    bmesh.ops.create_circle(bm, segments=32, radius=handle_radius)
    verts_base = [v for v in bm.verts]
    # Fill circle to create the start face
    bmesh.ops.contextual_create(bm, geom=verts_base)
    face_start = [f for f in bm.faces if len(f.verts) == 32][0]

    # 2. Extrude handle shaft
    res = bmesh.ops.extrude_face_region(bm, geom=[face_start])
    verts_shaft_top = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in verts_shaft_top:
        v.co.z += handle_length

    # 3. Transition from circular shaft to rectangular head
    steps = 10
    step_h = transition_length / steps
    
    current_verts = verts_shaft_top
    for i in range(steps):
        # Find the current top face (the one with most vertices)
        faces = [f for f in bm.faces if len(f.verts) == 32]
        face_to_extrude = None
        # The last created face is usually at the top
        for f in faces:
            if all(v in current_verts for v in f.verts):
                face_to_extrude = f
                break
        
        if not face_to_extrude: 
            # Fallback to find any face connected to these verts
            face_to_extrude = faces[-1]

        res = bmesh.ops.extrude_face_region(bm, geom=[face_to_extrude])
        new_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
        
        t = (i + 1) / steps
        # Target dimensions at this step
        curr_w = handle_radius * 2 + (head_width - handle_radius * 2) * t
        curr_d = handle_radius * 2 + (head_depth - handle_radius * 2) * t
        
        for v in new_verts:
            # Original position relative to current center
            center_z = v.co.z # approx
            # Map circle points to rounded rectangle
            angle = math.atan2(v.co.y, v.co.x)
            
            # Simplified rounded box mapping
            # Normalize the circular coords
            nx = math.cos(angle)
            ny = math.sin(angle)
            
            # Push points towards the edges of a rectangle (smoothly)
            # This creates a transition from circle to slightly rounded rect
            v.co.x = nx * (curr_w / 2)
            v.co.y = ny * (curr_d / 2)
            v.co.z += step_h
            
        current_verts = new_verts

    # 4. Create the head thickness
    faces = [f for f in bm.faces if len(f.verts) == 32]
    face_top = faces[-1]
    res = bmesh.ops.extrude_face_region(bm, geom=[face_top])
    head_surf_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in head_surf_verts:
        v.co.z += head_thickness

    # 5. Add slight curvature (crown) to the working surface
    for v in head_surf_verts:
        # Distance from center of width (X axis)
        dist_x = abs(v.co.x) / (head_width / 2)
        # Parabolic arc
        v.co.z += 0.15 * (1.0 - dist_x**2)

    # Finalize BMesh
    bm.to_mesh(mesh)
    bm.free()

    # Bevel for squared-off edges and a professional look
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.1
    bevel.segments = 3
    
    # Subdivision Surface to smooth the handle transition
    subsurf = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf.levels = 2

    # Set shading to smooth
    for poly in mesh.polygons:
        poly.use_smooth = True

    # Assign material
    mat = create_spatula_material()
    obj.data.materials.append(mat)
    
    return obj

def main():
    clear_scene()
    spatula_obj = build_spatula()
    
    # Center the spatula at the origin
    total_h = 20.0 + 5.0 + 0.3
    spatula_obj.location.z = -total_h / 2

if __name__ == "__main__":
    main()
