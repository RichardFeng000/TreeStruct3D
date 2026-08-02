import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clear all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Create a simple diffuse material with a specific color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Principled BSDF is standard in 5.0
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_bsdf.inputs['Base Color'].default_value = color
    node_bsdf.inputs['Roughness'].default_value = 0.9 # Fibers are matte
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_coconut():
    # Constants
    RADIUS = 1.0
    NUM_HAIRS = 8000
    FIBER_MIN_LEN = 0.15
    FIBER_MAX_LEN = 0.35
    BEVEL_DEPTH = 0.004 # Thinness of hair
    
    # Materials
    # Top: warm golden tan with reddish-orange tints
    mat_top = create_material("Mat_Hairs_Top", (0.6, 0.35, 0.15, 1.0))
    # Bottom: lighter cream-yellow
    mat_bot = create_material("Mat_Hairs_Bot", (0.9, 0.82, 0.6, 1.0))

    # Create the core sphere
    # Corrected arguments for Blender primitive_uv_sphere_add: segments and ring_count
    bpy.ops.mesh.primitive_uv_sphere_add(radius=RADIUS, segments=32, ring_count=16)
    core = bpy.context.active_object
    core.name = "CoconutCore"
    
    # To ensure no smooth surface is visible, the core can be hidden or just covered by hairs
    # We'll keep it there as a structural base but it will be completely buried.

    # Create two curve objects to separate materials (top and bottom)
    curve_data_top = bpy.data.curves.new('HairsTop', type='CURVE')
    curve_data_top.dimensions = '3D'
    curve_data_top.bevel_depth = BEVEL_DEPTH
    curve_data_top.bevel_resolution = 2
    curve_obj_top = bpy.data.objects.new('HairsTop', curve_data_top)
    bpy.context.collection.objects.link(curve_obj_top)
    curve_obj_top.active_material = mat_top

    curve_data_bot = bpy.data.curves.new('HairsBot', type='CURVE')
    curve_data_bot.dimensions = '3D'
    curve_data_bot.bevel_depth = BEVEL_DEPTH
    curve_data_bot.bevel_resolution = 2
    curve_obj_bot = bpy.data.objects.new('HairsBot', curve_data_bot)
    bpy.context.collection.objects.link(curve_obj_bot)
    curve_obj_bot.active_material = mat_bot

    # Use Fibonacci Spiral for a very even but organic distribution of hair roots
    golden_ratio = (1 + 5**0.5) / 2
    
    for i in range(NUM_HAIRS):
        # Spherical coordinates via Fibonacci spiral
        z = 1 - (2 * i / float(NUM_HAIRS - 1))
        radius_at_z = math.sqrt(max(0, 1 - z*z))
        theta = 2 * math.pi * i / golden_ratio
        
        root_pos = Vector((
            RADIUS * radius_at_z * math.cos(theta),
            RADIUS * radius_at_z * math.sin(theta),
            RADIUS * z
        ))
        
        # Determine length and random curvature
        length = random.uniform(FIBER_MIN_LEN, FIBER_MAX_LEN)
        
        # Normal vector for the root is just root_pos since it's a unit sphere
        normal = root_pos.normalized()
        
        # Create 3 points per fiber to allow some bending/tangle
        # Point 0: Root
        # Point 1: Middle (offset for curve)
        # Point 2: Tip
        
        noise_offset = Vector((
            random.uniform(-0.1, 0.1),
            random.uniform(-0.1, 0.1),
            random.uniform(-0.1, 0.1)
        ))
        
        p0 = root_pos
        p1 = root_pos + (normal * (length * 0.5)) + noise_offset
        p2 = root_pos + (normal * length) + (noise_offset * 1.8) # More tip variance for "messy" look
        
        # Assign to top or bottom object based on z coordinate
        target_curve = curve_data_top if z >= 0 else curve_data_bot
        
        spline = target_curve.splines.new('POLY')
        spline.points.add(2) # Starts with 1, add 2 more to make it 3 points
        
        # In 'POLY' splines, the points are stored as Vector4s (x, y, z, w)
        spline.points[0].co = (p0.x, p0.y, p0.z, 1.0)
        spline.points[1].co = (p1.x, p1.y, p1.z, 1.0)
        spline.points[2].co = (p2.x, p2.y, p2.z, 1.0)

if __name__ == "__main__":
    clear_scene()
    create_coconut()
