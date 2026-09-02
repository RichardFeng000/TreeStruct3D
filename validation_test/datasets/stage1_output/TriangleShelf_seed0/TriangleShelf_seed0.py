import bpy
import bmesh
import math

def clear_scene():
    """Removes all default objects and data from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    # Clear orphan data
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Creates a material with specific PBR properties."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

def create_triangular_shelf(name, size, thickness, z_pos, material):
    """Creates a right-angled triangular shelf mesh."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    # Bottom face vertices (Z-offset for thickness)
    v1 = bm.verts.new((0, 0, z_pos - thickness / 2))
    v2 = bm.verts.new((size, 0, z_pos - thickness / 2))
    v3 = bm.verts.new((0, size, z_pos - thickness / 2))
    
    # Top face vertices
    v4 = bm.verts.new((0, 0, z_pos + thickness / 2))
    v5 = bm.verts.new((size, 0, z_pos + thickness / 2))
    v6 = bm.verts.new((0, size, z_pos + thickness / 2))

    # Create faces: bottom, top and the three sides
    bm.faces.new((v1, v3, v2)) # Bottom
    bm.faces.new((v4, v5, v6)) # Top
    bm.faces.new((v1, v2, v5, v4)) # Side 1
    bm.faces.new((v2, v3, v6, v5)) # Hypotenuse side
    bm.faces.new((v3, v1, v4, v6)) # Side 2

    bm.to_mesh(mesh)
    bm.free()
    obj.active_material = material
    return obj

def create_post(name, x, y, height, radius, material):
    """Creates a vertical cylindrical post using BMesh."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    # Create cylinder (represented as a cone with identical radii)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=radius, radius2=radius, depth=height)
    
    # Offset geometry so post starts at z=0 and goes up to height
    for v in bm.verts:
        v.co.z += height / 2
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = (x, y, 0)
    obj.active_material = material
    return obj

def main():
    clear_scene()

    # Model parameters
    shelf_size = 0.6  # Leg length of the triangle
    shelf_thickness = 0.03
    total_height = 1.2
    post_radius = 0.02
    
    # Materials: Metallic frame (Silver) and Dark shelf surfaces (Charcoal/Black)
    mat_metal = create_material(
        "MetalFrame", 
        color=(0.8, 0.8, 0.8, 1.0), 
        metallic=1.0, 
        roughness=0.25
    )
    mat_dark = create_material(
        "DarkShelf", 
        color=(0.02, 0.02, 0.02, 1.0), 
        metallic=0.0, 
        roughness=0.8
    )

    # Create vertical support posts at the three corners of the triangle
    create_post("Post_Origin", 0, 0, total_height, post_radius, mat_metal)
    create_post("Post_X", shelf_size, 0, total_height, post_radius, mat_metal)
    create_post("Post_Y", 0, shelf_size, total_height, post_radius, mat_metal)

    # Distribute three shelves vertically
    z_positions = [0.15, total_height / 2, total_height - 0.15]
    for i, z in enumerate(z_positions):
        create_triangular_shelf(
            f"Shelf_{i+1}", 
            shelf_size, 
            shelf_thickness, 
            z, 
            mat_dark
        )

if __name__ == "__main__":
    main()
