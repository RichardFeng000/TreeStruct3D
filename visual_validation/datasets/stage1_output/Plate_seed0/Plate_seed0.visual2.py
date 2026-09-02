import bpy
import bmesh
import math

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_navy_blue_material():
    """Creates a dark navy blue material with ceramic glaze and subtle variation."""
    mat = bpy.data.materials.new(name="NavyBluePlate")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    for node in nodes:
        nodes.remove(node)
        
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # Dark Navy Blue: Deep, saturated blue
    navy_color = (0.01, 0.03, 0.12, 1.0)
    bsdf.inputs['Base Color'].default_value = navy_color
    bsdf.inputs['Roughness'].default_value = 0.1
    bsdf.inputs['Specular IOR Level'].default_value = 0.5 # Ceramic-like reflectiveness
    
    # Subtle surface variation using a Noise Texture and ColorRamp
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 15.0
    noise.inputs['Detail'].default_value = 8.0
    
    ramp = nodes.new('ShaderNodeValToRGB')
    # Slight variation between two deep navy shades
    ramp.color_ramp.elements[0].color = (0.005, 0.02, 0.08, 1.0)
    ramp.color_ramp.elements[1].color = (0.02, 0.04, 0.15, 1.0)
    
    # Mix node for Blender 4.0+ API compatibility
    mix = nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MIX'
    mix.inputs[0].default_value = 0.2  # Influence of the variation
    mix.inputs[6].default_value = navy_color # Color1 (Base)
    
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], mix.inputs[7]) # Color2 (Variation)
    links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    
    return mat

def create_plate():
    """Constructs a high-quality dinner plate with a realistic profile."""
    # Dimensions in meters
    radius = 0.15
    rim_width = 0.025
    well_depth = 0.01
    total_height = 0.02
    foot_outer = 0.07
    foot_inner = 0.06
    foot_bottom = -0.004

    # Profile points (r, z) for revolution to create a more organic shape
    # We define the outer silhouette of the plate cross-section
    profile = [
        (0, well_depth),                      # Center inside well
        (radius - rim_width * 1.5, well_depth), # Bottom of shallow well
        (radius - rim_width, total_height),   # Transition to raised rim (curved)
        (radius, total_height),               # Top outer edge of rim
        (radius, 0),                          # Bottom outer edge
        (foot_outer, 0),                      # Start of foot ring
        (foot_outer, foot_bottom),            # Foot bottom outer
        (foot_inner, foot_bottom),            # Foot bottom inner
        (foot_inner, 0),                      # Foot top inner
        (0, 0)                                # Center underside
    ]

    bm = bmesh.new()
    segments = 64

    # Create vertices for each ring in the profile
    rings = []
    for r, z in profile:
        ring_verts = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            ring_verts.append(bm.verts.new((x, y, z)))
        rings.append(ring_verts)

    # Bridge the rings into faces (forming the walls)
    for i in range(len(rings) - 1):
        r1 = rings[i]
        r2 = rings[i+1]
        for j in range(segments):
            v1 = r1[j]
            v2 = r1[(j + 1) % segments]
            v3 = r2[(j + 1) % segments]
            v4 = r2[j]
            bm.faces.new((v1, v2, v3, v4))

    # Fill the top face (the well interior)
    bm.faces.new(rings[0])
    # Fill the bottom face (the base center)
    bm.faces.new(reversed(rings[-1]))

    bm.normal_update()
    
    mesh = bpy.data.meshes.new("DinnerPlateMesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("DinnerPlate", mesh)
    bpy.context.collection.objects.link(obj)

    # Visual polish
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    # Add Bevel to break sharp edges of the rim and foot
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.0015
    bevel.segments = 3
    
    return obj

def main():
    clear_scene()
    
    plate_obj = create_plate()
    material = create_navy_blue_material()
    plate_obj.data.materials.append(material)

if __name__ == "__main__":
    main()
