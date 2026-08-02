import bpy
import bmesh
import math

def clear_scene():
    """Clears default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Creates a simple Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_cylinder(name, radius_bottom, radius_top, height, location, material=None):
    """Creates a cylinder/cone using BMesh."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, 
        cap_ends=True, 
        segments=32, 
        radius1=radius_bottom, 
        radius2=radius_top, 
        depth=height
    )
    bm.to_mesh(mesh)
    bm.free()

    obj.location = location
    if material:
        obj.data.materials.append(material)
    return obj

def create_tray(name, radius, thickness, height_pos, material):
    """Creates a tray with a small lip."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    # Bottom disk
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=radius, radius2=radius, depth=thickness)
    
    # Find the top face to create the lip
    top_face = None
    for f in bm.faces:
        if f.normal.z > 0.9:
            top_face = f
            break
    
    if top_face:
        # Extrude region creates new faces and edges
        extruded = bmesh.ops.extrude_face_region(bm, geom=[top_face])
        verts = [v for v in extruded['geom'] if isinstance(v, bmesh.types.BMVert)]
        
        # Move the extruded vertices up (lip height) and slightly out
        lip_height = 0.015
        lip_outset = 0.005
        for v in verts:
            v.co.z += lip_height
            # Push outwards from center
            dir_vec = v.co.copy()
            dir_vec.z = 0
            if dir_vec.length > 0:
                dir_vec.normalize()
                v.co += dir_vec * lip_outset

    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = (0, 0, height_pos)
    if material:
        obj.data.materials.append(material)
    return obj

def create_shade(name, radius_bottom, radius_top, height, location, material):
    """Creates a tapered shade with thickness."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    # Outer shell
    bmesh.ops.create_cone(
        bm, 
        cap_ends=False, # Shade is hollow
        segments=32, 
        radius1=radius_bottom, 
        radius2=radius_top, 
        depth=height
    )
    
    # To give it a professional look, we'll add a Solidify modifier instead of manual bmesh thickness
    bm.to_mesh(mesh)
    bm.free()

    obj.location = location
    if material:
        obj.data.materials.append(material)

    # Add solidifying thickness to the shade fabric
    mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    mod.thickness = 0.01
    mod.offset = 0 # Center it
    
    return obj

def main():
    clear_scene()

    # Materials
    metal_mat = create_material("MetalSilver", (0.75, 0.75, 0.78, 1.0), metallic=1.0, roughness=0.3)
    fabric_mat = create_material("FabricOffWhite", (0.95, 0.94, 0.85, 1.0), metallic=0.0, roughness=0.8)

    # Dimensions
    base_radius = 0.25
    base_height = 0.03
    pole_radius = 0.018
    pole_height = 1.7
    tray_radius = 0.18
    tray_thickness = 0.01
    tray_z_pos = 0.8 # Position of the tray from ground
    shade_bottom_radius = 0.25
    shade_top_radius = 0.15
    shade_height = 0.4

    # 1. Base - Flat round metallic base
    create_cylinder(
        "Base", 
        base_radius, base_radius, 
        base_height, 
        (0, 0, base_height / 2), 
        material=metal_mat
    )

    # 2. Pole - Tall slender metallic pole
    create_cylinder(
        "Pole", 
        pole_radius, pole_radius, 
        pole_height, 
        (0, 0, (base_height / 2) + (pole_height / 2)), 
        material=metal_mat
    )

    # 3. Tray - Small circular shelf partway up
    create_tray(
        "Tray", 
        tray_radius, 
        tray_thickness, 
        tray_z_pos, 
        metal_mat
    )

    # 4. Shade - Tapered conical off-white fabric shade at the top
    shade_z = (base_height / 2) + pole_height - (shade_height / 2)
    create_shade(
        "Shade", 
        shade_bottom_radius, 
        shade_top_radius, 
        shade_height, 
        (0, 0, shade_z), 
        material=fabric_mat
    )

    # Smooth shading for all objects
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for poly in obj.data.polygons:
                poly.use_smooth = True

if __name__ == "__main__":
    main()
