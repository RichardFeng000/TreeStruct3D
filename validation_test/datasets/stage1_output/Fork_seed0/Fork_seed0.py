import bpy
import bmesh
import math

def clear_scene():
    """Clear default scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Create metallic dark blue-gray material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = 1.0
        bsdf.inputs['Roughness'].default_value = 0.3
    return mat

def create_fork():
    """Build a dining fork using BMesh."""
    bm = bmesh.new()

    # Constants
    handle_len = 14.0
    handle_rad_start = 0.2
    handle_rad_end = 0.25
    head_width = 2.5
    head_thickness = 0.2
    tine_length = 5.0
    tine_width = 0.2
    tine_gap = 0.2
    num_tines = 4

    # --- Handle & Neck ---
    res = 16
    segments = 40
    verts = []
    for i in range(res):
        angle = (2 * math.pi * i) / res
        verts.append(bm.verts.new((math.cos(angle)*handle_rad_start, 0, math.sin(angle)*handle_rad_start)))
    
    face = bm.faces.new(verts)
    
    # Extrude handle along Y
    curr_face = face
    for i in range(1, segments + 1):
        t = i / segments
        scale = 1.0 + (t * (handle_rad_end/handle_rad_start - 1.0))
        
        # Curve the neck slightly upward and forward at the end
        offset_z = 0
        offset_y_extra = 0
        if t > 0.7:
            curve_t = (t - 0.7) / 0.3
            offset_z = math.sin(curve_t * math.pi/2) * 0.8
        
        extrude_res = bmesh.ops.extrude_face_region(bm, geom=[curr_face])
        new_verts = [v for v in extrude_res['geom'] if isinstance(v, bmesh.types.BMVert)]
        new_faces = [f for f in extrude_res['geom'] if isinstance(f, bmesh.types.BMFace)]
        
        for v in new_verts:
            v.co.y += (handle_len / segments)
            v.co.x *= scale
            v.co.z = (v.co.z * scale) + offset_z
        
        curr_face = new_faces[0]

    # --- Transition to Head/Shoulder ---
    # The last face is at the top of the neck
    center = curr_face.calc_center_median()
    
    # Create a flat rectangular head base
    v1 = bm.verts.new((center.x - head_width/2, center.y, center.z - head_thickness/2))
    v2 = bm.verts.new((center.x + head_width/2, center.y, center.z - head_thickness/2))
    v3 = bm.verts.new((center.x + head_width/2, center.y, center.z + head_thickness/2))
    v4 = bm.verts.new((center.x - head_width/2, center.y, center.z + head_thickness/2))
    head_face = bm.faces.new((v1, v2, v3, v4))

    # --- Tines ---
    # Calculate starting X for tines to be centered
    total_tine_span = (num_tines * tine_width) + ((num_tines - 1) * tine_gap)
    start_x = center.x - total_tine_span / 2

    for i in range(num_tines):
        tx = start_x + i * (tine_width + tine_gap) + tine_width/2
        
        # Each tine is a small box extending along Y
        tw1 = bm.verts.new((tx - tine_width/2, center.y, center.z - head_thickness/2))
        tw2 = bm.verts.new((tx + tine_width/2, center.y, center.z - head_thickness/2))
        tw3 = bm.verts.new((tx + tine_width/2, center.y + tine_length, center.z - head_thickness/2))
        tw4 = bm.verts.new((tx - tine_width/2, center.y + tine_length, center.z - head_thickness/2))
        tine_bot = bm.faces.new((tw1, tw2, tw3, tw4))
        
        tw5 = bm.verts.new((tx - tine_width/2, center.y, center.z + head_thickness/2))
        tw6 = bm.verts.new((tx + tine_width/2, center.y, center.z + head_thickness/2))
        tw7 = bm.verts.new((tx + tine_width/2, center.y + tine_length, center.z + head_thickness/2))
        tw8 = bm.verts.new((tx - tine_width/2, center.y + tine_length, center.z + head_thickness/2))
        tine_top = bm.faces.new((tw5, tw6, tw7, tw8))
        
        # Connect sides of tines
        bm.faces.new((tw1, tw5, tw8, tw4)) # Left
        bm.faces.new((tw2, tw6, tw7, tw3)) # Right
        bm.faces.new((tw4, tw8, tw7, tw3)) # Tip

    # Join the head face to the tines and handle by merging close vertices
    # The current setup has overlapping geometry; we'll use a simple union or just merge
    bm.verts.ensure_lookup_table()
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)

    # Finalize mesh
    mesh = bpy.data.meshes.new("ForkMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("Fork", mesh)
    bpy.context.collection.objects.link(obj)
    bm.free()

    # Smoothing and modifiers
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    return obj

def main():
    clear_scene()
    
    # Dark blue-gray color (Slate gray)
    color_dark_blue_gray = (0.12, 0.15, 0.2, 1.0)
    mat = create_material("ForkMat", color_dark_blue_gray)
    
    fork = create_fork()
    fork.data.materials.append(mat)
    
    # Top-down slightly angled perspective
    fork.location = (0, 0, 0)
    fork.rotation_euler = (math.radians(-60), 0, math.radians(45))

if __name__ == "__main__":
    main()
