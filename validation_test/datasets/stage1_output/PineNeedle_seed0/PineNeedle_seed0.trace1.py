import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Clears the default scene objects."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_pine_needle_material():
    """Creates a brownish-tan material for the pine needle."""
    mat = bpy.data.materials.new(name="PineNeedleMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    # Clear default nodes
    for node in nodes:
        nodes.remove(node)
    
    # Create Principled BSDF and Output nodes
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Brownish-tan color: desaturated brown/tan
    # RGB: (0.45, 0.35, 0.2)
    bsdf.inputs['Base Color'].default_value = (0.45, 0.35, 0.2, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.7
    
    # Link nodes
    links = mat.node_tree.links
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    return mat

def create_pine_needle():
    """Generates a thin, curved pine needle using a Bezier curve."""
    # Create curve data
    curve_data = bpy.data.curves.new('PineNeedleCurve', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    
    # Extremely thin radius for a hair-like filament (approx 0.5mm to 1mm)
    curve_data.bevel_depth = 0.001 
    curve_data.bevel_resolution = 3
    curve_data.resolution_u = 64 # High resolution for smooth arc
    
    # Create the spline
    spline = curve_data.splines.new('BEZIER')
    
    # We start with 1 point, add 1 more to get a total of 2 points.
    spline.bezier_points.add(1) 
    
    # Point 0: Start of the needle
    p0 = spline.bezier_points[0]
    p0.co = Vector((-1.2, 0.0, 0.0))
    p0.handle_left = Vector((-1.3, -0.05, 0.0))
    p0.handle_right = Vector((-0.6, 0.3, 0.0))
    
    # Point 1: End of the needle
    p1 = spline.bezier_points[1]
    p1.co = Vector((1.2, 0.0, 0.0))
    p1.handle_left = Vector((0.6, 0.3, 0.0))
    p1.handle_right = Vector((1.3, -0.05, 0.0))

    # Create object and link to scene
    needle_obj = bpy.data.objects.new('PineNeedle', curve_data)
    bpy.context.collection.objects.link(needle_obj)
    
    # Apply material
    mat = create_pine_needle_material()
    needle_obj.data.materials.append(mat)
    
    return needle_obj

def main():
    clear_scene()
    
    # Create the pine needle
    needle = create_pine_needle()
    
    # To match "rendered from above", we keep it primarily in XY plane 
    # but give it a very slight tilt and rotation for naturalism.
    needle.rotation_euler[0] = 0.05 # Small X tilt
    needle.rotation_euler[2] = 0.1  # Small Z rotation

if __name__ == "__main__":
    main()
