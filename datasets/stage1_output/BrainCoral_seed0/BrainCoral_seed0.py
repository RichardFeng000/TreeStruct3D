import bpy
import bmesh
import math

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.textures:
        if block.users == 0:
            bpy.data.textures.remove(block)

def create_coral_material():
    """Creates a material blending warm beige/tan with pale green in valleys."""
    mat = bpy.data.materials.new(name="BrainCoralMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for node in nodes:
        nodes.remove(node)

    # Node setup
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_mix = nodes.new(type='ShaderNodeMixRGB')
    node_noise = nodes.new(type='ShaderNodeTexNoise')
    node_ramp = nodes.new(type='ShaderNodeValToRGB')

    # Colors: Warm beige-tan and a more distinct pale green
    color_ridge = (0.8, 0.6, 0.4, 1.0)  # Tan/Beige
    color_valley = (0.3, 0.45, 0.2, 1.0) # Pale Green

    node_mix.inputs[1].default_value = color_ridge
    node_mix.inputs[2].default_value = color_valley

    # Noise to define where green settles (valleys)
    node_noise.inputs['Scale'].default_value = 5.0
    node_noise.inputs['Detail'].default_value = 12.0
    
    # Sharper ramp for better contrast between colors
    node_ramp.color_ramp.elements[0].position = 0.4
    node_ramp.color_ramp.elements[1].position = 0.6

    links.new(node_noise.outputs['Fac'], node_ramp.inputs[0])
    links.new(node_ramp.outputs[0], node_mix.inputs[0])
    links.new(node_mix.outputs[0], node_bsdf.inputs['Base Color'])
    links.new(node_bsdf.outputs[0], node_output.inputs[0])

    node_bsdf.inputs['Roughness'].default_value = 0.85
    return mat

def create_brain_coral():
    """Generates a dome-shaped brain coral with deep, winding labyrinthine folds."""
    # Start with high resolution UV sphere for displacement detail
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=128, ring_count=64)
    obj = bpy.context.active_object
    obj.name = "BrainCoral"

    # Shape into a dome (flattened sphere)
    obj.scale = (1.3, 1.3, 0.75)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Add significant resolution via subdivision for the displacement to actually show
    subdiv = obj.modifiers.new(name="Subdivide", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 3

    # Labyrinthine Folds: Using Musgrave with a small scale and high strength
    # We use multiple displacement layers to create the 'brain' complexity
    tex_folds = bpy.data.textures.new("LabyrinthTex", type='MUSGRAVE')
    tex_folds.noise_scale = 0.8 # Lower scale = more frequent ridges
    tex_folds.lacunarity = 2.0
    
    disp_folds = obj.modifiers.new(name="BrainFolds", type='DISPLACE')
    disp_folds.texture = tex_folds
    disp_folds.strength = 0.18

    # Second layer for organic variation and "blobs"
    tex_organic = bpy.data.textures.new("OrganicTex", type='CLOUDS')
    tex_organic.noise_scale = 2.5
    
    disp_organic = obj.modifiers.new(name="OrganicBulk", type='DISPLACE')
    disp_organic.texture = tex_organic
    disp_organic.strength = 0.08

    # Final smooth pass to remove jaggy edges while keeping the folds
    subdiv_final = obj.modifiers.new(name="SmoothFinal", type='SUBSURF')
    subdiv_final.levels = 1

    # Apply all modifiers to bake geometry
    bpy.context.view_layer.objects.active = obj
    mods = [m.name for m in obj.modifiers]
    for mod_name in mods:
        bpy.ops.object.modifier_apply(modifier=mod_name)

    bpy.ops.object.shade_smooth()

    # Assign material
    mat = create_coral_material()
    obj.data.materials.append(mat)

def main():
    clear_scene()
    create_brain_coral()

if __name__ == "__main__":
    main()
