import bpy
import bmesh
import math

def clear_scene():
    """Clear all default objects from the scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, transmission=0.0, roughness=0.5):
    """Create a Principled BSDF material compatible with Blender 5.0."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    shader = nodes.new('ShaderNodeBsdfPrincipled')
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Roughness'].default_value = roughness
    
    # Blender 4.0+ uses 'Transmission Weight' instead of 'Transmission'
    if 'Transmission Weight' in shader.inputs:
        shader.inputs['Transmission Weight'].default_value = transmission
    elif 'Transmission' in shader.inputs:
        shader.inputs['Transmission'].default_value = transmission
    
    output = nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    
    return mat

def create_hexagonal_jar():
    # Parameters
    outer_radius = 1.0
    inner_radius = 0.92
    height = 4.5
    bottom_thickness = 0.2
    lid_thickness = 0.15
    lid_radius = 1.1

    # --- Body Creation using BMesh for a proper hollow shell ---
    bm = bmesh.new()
    
    def get_hex_verts(r, z):
        verts = []
        for i in range(6):
            angle = math.radians(i * 60)
            verts.append(bm.verts.new((r * math.cos(angle), r * math.sin(angle), z)))
        return verts

    # Outer Shell
    outer_bottom = get_hex_verts(outer_radius, 0)
    outer_top = get_hex_verts(outer_radius, height)
    
    # Inner Shell (starting from bottom thickness up to top)
    inner_bottom = get_hex_verts(inner_radius, bottom_thickness)
    inner_top = get_hex_verts(inner_radius, height)

    # Create outer walls
    for i in range(6):
        bm.faces.new((outer_bottom[i], outer_bottom[(i+1)%6], outer_top[(i+1)%6], outer_top[i]))

    # Create inner walls
    for i in range(6):
        bm.faces.new((inner_bottom[i], inner_top[i], inner_top[(i+1)%6], inner_bottom[(i+1)%6]))

    # Close the bottom (ring between outer and inner)
    for i in range(6):
        bm.faces.new((outer_bottom[i], outer_bottom[(i+1)%6], inner_bottom[(i+1)%6], inner_bottom[i]))

    # Close the top rim (ring between outer and inner at height)
    for i in range(6):
        bm.faces.new((outer_top[i], inner_top[i], inner_top[(i+1)%6], outer_top[(i+1)%6]))

    # Finalize body mesh
    mesh_body = bpy.data.meshes.new("JarBody")
    bm.to_mesh(mesh_body)
    bm.free()

    obj_body = bpy.data.objects.new("StorageJar", mesh_body)
    bpy.context.collection.objects.link(obj_body)

    # --- Lid Creation ---
    # Creating a flat disc lid using a cylinder primitive
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64, 
        radius=lid_radius, 
        depth=lid_thickness, 
        location=(0, 0, height + (lid_thickness / 2))
    )
    obj_lid = bpy.context.active_object
    obj_lid.name = "JarLid"

    # --- Materials ---
    # Body: Brownish tinted semi-transparent
    mat_body = create_material(
        "BrownGlass", 
        (0.35, 0.2, 0.1, 1.0), 
        transmission=0.9, 
        roughness=0.05
    )
    obj_body.data.materials.append(mat_body)

    # Lid: Dark flat disc (almost black)
    mat_lid = create_material(
        "DarkLid", 
        (0.02, 0.02, 0.02, 1.0), 
        transmission=0.0, 
        roughness=0.4
    )
    obj_lid.data.materials.append(mat_lid)

if __name__ == "__main__":
    clear_scene()
    create_hexagonal_jar()
