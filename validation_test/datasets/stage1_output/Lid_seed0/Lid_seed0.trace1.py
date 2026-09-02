import bpy
import bmesh
import math

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple diffuse material with a specific color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Create Principled BSDF
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_bsdf.inputs['Base Color'].default_value = color
    
    # Create Output node
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Link them
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_pot_lid():
    # Dimensions
    radius = 5.0
    thickness = 0.2
    dome_height = 0.4
    rim_width = 0.15
    knob_radius = 0.4
    knob_total_height = 1.2

    # Materials
    beige_mat = create_material("Beige", (0.93, 0.85, 0.78, 1.0)) # Light pinkish-beige
    pink_mat = create_material("Pink", (1.0, 0.4, 0.6, 1.0))      # Bright Pink
    blue_mat = create_material("DarkBlue", (0.02, 0.05, 0.25, 1.0)) # Dark Blue

    # --- Create Lid Body ---
    lid_mesh = bpy.data.meshes.new("LidMesh")
    bm = bmesh.new()
    
    # Create a circular base disk (top face)
    bmesh.ops.create_circle(bm, cap_ends=True, radius=radius, segments=64)
    
    # Slightly dome the profile: z = h * (1 - r^2/R^2)
    for v in bm.verts:
        dist_sq = v.co.x**2 + v.co.y**2
        v.co.z = dome_height * (1.0 - dist_sq / (radius**2))

    # Extrude for thickness
    bm.edges.index_update()
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.extrude_face_region(bm, geom=geom)
    
    # Move extruded vertices down
    verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in verts_extruded:
        v.co.z -= thickness

    # Create a rim by beveling the outer edges
    bm.edges.index_update()
    # Find the perimeter edges of the bottom face
    rim_edges = [e for e in bm.edges if all(round(v.co.length, 3) >= radius - 0.1 for v in e.verts)]
    bmesh.ops.bevel(bm, geom=rim_edges, offset=rim_width, segments=4, affect='EDGES')

    bm.to_mesh(lid_mesh)
    bm.free()
    
    lid_obj = bpy.data.objects.new("PotLid", lid_mesh)
    bpy.context.collection.objects.link(lid_obj)
    lid_obj.data.materials.append(beige_mat)

    # --- Create Knob Handle ---
    def create_knob_part(name, radius, height, z_start, material, rounded_top=False):
        mesh = bpy.data.meshes.new(name + "Mesh")
        bm_k = bmesh.new()
        bmesh.ops.create_cylinder(
            bm_k, 
            cap_ends=True, 
            radius=radius, 
            depth=height, 
            segments=32
        )
        # Shift Z so the bottom is at z_start
        for v in bm_k.verts:
            v.co.z += (z_start + height/2)
            
        if rounded_top:
            bm_k.edges.index_update()
            top_edges = [e for e in bm_k.edges if all(abs(v.co.z - (z_start + height)) < 0.1 for v in e.verts)]
            bmesh.ops.bevel(bm_k, geom=top_edges, offset=0.2, segments=8, affect='EDGES')

        bm_k.to_mesh(mesh)
        bm_k.free()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(material)
        return obj

    # Split knob into two halves
    half_h = knob_total_height / 2
    knob_bottom = create_knob_part("KnobBottom", knob_radius, half_h, dome_height, blue_mat, False)
    knob_top = create_knob_part("KnobTop", knob_radius, half_h, dome_height + half_h, pink_mat, True)

    # Join all parts into one object for clean output
    bpy.ops.object.select_all(action='DESELECT')
    lid_obj.select_set(True)
    knob_bottom.select_set(True)
    knob_top.select_set(True)
    bpy.context.view_layer.objects.active = lid_obj
    bpy.ops.object.join()

clear_scene()
create_pot_lid()
