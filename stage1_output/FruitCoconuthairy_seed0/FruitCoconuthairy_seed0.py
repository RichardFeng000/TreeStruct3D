import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clear all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_gradient_material():
    """Create a material with a Z-axis gradient for coconut hair colors."""
    mat = bpy.data.materials.new(name="CoconutHairMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    # Texture Coordinate -> Separate XYZ (Z) -> ColorRamp -> Principled BSDF
    tex_coord = nodes.new(type='ShaderNodeTexCoord')
    sep_xyz = nodes.new(type='ShaderNodeSeparateXYZ')
    color_ramp = nodes.new(type='ShaderNodeValToRGB')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Configure Color Ramp for the specific coconut hues
    # 0.0: Cream Yellow, 0.5: Golden Tan, 1.0: Reddish Orange
    elements = color_ramp.color_ramp.elements
    elements[0].position = 0.0
    elements[0].color = (0.9, 0.82, 0.6, 1.0) # Cream Yellow
    
    mid = elements.new(0.5)
    mid.color = (0.6, 0.35, 0.15, 1.0)        # Golden Tan
    
    elements[2].position = 1.0
    elements[2].color = (0.7, 0.2, 0.05, 1.0) # Reddish Orange
    
    bsdf.inputs['Roughness'].default_value = 0.9
    
    links.new(tex_coord.outputs['Generated'], sep_xyz.inputs['Vector'])
    links.new(sep_xyz.outputs['Z'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    return mat

def create_coconut():
    # Constants for density and appearance
    RADIUS = 1.0
    NUM_HAIRS = 25000 # Increased significantly to hide core
    FIBER_MIN_LEN = 0.2
    FIBER_MAX_LEN = 0.4
    BEVEL_DEPTH = 0.003 
    
    # Material with gradient mapping (Z-axis)
    hair_mat = create_gradient_material()

    # Create the core sphere - slightly smaller to ensure it's buried
    bpy.ops.mesh.primitive_uv_sphere_add(radius=RADIUS * 0.95, segments=32, ring_count=16)
    core = bpy.context.active_object
    core.name = "CoconutCore"
    # Hide core from render/view if needed, but density should cover it
    
    # Create a single curve object for all fibers to use the gradient material
    curve_data = bpy.data.curves.new('Hairs', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = BEVEL_DEPTH
    curve_data.bevel_resolution = 2
    curve_obj = bpy.data.objects.new('CoconutHairs', curve_data)
    bpy.context.collection.objects.link(curve_obj)
    curve_obj.active_material = hair_mat

    # Fibonacci Spiral distribution for roots
    golden_ratio = (1 + 5**0.5) / 2
    
    for i in range(NUM_HAIRS):
        z = 1 - (2 * i / float(NUM_HAIRS - 1))
        radius_at_z = math.sqrt(max(0, 1 - z*z))
        theta = 2 * math.pi * i / golden_ratio
        
        # Root position on the sphere surface
        root_pos = Vector((
            RADIUS * radius_at_z * math.cos(theta),
            RADIUS * radius_at_z * math.sin(theta),
            RADIUS * z
        ))
        
        length = random.uniform(FIBER_MIN_LEN, FIBER_MAX_LEN)
        normal = root_pos.normalized()
        
        # Create 5 points per fiber to ensure an organic "curved" and "tangled" look
        # instead of straight sticks.
        spline = curve_data.splines.new('POLY')
        spline.points.add(4) # Default is 1, add 4 more for total 5 points
        
        prev_p = root_pos
        for j in range(5):
            if j == 0:
                p = root_pos
            elif j == 4:
                # Final tip point with significant random offset for "messy" look
                tip_dir = (normal + Vector((random.uniform(-0.3, 0.3), 
                                            random.uniform(-0.3, 0.3), 
                                            random.uniform(-0.3, 0.3)))).normalized()
                p = root_pos + tip_dir * length
            else:
                # Intermediate points for curvature and tangling
                progress = j / 4.0
                jitter = Vector((random.uniform(-0.12, 0.12), 
                                random.uniform(-0.12, 0.12), 
                                random.uniform(-0.12, 0.12)))
                p = root_pos + (normal * length * progress) + jitter
            
            spline.points[j].co = (p.x, p.y, p.z, 1.0)

if __name__ == "__main__":
    clear_scene()
    create_coconut()
