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
    """Creates a dark green marble material with distinct veining."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    for node in nodes:
        nodes.remove(node)
        
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    noise = nodes.new('ShaderNodeTexNoise')
    ramp = nodes.new('ShaderNodeValToRGB')
    coord = nodes.new('ShaderNodeTexCoord')

    # Scale and detail for marble veining
    noise.inputs['Scale'].default_value = 2.0
    noise.inputs['Detail'].default_value = 15.0
    noise.inputs['Roughness'].default_value = 0.7

    # ColorRamp: Deep dark green to a slightly lighter stone-green
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[0].color = (0.01, 0.03, 0.01, 1.0) # Very dark green
    ramp.color_ramp.elements[1].position = 0.6
    ramp.color_ramp.elements[1].color = (0.04, 0.12, 0.05, 1.0) # Vein color

    # High gloss for the "reflective glossy interior surface"
    bsdf.inputs['Roughness'].default_value = 0.08
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 1.0

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
    bsdf.inputs['Base Color'].default_value = (0.85, 0.85, 0.85, 1.0)
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.02
    return mat

def create_sink():
    """Creates a dark green stone sink with a deep bowl."""
    # Dimensions for a substantial countertop block
    width, depth, height = 0.6, 0.45, 0.25
    wall_thickness = 0.05
    bowl_radius = 0.04

    # Outer Block
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, height/2))
    sink_obj = bpy.context.active_object
    sink_obj.name = "Sink_Basin"
    sink_obj.scale = (width, depth, height)
    bpy.ops.object.transform_apply(scale=True)

    # Inner Cutout - positioned to leave a floor at the bottom
    bowl_depth = height - wall_thickness * 2
    cutout_z = height - (bowl_depth / 2) - (wall_thickness/2) # adjust for bowl depth
    
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, height - wall_thickness))
    cutout = bpy.context.active_object
    cutout.scale = (width - wall_thickness*2, depth - wall_thickness*2, height)
    # Move it up so it doesn't cut through the bottom completely
    cutout.location.z = height - (wall_thickness/2) 
    bpy.ops.object.transform_apply(scale=True)

    # Bevel for rounded bowl interior corners
    bev_mod = cutout.modifiers.new(name="Bevel", type='BEVEL')
    bev_mod.width = 0.05
    bev_mod.segments = 12
    bpy.ops.object.modifier_apply(modifier="Bevel")

    # Boolean subtraction to carve the deep bowl
    bool_mod = sink_obj.modifiers.new(name="BowlCut", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = cutout
    bpy.context.view_layer.objects.active = sink_obj
    bpy.ops.object.modifier_apply(modifier="BowlCut")

    # Clean up cutter
    bpy.data.objects.remove(cutout, do_unlink=True)

    # Bevel outer edges for a premium look
    bev_outer = sink_obj.modifiers.new(name="OuterBevel", type='BEVEL')
    bev_outer.width = 0.01
    bev_outer.segments = 4
    bpy.ops.object.modifier_apply(modifier="OuterBevel")
    
    marble_mat = create_marble_material("DarkGreenMarble")
    sink_obj.data.materials.append(marble_mat)
    return sink_obj

def create_faucet():
    """Creates the chrome gooseneck faucet with single handle, correctly attached."""
    chrome = create_chrome_material("Chrome")
    sink_top_z = 0.25
    # Back-left rim positioning
    base_x, base_y = -0.18, -0.12 

    # Faucet Base
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.05, location=(base_x, base_y, sink_top_z))
    base = bpy.context.active_object
    base.name = "Faucet_Base"
    base.data.materials.append(chrome)

    # Gooseneck using a curve converted to mesh
    curve_data = bpy.data.curves.new('GooseneckCurve', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 0.018
    curve_data.bevel_resolution = 8

    polyline = curve_data.splines.new('BEZIER')
    # Corrected coordinates to ensure connection and gooseneck shape
    coords = [
        (base_x, base_y, sink_top_z + 0.025), # Start exactly at top of base
        (base_x, base_y, 0.45),               # Rise up straight
        (0.0, base_y, 0.45),                  # Curve across the top
        (0.08, base_y, 0.32),                 # Descend to spout
    ]
    
    polyline.bezier_points.add(len(coords) - 1)
    for i, coord in enumerate(coords):
        p = polyline.bezier_points[i]
        p.co = coord
        p.handle_left = Vector((coord[0], coord[1], coord[2] - 0.05))
        p.handle_right = Vector((coord[0], coord[1], coord[2] + 0.05))

    faucet_curve_obj = bpy.data.objects.new('Faucet_Neck', curve_data)
    bpy.context.collection.objects.link(faucet_curve_obj)
    
    # Convert to mesh and apply material
    bpy.context.view_layer.objects.active = faucet_curve_obj
    bpy.ops.object.convert(target='MESH')
    faucet_neck = bpy.context.active_object
    faucet_neck.data.materials.append(chrome)

    # Single Handle - attached to the base assembly
    bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=0.08, location=(base_x - 0.06, base_y, sink_top_z + 0.04))
    handle = bpy.context.active_object
    handle.name = "Faucet_Handle"
    handle.rotation_euler[1] = math.radians(20) # Ergonomic tilt
    handle.data.materials.append(chrome)

    return [base, faucet_neck, handle]

def create_drain():
    """Creates the chrome drain at bottom of basin."""
    chrome = create_chrome_material("ChromeDrain")
    # Positioned near the floor of the bowl (approx z=0.05)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.03, location=(0, 0, 0.06))
    drain = bpy.context.active_object
    drain.name = "Sink_Drain"
    bev = drain.modifiers.new(name="DrainBev", type='BEVEL')
    bev.width = 0.005
    bev.segments = 4
    bpy.ops.object.modifier_apply(modifier="DrainBev")
    drain.data.materials.append(chrome)

def main():
    clear_scene()
    create_sink()
    create_faucet()
    create_drain()

if __name__ == "__main__":
    main()
