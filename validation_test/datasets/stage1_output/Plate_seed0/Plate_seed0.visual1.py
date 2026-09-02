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
    
    # Clear default nodes
    for node in nodes:
        nodes.remove(node)
        
    # Create Principled BSDF
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # Base Color - Dark Navy Blue
    navy_color = (0.01, 0.02, 0.08, 1.0)
    bsdf.inputs['Base Color'].default_value = navy_color
    bsdf.inputs['Roughness'].default_value = 0.15
    
    # Subtle surface variation using a Noise Texture
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 20.0
    noise.inputs['Detail'].default_value = 4.0
    
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.005, 0.015, 0.06, 1.0) # Slightly darker
    ramp.color_ramp.elements[1].color = (0.02, 0.03, 0.1, 1.0)   # Slightly lighter
    
    mix = nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MIX'
    mix.inputs[0].default_value = 0.15 # Subtle effect strength
    mix.inputs[1].default_value = navy_color
    
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], mix.inputs[2])
    links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
    
    return mat

def create_plate():
    """Constructs a high-quality dinner plate using a revolve profile."""
    # Dimensions (meters)
    plate_radius = 0.15
    rim_width = 0.025
    thickness = 0.008
    rim_height = 0.012
    foot_inner = 0.06
    foot_outer = 0.08
    foot_depth = 0.005

    # Define the profile points (r, z) for a revolution
    profile = [
        (0, thickness),                       # Center of well
        (plate_radius - rim_width, thickness), # Bottom of rim / start of well
        (plate_radius - rim_width, thickness + rim_height), # Top inner edge of rim
        (plate_radius, thickness + rim_height), # Top outer edge of rim
        (plate_radius, 0),                    # Bottom outer edge
        (foot_outer, 0),                      # Outer foot ring top
        (foot_outer, -foot_depth),            # Outer foot ring bottom
        (foot_inner, -foot_depth),            # Inner foot ring bottom
        (foot_inner, 0),                      # Inner foot ring top
        (0, 0)                                # Center bottom
    ]

    bm = bmesh.new()
    segments = 64

    # Create circular rings for each profile point
    rings = []
    for r, z in profile:
        ring_verts = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            ring_verts.append(bm.verts.new((x, y, z)))
        rings.append(ring_verts)

    # Bridge the rings into faces
    for i in range(len(rings) - 1):
        r1 = rings[i]
        r2 = rings[i+1]
        for j in range(segments):
            v1 = r1[j]
            v2 = r1[(j + 1) % segments]
            v3 = r2[(j + 1) % segments]
            v4 = r2[j]
            bm.faces.new((v1, v2, v3, v4))

    # Fill the top center (well) and bottom center (base)
    # Top face
    top_verts = rings[0]
    bm.faces.new(top_verts)
    # Bottom face
    bot_verts = rings[-1]
    bm.faces.new(reversed(bot_verts))

    # Ensure normals are correct and geometry is clean
    bm.normal_update()
    
    mesh = bpy.data.meshes.new("DinnerPlateMesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("DinnerPlate", mesh)
    bpy.context.collection.objects.link(obj)

    # Shading and polish
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    # Add Bevel for softer edges
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.001
    bevel.segments = 2
    
    return obj

def main():
    clear_scene()
    
    plate_obj = create_plate()
    material = create_navy_blue_material()
    plate_obj.data.materials.append(material)

if __name__ == "__main__":
    main()
