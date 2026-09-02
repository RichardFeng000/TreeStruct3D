import bpy
import bmesh
import math
from mathutils import Vector, Matrix

def clear_scene():
    """Removes all default objects from the scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_central_post(radius, height):
    """Creates the central support pillar."""
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32, 
        radius=radius, 
        depth=height, 
        location=(0, 0, height / 2)
    )
    post = bpy.context.active_object
    post.name = "CentralPost"
    return post

def create_staircase_geometry(num_steps, inner_r, outer_r, thickness, step_height, angle_per_step):
    """Creates all treads as a single mesh object."""
    bm = bmesh.new()
    angle_rad_step = math.radians(angle_per_step)

    for i in range(num_steps):
        current_angle = i * angle_rad_step
        z_pos = i * step_height
        
        cos_a = math.cos(current_angle)
        sin_a = math.sin(current_angle)
        cos_next = math.cos(current_angle + angle_rad_step)
        sin_next = math.sin(current_angle + angle_rad_step)

        # Top face vertices
        v0 = bm.verts.new(Vector((inner_r * cos_a, inner_r * sin_a, z_pos)))
        v1 = bm.verts.new(Vector((outer_r * cos_a, outer_r * sin_a, z_pos)))
        v2 = bm.verts.new(Vector((outer_r * cos_next, outer_r * sin_next, z_pos)))
        v3 = bm.verts.new(Vector((inner_r * cos_next, inner_r * sin_next, z_pos)))
        
        # Bottom face vertices
        v4 = bm.verts.new(Vector((inner_r * cos_a, inner_r * sin_a, z_pos - thickness)))
        v5 = bm.verts.new(Vector((outer_r * cos_a, outer_r * sin_a, z_pos - thickness)))
        v6 = bm.verts.new(Vector((outer_r * cos_next, outer_r * sin_next, z_pos - thickness)))
        v7 = bm.verts.new(Vector((inner_r * cos_next, inner_r * sin_next, z_pos - thickness)))

        # Create the faces of the wedge
        bm.faces.new((v0, v1, v2, v3)) # Top
        bm.faces.new((v4, v7, v6, v5)) # Bottom
        bm.faces.new((v0, v1, v5, v4)) # Side 1 (Inner-Outer)
        bm.faces.new((v1, v2, v6, v5)) # Side 2 (Outer edge)
        bm.faces.new((v2, v3, v7, v6)) # Side 3 (Outer-Inner)
        bm.faces.new((v3, v0, v4, v7)) # Side 4 (Inner edge)

    mesh = bpy.data.meshes.new("Treads")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("StaircaseTreads", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_handrail(num_steps, outer_r, step_height, angle_per_step, rail_height):
    """Creates the elegant spiral handrail using a curve."""
    curve_data = bpy.data.curves.new('HandrailCurve', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 0.04
    curve_data.bevel_resolution = 6

    polyline = curve_data.splines.new('BEZIER')
    # Need to add points first; polyline starts with 1 point by default
    polyline.bezier_points.add(num_steps)
    
    angle_rad_step = math.radians(angle_per_step)
    
    for i in range(num_steps + 1):
        angle_rad = i * angle_rad_step
        z_pos = (i * step_height) + rail_height
        x = outer_r * math.cos(angle_rad)
        y = outer_r * math.sin(angle_rad)
        
        p = polyline.bezier_points[i]
        p.co = Vector((x, y, z_pos))
        p.handle_left_type = 'AUTO'
        p.handle_right_type = 'AUTO'

    rail_obj = bpy.data.objects.new('Handrail', curve_data)
    bpy.context.collection.objects.link(rail_obj)
    return rail_obj

def create_balusters(num_steps, outer_r, step_height, angle_per_step, rail_height):
    """Creates vertical posts connecting the treads to the handrail."""
    bm = bmesh.new()
    angle_rad_step = math.radians(angle_per_step)
    baluster_radius = 0.025

    for i in range(num_steps):
        angle_rad = i * angle_rad_step
        z_start = i * step_height
        # The baluster goes from tread top to handrail height above the tread
        z_mid = z_start + (rail_height / 2)
        x = outer_r * math.cos(angle_rad)
        y = outer_r * math.sin(angle_rad)

        # Create a small cylinder for each baluster
        # Corrected Matrix.Rotation call: angle, size(4), axis
        rot_mat = Matrix.Rotation(math.pi / 2, 4, (1, 0, 0))
        trans_mat = Matrix.Translation((x, y, z_mid))
        
        bmesh.ops.create_cone(
            bm, 
            cap_ends=True, 
            segments=12, 
            radius1=baluster_radius, 
            radius2=baluster_radius, 
            depth=rail_height, 
            matrix=trans_mat @ rot_mat
        )

    mesh = bpy.data.meshes.new("Balusters")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Balusters", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def run():
    # Parameters
    post_radius = 0.25
    tread_width = 1.1
    outer_radius = post_radius + tread_width
    tread_thickness = 0.06
    step_height = 0.18
    angle_per_step = 22 # Degrees
    num_steps = 32        
    rail_height = 0.95
    total_height = num_steps * step_height

    clear_scene()
    
    # 1. Central Column
    create_central_post(post_radius, total_height)
    
    # 2. Treads (Wedge-shaped stairs)
    create_staircase_geometry(num_steps, post_radius, outer_radius, tread_thickness, step_height, angle_per_step)
    
    # 3. Handrail (The spiraling top)
    create_handrail(num_steps, outer_radius, step_height, angle_per_step, rail_height)
    
    # 4. Balusters (Connecting posts)
    create_balusters(num_steps, outer_radius, step_height, angle_per_step, rail_height)

if __name__ == "__main__":
    run()
