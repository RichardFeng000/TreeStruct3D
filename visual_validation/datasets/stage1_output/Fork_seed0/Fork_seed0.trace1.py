import bpy
import bmesh
import math

def clear_scene():
    """Clear the default scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Create a metallic material with specified color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = 1.0
        bsdf.inputs['Roughness'].default_value = 0.25
    return mat

def create_fork():
    """Procedurally construct a dining fork using BMesh."""
    # Dimensions
    handle_length = 16.0
    handle_radius = 0.3
    taper_factor = 1.2  # Neck is slightly wider than the base of handle
    neck_curvature = 0.8
    head_width = 2.6
    head_depth = 0.2
    tine_length = 5.0
    tine_width = 0.3
    tine_gap = 0.25

    bm = bmesh.new()

    # 1. Create the handle profile (circular)
    res = 16
    verts = []
    for i in range(res):
        angle = (2 * math.pi * i) / res
        x = math.cos(angle) * handle_radius
        z = math.sin(angle) * handle_radius
        verts.append(bm.verts.new((x, 0, z)))

    # Create initial face for the bottom of the handle
    bottom_face = bm.faces.new(verts)

    # 2. Extrude handle with tapering and curvature
    segments = 32
    current_face = bottom_face
    for i in range(1, segments + 1):
        t = i / segments
        
        # Tapering: slightly wider as we go towards the head
        scale = 1.0 + (t * (taper_factor - 1.0))
        
        # Curvature: a slight bend in the neck (the last 30% of handle)
        offset_x = 0
        if t > 0.7:
            curve_t = (t - 0.7) / 0.3
            offset_x = math.sin(curve_t * math.pi / 2) * neck_curvature

        # Extrude
        extrude_result = bmesh.ops.extrude_face_region(bm, geom=[current_face])
        
        # Find the new face and vertices to transform them
        new_verts = [v for v in extrude_result['geom'] if isinstance(v, bmesh.types.BMVert)]
        new_faces = [f for f in extrude_result['geom'] if isinstance(f, bmesh.types.BMFace)]
        
        for v in new_verts:
            v.co.y += (handle_length / segments)
            v.co.x *= scale
            v.co.z *= scale
            v.co.x += offset_x
            
        current_face = new_faces[0]

    # 3. Create the head/shoulder area
    # Current face is at the top of the handle. We expand it into a flat base for tines.
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    last_face = current_face
    center = last_face.calc_center_median()
    
    # Create the wide head block
    v1 = bm.verts.new((center.x - head_width/2, center.y, center.z))
    v2 = bm.verts.new((center.x + head_width/2, center.y, center.z))
    v3 = bm.verts.new((center.x + head_width/2, center.y + 0.5, center.z))
    v4 = bm.verts.new((center.x - head_width/2, center.y + 0.5, center.z))
    head_base_face = bm.faces.new((v1, v2, v3, v4))
    
    # Give the base some thickness
    extrude_head = bmesh.ops.extrude_face_region(bm, geom=[head_base_face])
    for v in [v for v in extrude_head['geom'] if isinstance(v, bmesh.types.BMVert)]:
        v.co.z += head_depth

    # 4. Create the tines
    tine_count = 4
    start_x = center.x - head_width/2 + (tine_width / 2) + (tine_gap / 2)
    
    for i in range(tine_count):
        tx = start_x + i * (tine_width + tine_gap)
        
        # Create a rectangular profile for each tine
        tv1 = bm.verts.new((tx - tine_width/2, center.y + 0.5, center.z))
        tv2 = bm.verts.new((tx + tine_width/2, center.y + 0.5, center.z))
        tv3 = bm.verts.new((tx + tine_width/2, center.y + 0.5 + tine_length, center.z))
        tv4 = bm.verts.new((tx - tine_width/2, center.y + 0.5 + tine_length, center.z))
        tine_face = bm.faces.new((tv1, tv2, tv3, tv4))
        
        # Give tines thickness and taper them slightly at the tips
        extrude_tine = bmesh.ops.extrude_face_region(bm, geom=[tine_face])
        for v in [v for v in extrude_tine['geom'] if isinstance(v, bmesh.types.BMVert)]:
            v.co.z += head_depth
            # Taper tip: move vertices inward at the far end of the tine
            if v.co.y > center.y + 0.5 + (tine_length * 0.7):
                factor = (v.co.y - (center.y + 0.5 + tine_length*0.7)) / (tine_length * 0.3)
                # Move x towards the center of this specific tine
                v.co.x += (tx - v.co.x) * factor * 0.5

    # Clean up and finalize mesh
    bm.to_mesh(bpy.data.meshes.new("ForkMesh"))
    obj = bpy.data.objects.new("Fork", bpy.data.meshes["ForkMesh"])
    bpy.context.collection.objects.link(obj)
    bm.free()

    # Smooth the fork with a subdivision surface modifier
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    # Shade smooth
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    return obj

def main():
    clear_scene()
    
    # Color: dark blue-gray (SlateGray ish)
    color_dark_blue_gray = (0.1, 0.15, 0.2, 1.0)
    material = create_material("ForkMaterial", color_dark_blue_gray)
    
    fork_obj = create_fork()
    fork_obj.data.materials.append(material)
    
    # Position and rotate for "top-down slightly angled" perspective
    fork_obj.location = (0, 0, 0)
    # Rotation: tilt it so the viewer sees the handle and tines clearly
    fork_obj.rotation_euler = (math.radians(-15), 0, math.radians(30))

if __name__ == "__main__":
    main()
