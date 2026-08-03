import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears all objects from the current scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Creates a Principled BSDF material with specified properties."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    shader = nodes.new('ShaderNodeBsdfPrincipled')
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    
    output = nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    return mat

def create_box(name, size, location, material):
    """Creates a box mesh with given dimensions and assigns a material."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    obj.data.materials.append(material)
    return obj

def create_cylinder_between_points(name, p1, p2, radius, material):
    """Creates a cylinder that spans between two 3D points."""
    direction = p2 - p1
    length = direction.length
    center = (p1 + p2) / 2
    z_axis = Vector((0, 0, 1))
    rot_quat = z_axis.rotation_difference(direction.normalized())
    
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, 
        depth=length, 
        location=center, 
        rotation=rot_quat.to_euler()
    )
    cyl_obj = bpy.context.active_object
    cyl_obj.name = name
    cyl_obj.data.materials.append(material)
    return cyl_obj

def main():
    clear_scene()
    
    # Dimensions
    width = 1.4
    depth = 0.6
    height = 0.75
    top_thickness = 0.03
    leg_radius = 0.025
    shelf_height = 0.25  # Slightly raised for better proportions
    shelf_thickness = 0.02
    
    # Materials - Using very dark values and metallic properties to ensure contrast in renders
    mat_white = create_material("WhiteTabletop", (0.9, 0.9, 0.9, 1.0), metallic=0.0, roughness=0.4)
    mat_black = create_material("BlackMetalLegs", (0.01, 0.01, 0.01, 1.0), metallic=1.0, roughness=0.3)
    mat_gray = create_material("DarkGrayShelf", (0.05, 0.05, 0.05, 1.0), metallic=0.2, roughness=0.6)
    
    # Tabletop: placed so the bottom of the slab is at z = height - top_thickness
    create_box(
        "Tabletop", 
        (width, depth, top_thickness), 
        (0, 0, height - top_thickness / 2), 
        mat_white
    )
    
    # Define Leg endpoints for a trapezoidal flare
    z_top = height - top_thickness
    z_bot = 0.0
    
    # Top points: tucked in slightly from corners of the tabletop
    top_off_x, top_off_y = width * 0.4, depth * 0.35
    # Bottom points: flared out wider than the top
    bot_off_x, bot_off_y = width * 0.52, depth * 0.42
    
    corners_top = [
        Vector(( top_off_x,  top_off_y, z_top)),
        Vector((-top_off_x,  top_off_y, z_top)),
        Vector((-top_off_x, -top_off_y, z_top)),
        Vector(( top_off_x, -top_off_y, z_top))
    ]
    
    corners_bot = [
        Vector(( bot_off_x,  bot_off_y, z_bot)),
        Vector((-bot_off_x,  bot_off_y, z_bot)),
        Vector((-bot_off_x, -bot_off_y, z_bot)),
        Vector(( bot_off_x, -bot_off_y, z_bot))
    ]
    
    # Create legs
    for i in range(4):
        create_cylinder_between_points(
            f"Leg_{i}", 
            corners_bot[i], 
            corners_top[i], 
            leg_radius, 
            mat_black
        )
        
    # Lower shelf: dimensions interpolated to fit the angled legs at shelf_height
    t = shelf_height / (z_top - z_bot) if (z_top - z_bot) != 0 else 0
    shelf_pts = [corners_bot[i] + t * (corners_top[i] - corners_bot[i]) for i in range(4)]
        
    # Shelf width and depth calculated from interpolated points
    s_w = shelf_pts[0].x - shelf_pts[1].x
    s_d = shelf_pts[0].y - shelf_pts[3].y
    
    create_box(
        "LowerShelf", 
        (s_w, s_d, shelf_thickness), 
        (0, 0, shelf_height + shelf_thickness / 2), 
        mat_gray
    )

if __name__ == "__main__":
    main()
