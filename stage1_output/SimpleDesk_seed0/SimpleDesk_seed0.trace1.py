import bpy
import bmesh
import math
from mathutils import Vector, Quaternion

def clear_scene():
    """Clears all objects from the current scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple Principled BSDF material with a given color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    shader = nodes.new('ShaderNodeBsdfPrincipled')
    shader.inputs['Base Color'].default_value = color
    output = nodes.new('ShaderNodeOutputMaterial')
    
    links = mat.node_tree.links
    links.new(shader.outputs['BSDF'], output.inputs['Surface'])
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
    
    # Calculate rotation to align Z-axis with the direction vector
    z_axis = Vector((0, 0, 1))
    rot_quat = z_axis.rotation_difference(direction.normalized())
    
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Manual cylinder construction using BMesh for reliability across versions
    bmesh.ops.create_circle(bm, segments=16, radius=radius, cap_ends=False)
    # Extrude the circle along Z axis
    # To extrude properly in BMesh: select all verts and extrude
    res = bmesh.ops.extrude_edge_only(bm, edges=bm.edges)
    verts = [v for v in res['geom'] if isinstance(v, bpy.types.BMeshVert)]
    for v in verts:
        v.co.z += length
    
    # Cap the ends
    bmesh.ops.contextual_create(bm, geom=bm.verts) # This is too generic
    # Better cap method: find vertices at z=0 and z=length and create faces
    # But we already have a circle at 0 and one at length.
    # Let's use the standard primitive operator instead for cleanliness
    # Since we are creating separate objects, bpy.ops is acceptable if handled carefully.
    bm.free()
    
    # Using primitives via ops:
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, 
        depth=length, 
        location=center, 
        rotation=rot_quat
    )
    cyl_obj = bpy.context.active_object
    cyl_obj.name = name
    cyl_obj.data.materials.append(material)
    
    # Remove the dummy object created by bmesh above
    bpy.data.objects.remove(obj, do_unlink=True)
    return cyl_obj

def main():
    clear_scene()
    
    # Dimensions
    width = 1.4
    depth = 0.6
    height = 0.75
    top_thickness = 0.03
    leg_radius = 0.025
    shelf_height = 0.18
    shelf_thickness = 0.02
    
    # Materials
    mat_white = create_material("WhiteTabletop", (0.95, 0.95, 0.95, 1.0))
    mat_black = create_material("BlackMetal", (0.02, 0.02, 0.02, 1.0))
    mat_gray = create_material("DarkGrayShelf", (0.18, 0.18, 0.18, 1.0))
    
    # Tabletop
    create_box(
        "Tabletop", 
        (width, depth, top_thickness), 
        (0, 0, height - top_thickness / 2), 
        mat_white
    )
    
    # Define Leg endpoints for a trapezoidal flare
    # Top points: tucked in slightly from corners
    # Bottom points: flared out slightly
    top_off_x = (width / 2) * 0.9
    top_off_y = (depth / 2) * 0.85
    bot_off_x = (width / 2) * 1.05
    bot_off_y = (depth / 2) * 0.95
    z_top = height - top_thickness
    z_bot = 0.0
    
    corners_top = [
        Vector((top_off_x, top_off_y, z_top)),
        Vector((-top_off_x, top_off_y, z_top)),
        Vector((-top_off_x, -top_off_y, z_top)),
        Vector((top_off_x, -top_off_y, z_top))
    ]
    
    corners_bot = [
        Vector((bot_off_x, bot_off_y, z_bot)),
        Vector((-bot_off_x, bot_off_y, z_bot)),
        Vector((-bot_off_x, -bot_off_y, z_bot)),
        Vector((bot_off_x, -bot_off_y, z_bot))
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
        
    # Lower shelf: dimensions interpolated based on height
    t = shelf_height / (z_top - z_bot)
    shelf_pts = []
    for i in range(4):
        p = corners_bot[i] + t * (corners_top[i] - corners_bot[i])
        shelf_pts.append(p)
        
    # Shelf dimensions based on the interpolated points
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
