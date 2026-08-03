import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clear the default scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_patterned_material(name, color1, color2):
    """Create a procedural striped material to simulate growth rings."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    # Output and BSDF
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_principled.inputs['Roughness'].default_value = 0.7
    links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    
    # Coordinates and Pattern
    node_tex_coord = nodes.new(type='ShaderNodeTexCoord')
    node_separate = nodes.new(type='ShaderNodeSeparateXYZ')
    links.new(node_tex_coord.outputs['Generated'], node_separate.inputs['Vector'])
    
    # Sine wave for stripes along Z axis (the length of the shell)
    node_math_mul = nodes.new(type='ShaderNodeMath')
    node_math_mul.operation = 'MULTIPLY'
    node_math_mul.inputs[1].default_value = 12.0 # Frequency of rings
    links.new(node_separate.outputs['Z'], node_math_mul.inputs[0])
    
    node_math_sin = nodes.new(type='ShaderNodeMath')
    node_math_sin.operation = 'SINE'
    links.new(node_math_mul.outputs[0], node_math_sin.inputs[0])
    
    # Map -1..1 to 0..1
    node_map = nodes.new(type='ShaderNodeMapRange')
    node_map.inputs['From Min'].default_value = -1.0
    node_map.inputs['From Max'].default_value = 1.0
    node_map.inputs['To Min'].default_value = 0.0
    node_map.inputs['To Max'].default_value = 1.0
    links.new(node_math_sin.outputs[0], node_map.inputs[0])
    
    # Mix colors based on the pattern
    node_mix = nodes.new(type='ShaderNodeMixRGB')
    node_mix.inputs['Fac'].default_value = 0.5 # Not used, driven by map
    node_mix.inputs[1].default_value = color1
    node_mix.inputs[2].default_value = color2
    links.new(node_map.outputs[0], node_mix.inputs['Fac'])
    
    links.new(node_mix.outputs[0], node_principled.inputs['Base Color'])
    return mat

def create_simple_material(name, color, roughness=0.4):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Roughness'].default_value = roughness
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_mussel_valve(name):
    bm = bmesh.new()
    res_long = 64
    res_arc = 32
    length = 5.0
    width_max = 2.2
    height_max = 1.8
    thickness = 0.15

    # Create the outer shell geometry
    outer_verts = []
    for i in range(res_long + 1):
        u = i / res_long
        # Teardrop shape: starts sharp, bulges slightly then narrows/rounds at end
        swell = (u ** 0.6) * (1.0 - 0.2 * u**2) 
        if u == 0: swell = 0.01
        
        w = width_max * swell
        h = height_max * swell
        # Add a slight organic curve to the spine
        z = u * length
        y_offset = 0.2 * math.sin(u * math.pi)
        
        row = []
        for j in range(res_arc + 1):
            theta = (j / res_arc) * math.pi
            x = w * math.cos(theta)
            y = h * math.sin(theta) + y_offset
            row.append(bm.verts.new(Vector((x, y, z))))
        outer_verts.append(row)

    for i in range(res_long):
        for j in range(res_arc):
            bm.faces.new((outer_verts[i][j], outer_verts[i+1][j], 
                          outer_verts[i+1][j+1], outer_verts[i][j+1]))

    # Create the inner shell geometry (hollowed)
    inner_verts = []
    for i in range(res_long + 1):
        u = i / res_long
        swell = (u ** 0.6) * (1.0 - 0.2 * u**2)
        if u == 0: swell = 0.01
        w_inner = width_max * swell * 0.92
        h_inner = height_max * swell * 0.92
        z = u * length
        y_offset = 0.2 * math.sin(u * math.pi)
        
        row = []
        for j in range(res_arc + 1):
            theta = (j / res_arc) * math.pi
            x = w_inner * math.cos(theta)
            y = h_inner * math.sin(theta) + y_offset - thickness
            row.append(bm.verts.new(Vector((x, y, z))))
        inner_verts.append(row)

    for i in range(res_long):
        for j in range(res_arc):
            bm.faces.new((inner_verts[i][j+1], inner_verts[i+1][j+1], 
                          inner_verts[i+1][j], inner_verts[i][j]))

    # Bridging the lips and hinge
    for j in range(res_arc):
        bm.faces.new((outer_verts[0][j], outer_verts[0][j+1], inner_verts[0][j+1], inner_verts[0][j]))
    for j in range(res_arc):
        bm.faces.new((outer_verts[res_long][j], inner_verts[res_long][j], 
                      inner_verts[res_long][j+1], outer_verts[res_long][j+1]))
    for i in range(res_long):
        bm.faces.new((outer_verts[i][0], outer_verts[i+1][0], inner_verts[i+1][0], inner_verts[i][0]))
        bm.faces.new((outer_verts[i][res_arc], inner_verts[i][res_arc], 
                      inner_verts[i+1][res_arc], outer_verts[i+1][res_arc]))

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def main():
    clear_scene()
    
    # Colors: Cream and Brown for exterior, Dark Purple/Black for interior
    color_cream = (0.9, 0.85, 0.7, 1.0)
    color_brown = (0.4, 0.3, 0.2, 1.0)
    color_dark = (0.02, 0.01, 0.03, 1.0)

    mat_outer = create_patterned_material("MusselOuter", color_cream, color_brown)
    mat_inner = create_simple_material("MusselInner", color_dark, roughness=0.2)

    v_top = create_mussel_valve("ValveTop")
    v_bot = create_mussel_valve("ValveBottom")
    
    # Flip bottom valve
    v_bot.scale = (1, -1, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    for v in [v_top, v_bot]:
        v.data.materials.append(mat_outer)
        v.data.materials.append(mat_inner)
        for poly in v.data.polygons:
            # Simple heuristic: faces pointing generally 'outward' get the pattern
            if (v == v_top and poly.normal.y > 0) or (v == v_bot and poly.normal.y < 0):
                poly.material_index = 0
            else:
                poly.material_index = 1

    # Hinge at origin, partially open
    v_top.rotation_euler = (0, math.radians(-20), 0)
    v_bot.rotation_euler = (0, math.radians(20), 0)
    
    for v in [v_top, v_bot]:
        v.data.polygons.foreach_set("use_smooth", [True] * len(v.data.polygons))
        subdiv = v.modifiers.new(name="Subdiv", type='SUBSURF')
        subdiv.levels = 2

    container = bpy.data.objects.new("MusselContainer", None)
    bpy.context.collection.objects.link(container)
    v_top.parent = container
    v_bot.parent = container
    container.rotation_euler = (math.radians(-70), 0, math.radians(45))

if __name__ == "__main__":
    main()
