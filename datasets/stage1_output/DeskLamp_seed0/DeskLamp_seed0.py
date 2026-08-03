import bpy
import bmesh
import math

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, specular=0.5, roughness=0.5):
    """Creates a simple BSDF material for Blender 4.0+."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Blender 4.0+ uses 'Base Color' and 'Roughness'. 
    # Specular is handled by 'Specular IOR Level' in newer versions.
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Roughness'].default_value = roughness
    if 'Specular IOR Level' in node_principled.inputs:
        node_principled.inputs['Specular IOR Level'].default_value = specular
    
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_truncated_cone(name, bottom_radius, top_radius, height, location, material):
    """Creates a truncated cone using bmesh."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    segments = 64
    
    # Bottom circle
    bottom_verts = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        x = math.cos(angle) * bottom_radius
        y = math.sin(angle) * bottom_radius
        bottom_verts.append(bm.verts.new((x, y, 0)))
        
    # Top circle
    top_verts = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        x = math.cos(angle) * top_radius
        y = math.sin(angle) * top_radius
        top_verts.append(bm.verts.new((x, y, height)))
        
    # Create faces (side walls)
    for i in range(segments):
        v1 = bottom_verts[i]
        v2 = bottom_verts[(i + 1) % segments]
        v3 = top_verts[(i + 1) % segments]
        v4 = top_verts[i]
        bm.faces.new((v1, v2, v3, v4))
        
    # Cap the bottom and top
    bm.faces.new(bottom_verts)
    bm.faces.new(reversed(top_verts))
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    obj.data.materials.append(material)
    return obj

def create_cylinder(name, radius, height, location, material):
    """Creates a cylinder and sets its material."""
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64, 
        radius=radius, 
        depth=height, 
        location=location
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    return obj

def create_torus_ring(name, radius, thickness, location, material):
    """Creates a torus for the rim."""
    # Removed align='Z' which caused previous failure; defaults to Z axis alignment in WORLD
    bpy.ops.mesh.primitive_torus_add(
        align='WORLD', 
        location=location, 
        major_radius=radius, 
        minor_radius=thickness, 
        major_segments=64, 
        minor_segments=16
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Materials
    mat_dark = create_material("DarkGlossy", (0.02, 0.02, 0.02, 1.0), specular=0.8, roughness=0.1)
    mat_offwhite = create_material("OffWhiteFabric", (0.9, 0.88, 0.8, 1.0), specular=0.1, roughness=0.9)
    
    # Dimensions
    plate_radius = 0.7
    plate_height = 0.05
    base_bottom_r = 0.6
    base_top_r = 0.3
    base_height = 0.4
    stem_radius = 0.08
    stem_height = 0.2
    shade_bottom_r = 0.25
    shade_top_r = 0.6
    shade_height = 0.7

    # Base Plate: positioned at center of its height
    create_cylinder("FootPlate", plate_radius, plate_height, (0, 0, plate_height/2), mat_dark)
    
    # Base Body: bottom sits on top of footplate
    # create_truncated_cone builds from z=0 upwards to base_height
    create_truncated_cone(
        "BaseBody", 
        base_bottom_r, 
        base_top_r, 
        base_height, 
        (0, 0, plate_height), 
        mat_dark
    )
    
    # Stem: center is at (plate + base + stem/2)
    stem_z = plate_height + base_height + (stem_height / 2)
    create_cylinder("Stem", stem_radius, stem_height, (0, 0, stem_z), mat_dark)
    
    # Shade: bottom sits on top of the stem
    shade_obj = create_truncated_cone(
        "Shade", 
        shade_bottom_r, 
        shade_top_r, 
        shade_height, 
        (0, 0, plate_height + base_height + stem_height), 
        mat_offwhite
    )
    
    # Rim: sits at the very top edge of the shade
    rim_z = plate_height + base_height + stem_height + shade_height
    create_torus_ring("Rim", shade_top_r, 0.02, (0, 0, rim_z), mat_dark)

if __name__ == "__main__":
    main()
