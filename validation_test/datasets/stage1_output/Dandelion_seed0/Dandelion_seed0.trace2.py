import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_stem(start, end, curvature=0.5):
    """Creates a slender, gently curving stem using a curve object."""
    curve_data = bpy.data.curves.new('StemCurve', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 0.015
    curve_data.bevel_resolution = 3

    polyline = curve_data.splines.new('BEZIER')
    
    # Midpoint for curvature to make it a gentle arc
    mid = (start + end) * 0.5 + Vector((curvature, curvature * 0.2, 0))
    
    points = [start, mid, end]
    polyline.bezier_points.add(len(points) - 1)
    
    for i, p in enumerate(points):
        bp = polyline.bezier_points[i]
        bp.co = p
        # In Blender 5.0, the correct enum is 'AUTO', not 'AUTOMATIC'
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'

    stem_obj = bpy.data.objects.new('Stem', curve_data)
    bpy.context.collection.objects.link(stem_obj)
    
    green_mat = create_material('StemGreen', (0.1, 0.3, 0.05, 1.0))
    stem_obj.data.materials.append(green_mat)
    return stem_obj

def create_puffball(center, radius, seed_count=200, scale=1.0, flattened=False):
    """Creates a spherical cluster of dandelion seeds using Curves for thin filaments."""
    curve_data = bpy.data.curves.new('PuffballCurve', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 0.004
    curve_data.bevel_resolution = 2

    # Material for the seeds
    white_mat = create_material('SeedWhite', (0.95, 0.95, 0.95, 1.0))

    for _ in range(seed_count):
        # Uniformly distribute points on a sphere
        phi = random.uniform(0, 2 * math.pi)
        cos_theta = random.uniform(-1, 1)
        sin_theta = math.sqrt(max(0, 1 - cos_theta**2))
        
        dir_vec = Vector((
            sin_theta * math.cos(phi),
            sin_theta * math.sin(phi),
            cos_theta
        ))
        
        # Base of the seed (center of puffball) to tip of beak
        start_p = center
        end_p = center + dir_vec * (radius * scale)
        
        if flattened:
            # Flatten seeds if it's a fallen head
            end_p.z *= 0.4
            
        # Create the central stalk of the seed (the beak)
        stalk = curve_data.splines.new('BEZIER')
        stalk.bezier_points.add(1)
        stalk.bezier_points[0].co = start_p
        stalk.bezier_points[0].handle_left_type = 'AUTO'
        stalk.bezier_points[0].handle_right_type = 'AUTO'
        stalk.bezier_points[1].co = end_p
        stalk.bezier_points[1].handle_left_type = 'AUTO'
        stalk.bezier_points[1].handle_right_type = 'AUTO'
        
        # Create the "parachute" hairs (the pappus) at the tip
        hair_count = random.randint(8, 15)
        hair_length = radius * 0.3 * scale
        
        # Define local coordinate system for hair spread
        if abs(dir_vec.z) < 0.9:
            up = Vector((0, 0, 1))
        else:
            up = Vector((0, 1, 0))
            
        ortho_v1 = up.cross(dir_vec).normalized()
        ortho_v2 = dir_vec.cross(ortho_v1).normalized()
        
        for j in range(hair_count):
            angle = (2 * math.pi / hair_count) * j
            # Spread hairs slightly outwards from the direction of the beak
            spread = 0.6
            hair_dir = (dir_vec + ortho_v1 * math.cos(angle) * spread + ortho_v2 * math.sin(angle) * spread).normalized()
            hair_end = end_p + hair_dir * hair_length
            
            hair_spline = curve_data.splines.new('BEZIER')
            hair_spline.bezier_points.add(1)
            hair_spline.bezier_points[0].co = end_p
            hair_spline.bezier_points[0].handle_left_type = 'AUTO'
            hair_spline.bezier_points[0].handle_right_type = 'AUTO'
            hair_spline.bezier_points[1].co = hair_end
            hair_spline.bezier_points[1].handle_left_type = 'AUTO'
            hair_spline.bezier_points[1].handle_right_type = 'AUTO'

    puff_obj = bpy.data.objects.new('Puffball', curve_data)
    bpy.context.collection.objects.link(puff_obj)
    puff_obj.data.materials.append(white_mat)
    return puff_obj

def main():
    clear_scene()
    
    # Parameters
    stem_start = Vector((0, 0, 0))
    stem_end = Vector((0.15, -0.1, 4.0)) # Slightly elevated end point
    puffball_radius = 0.7
    
    # 1. Create the main stem
    create_stem(stem_start, stem_end, curvature=0.6)
    
    # 2. Create the main head on top of the stem
    create_puffball(stem_end, puffball_radius, seed_count=250)
    
    # 3. Create a fallen puffball at the base
    fallen_center = Vector((0.6, 0.4, 0))
    fallen_radius = puffball_radius * 0.6
    fallen = create_puffball(fallen_center, fallen_radius, seed_count=100, scale=0.8, flattened=True)
    
    # Rotate the fallen one to look natural
    fallen.rotation_euler = (
        random.uniform(0.2, 0.8), 
        random.uniform(0.2, 0.8), 
        random.uniform(0, 6.28)
    )

if __name__ == "__main__":
    main()
