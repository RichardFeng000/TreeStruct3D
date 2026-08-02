import bpy
import bmesh
import math

def clear_scene():
    """Clears all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple diffuse material with metallic properties."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    node_bsdf.inputs['Base Color'].default_value = color
    node_bsdf.inputs['Roughness'].default_value = 0.15
    node_bsdf.inputs['Metallic'].default_value = 0.9
    
    mat.node_tree.links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_spoon():
    # Parameters
    handle_length = 18.0
    handle_width = 0.7
    handle_thickness = 0.35
    bowl_rx = 2.4  # Width of bowl (X)
    bowl_ry = 3.6  # Length of bowl (Y)
    bowl_rz = 1.1  # Depth/Thickness of bowl base (Z)
    bowl_scoop_depth = 1.5 # How deep the dip is

    mesh = bpy.data.meshes.new("SpoonMesh")
    obj = bpy.data.objects.new("DiningSpoon", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # --- Construct the Bowl ---
    res_u, res_v = 24, 24
    bowl_verts = []
    for i in range(res_u + 1):
        phi = math.pi * i / res_u
        for j in range(res_v + 1):
            theta = 2 * math.pi * j / res_v
            
            x = bowl_rx * math.sin(phi) * math.cos(theta)
            y = bowl_ry * math.sin(phi) * math.sin(theta)
            z = bowl_rz * math.cos(phi)
            
            # Scoop out the center for the "bowl" part
            if z > -0.2:
                dist_sq = (x*x)/(bowl_rx**2) + (y*y)/(bowl_ry**2)
                dip = bowl_scoop_depth * (1.0 - dist_sq) if dist_sq < 1.0 else 0
                z -= max(0, dip)

            bowl_verts.append(bm.verts.new((x, y, z)))

    for i in range(res_u):
        for j in range(res_v):
            v1 = bowl_verts[i * (res_v + 1) + j]
            v2 = bowl_verts[(i + 1) * (res_v + 1) + j]
            v3 = bowl_verts[(i + 1) * (res_v + 1) + (j + 1)]
            v4 = bowl_verts[i * (res_v + 1) + (j + 1)]
            bm.faces.new((v1, v2, v3, v4))

    # --- Construct the Handle ---
    handle_start_y = bowl_ry * 0.7
    handle_end_y = handle_start_y + handle_length
    
    res_h = 20
    half_w = handle_width / 2
    half_t = handle_thickness / 2
    
    handle_rings = []
    for step in range(res_h + 1):
        t = step / res_h
        y_pos = handle_start_y + t * handle_length
        scale = 1.0 - (t * 0.4) # Taper the end
        cw = half_w * scale
        ct = half_t * scale
        
        v1 = bm.verts.new((-cw, y_pos, ct))
        v2 = bm.verts.new((cw, y_pos, ct))
        v3 = bm.verts.new((cw, y_pos, -ct))
        v4 = bm.verts.new((-cw, y_pos, -ct))
        handle_rings.append([v1, v2, v3, v4])

    for i in range(res_h):
        r1 = handle_rings[i]
        r2 = handle_rings[i+1]
        bm.faces.new((r1[0], r1[1], r2[1], r2[0]))
        bm.faces.new((r1[1], r1[2], r2[2], r2[1]))
        bm.faces.new((r1[2], r1[3], r2[3], r2[2]))
        bm.faces.new((r1[3], r1[0], r2[0], r2[3]))

    end_ring = handle_rings[-1]
    bm.faces.new((end_ring[0], end_ring[1], end_ring[2], end_ring[3]))

    # Handle-to-Bowl Connection: remove overlapping vertices to allow Subdiv to merge them
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.2)

    bm.to_mesh(mesh)
    bm.free()

    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 3
    subsurf.render_levels = 3
    
    for poly in mesh.polygons:
        poly.use_smooth = True

    # Calculate centering based on dimensions used inside the function
    total_y_extent = handle_end_y + bowl_ry * 0.5
    center_offset_y = - (total_y_extent / 2)
    obj.location.y = center_offset_y

    return obj

def main():
    clear_scene()
    
    spoon_obj = create_spoon()
    
    # Dark blue-gray color (R, G, B, A)
    color = (0.12, 0.15, 0.2, 1.0)
    mat = create_material("SpoonMat", color)
    spoon_obj.data.materials.append(mat)

if __name__ == "__main__":
    main()
