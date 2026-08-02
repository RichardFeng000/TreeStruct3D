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
    """Creates a Principled BSDF material."""
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

def create_leg(name, p1, p2, thickness, material):
    """Creates a square-profile leg between two points."""
    direction = p2 - p1
    length = direction.length
    center = (p1 + p2) / 2
    
    # Create the box for the leg
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    # Scale to be a long thin beam
    for v in bm.verts:
        v.co.x *= thickness
        v.co.y *= thickness
        v.co.z *= length
    
    bm.to_mesh(mesh)
    bm.free()
    
    # Align and position
    obj.location = center
    z_axis = Vector((0, 0, 1))
    rot_quat = z_axis.rotation_difference(direction.normalized())
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = rot_quat
    
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Dimensions
    width = 1.4
    depth = 0.6
    height = 0.75
    top_thickness = 0.03
    leg_thickness = 0.03
    shelf_height = 0.2
    shelf_thickness = 0.02
    
    # Materials - High contrast for clear visual distinction in renders
    mat_white = create_material("WhiteTabletop", (1.0, 1.0, 1.0, 1.0), metallic=0.0, roughness=0.3)
    mat_black = create_material("BlackMetalLegs", (0.02, 0.02, 0.02, 1.0), metallic=0.8, roughness=0.4)
    # Dark gray shelf: low color value and high roughness to prevent highlights from washing it out
    mat_gray = create_material("DarkGrayShelf", (0.1, 0.1, 0.1, 1.0), metallic=0.0, roughness=0.8)
    
    # Tabletop
    create_box(
        "Tabletop", 
        (width, depth, top_thickness), 
        (0, 0, height - top_thickness / 2), 
        mat_white
    )
    
    z_top = height - top_thickness
    z_bot = 0.0
    
    # Define Leg endpoints for trapezoidal flare
    # Top points slightly inset from the table edges
    t_ox, t_oy = width * 0.42, depth * 0.35
    # Bottom points flared further out
    b_ox, b_oy = width * 0.52, depth * 0.42
    
    corners_top = [
        Vector(( t_ox,  t_oy, z_top)),
        Vector((-t_ox,  t_oy, z_top)),
        Vector((-t_ox, -t_oy, z_top)),
        Vector(( t_ox, -t_oy, z_top))
    ]
    
    corners_bot = [
        Vector(( b_ox,  b_oy, z_bot)),
        Vector((-b_ox,  b_oy, z_bot)),
        Vector((-b_ox, -b_oy, z_bot)),
        Vector(( b_ox, -b_oy, z_bot))
    ]
    
    # Create legs as square profiles for a "frame" look
    for i in range(4):
        create_leg(
            f"Leg_{i}", 
            corners_bot[i], 
            corners_top[i], 
            leg_thickness, 
            mat_black
        )
        
    # Lower shelf interpolation for placement
    t = shelf_height / (z_top - z_bot) if (z_top - z_bot) != 0 else 0
    shelf_pts = [corners_bot[i] + t * (corners_top[i] - corners_bot[i]) for i in range(4)]
        
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
