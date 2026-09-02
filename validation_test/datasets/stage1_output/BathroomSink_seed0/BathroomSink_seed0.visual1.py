import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_marble_material(name):
    """Creates a dark green marble material with procedural veining."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    for node in nodes:
        nodes.remove(node)
        
    # Nodes for marble effect
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    noise = nodes.new('ShaderNodeTexNoise')
    ramp = nodes.new('ShaderNodeValToRGB')
    coord = nodes.new('ShaderNodeTexCoord')

    # Configure Noise for veining
    noise.inputs['Scale'].default_value = 4.0
    noise.inputs['Detail'].default_value = 15.0
    noise.inputs['Roughness'].default_value = 0.6

    # ColorRamp for dark green marble colors
    ramp.color_ramp.elements[0].color = (0.01, 0.04, 0.02, 1.0) # Very dark green
    ramp.color_ramp.elements[1].color = (0.05, 0.15, 0.08, 1.0) # Lighter green vein

    # Surface properties
    bsdf.inputs['Roughness'].default_value = 0.1
    bsdf.inputs['Specular'].default_value = 0.6

    # Linking
    links.new(coord.outputs['Generated'], noise.inputs['Vector'])
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    return mat

def create_chrome_material(name):
    """Creates a highly reflective chrome material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.05
    return mat

def create_sink():
    """Creates the dark green stone sink with a deep bowl."""
    # Dimensions
    width, depth, height = 0.6, 0.45, 0.2
    wall_thickness = 0.04
    bowl_radius = 0.03

    # Outer block
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, height/2))
    sink_obj = bpy.context.active_object
    sink_obj.name = "Sink_Basin"
    sink_obj.scale = (width, depth, height)
    bpy.ops.object.transform_apply(scale=True)

    # Inner cutout for the bowl
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, height/2 + wall_thickness))
    cutout = bpy.context.active_object
    cutout.scale = (width - wall_thickness*2, depth - wall_thickness*2, height)
    bpy.ops.object.transform_apply(scale=True)

    # Bevel the cutout for rounded bowl interior
    bev_mod = cutout.modifiers.new(name="Bevel", type='BEVEL')
    bev_mod.width = bowl_radius * 1.5
    bev_mod.segments = 12
    bpy.ops.object.modifier_apply(modifier="Bevel")

    # Boolean subtraction to carve the bowl
    bool_mod = sink_obj.modifiers.new(name="BowlCut", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = cutout
    bpy.context.view_layer.objects.active = sink_obj
    bpy.ops.object.modifier_apply(modifier="BowlCut")

    # Clean up cutter
    bpy.data.objects.remove(cutout, do_unlink=True)

    # Subtle bevel for outer edges of the block
    bev_outer = sink_obj.modifiers.new(name="OuterBevel", type='BEVEL')
    bev_outer.width = 0.005
    bev_outer.segments = 3
    bpy.ops.object.modifier_apply(modifier="OuterBevel")
    
    # Apply marble material
    marble_mat = create_marble_material("DarkGreenMarble")
    sink_obj.data.materials.append(marble_mat)
    
    return sink_obj

def create_faucet():
    """Creates the chrome gooseneck faucet with single handle."""
    chrome = create_chrome_material("Chrome")
    
    # Faucet Base - positioned on back-left rim
    base_pos = (-0.2, -0.15, height_offset := 0.2)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=0.04, location=base_pos)
    base = bpy.context.active_object
    base.name = "Faucet_Base"
    base.data.materials.append(chrome)

    # Gooseneck tube using a curve converted to mesh
    curve_data = bpy.data.curves.new('GooseneckCurve', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 0.015
    curve_data.bevel_resolution = 8

    polyline = curve_data.splines.new('BEZIER')
    # Arc coordinates from base to spout
    coords = [
        (-0.2, -0.15, 0.22), # Start at base
        (-0.2, -0.15, 0.45), # Rise up
        (0.0, -0.15, 0.45),  # Top of arc
        (0.05, -0.15, 0.3),  # Descend to spout
    ]
    
    polyline.bezier_points.add(len(coords) - 1)
    for i, coord in enumerate(coords):
        p = polyline.bezier_points[i]
        p.co = coord
        p.handle_left = Vector((coord[0], coord[1], coord[2] - 0.1))
        p.handle_right = Vector((coord[0], coord[1], coord[2] + 0.1))

    faucet_curve_obj = bpy.data.objects.new('Faucet_Neck', curve_data)
    bpy.context.collection.objects.link(faucet_curve_obj)
    
    # Convert to mesh
    bpy.context.view_layer.objects.active = faucet_curve_obj
    bpy.ops.object.convert(target='MESH')
    faucet_neck = bpy.context.active_object
    faucet_neck.data.materials.append(chrome)

    # Single Handle - offset from base
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.07, location=(-0.25, -0.15, 0.24))
    handle = bpy.context.active_object
    handle.name = "Faucet_Handle"
    handle.rotation_euler[1] = math.radians(30) # Slight tilt
    handle.data.materials.append(chrome)

    return [base, faucet_neck, handle]

def create_drain():
    """Creates the chrome drain at the bottom of the basin."""
    chrome = create_chrome_material("ChromeDrain")
    # Positioned at the center floor of the bowl
    bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.02, location=(0, 0, 0.06))
    drain = bpy.context.active_object
    drain.name = "Sink_Drain"
    
    # Simple bevel for the drain lip
    bev = drain.modifiers.new(name="DrainBev", type='BEVEL')
    bev.width = 0.005
    bev.segments = 4
    bpy.ops.object.modifier_apply(modifier="DrainBev")
    
    drain.data.materials.append(chrome)

def main():
    clear_scene()
    
    # Build components
    create_sink()
    create_faucet()
    create_drain()

if __name__ == "__main__":
    main()
