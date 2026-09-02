import bpy
import bmesh
import math
import random

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
    """Creates a material that blends beige/tan with green in the valleys."""
    mat = bpy.data.materials.new(name="BrainCoralMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for node in nodes:
        nodes.remove(node)

    # Nodes setup
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_mix = nodes.new(type='ShaderNodeMixRGB')
    node_noise = nodes.new(type='ShaderNodeTexNoise')
    node_color_ramp = nodes.new(type='ShaderNodeValToRGB')

    # Colors: Warm beige/tan and pale green
    color_ridge = (0.85, 0.72, 0.55, 1.0) # Beige-Tan
    color_valley = (0.4, 0.5, 0.3, 1.0)   # Pale Green

    node_mix.inputs[1].default_value = color_ridge
    node_mix.inputs[2].default_value = color_valley

    # Noise to create organic patches of green in the valleys/recesses
    node_noise.inputs['Scale'].default_value = 8.0
    node_noise.inputs['Detail'].default_value = 15.0
    
    # Color ramp to sharpen the transition between ridge and valley color
    node_color_ramp.color_ramp.elements[0].position = 0.35
    node_color_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    node_color_ramp.color_ramp.elements[1].position = 0.65
    node_color_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)

    links.new(node_noise.outputs['Fac'], node_color_ramp.inputs[0])
    links.new(node_color_ramp.outputs[0], node_mix.inputs[0])
    links.new(node_mix.outputs[0], node_bsdf.inputs['Base Color'])
    links.new(node_bsdf.outputs[0], node_output.inputs[0])

    node_bsdf.inputs['Roughness'].default_value = 0.9
    return mat

def create_brain_coral():
    """Generates a dome-shaped brain coral with strong labyrinthine geometry."""
    # 1. Base Sphere: High resolution to allow for visible displacement
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=128, ring_count=64)
    obj = bpy.context.active_object
    obj.name = "BrainCoral"

    # Flatten into a dome shape (oblate spheroid)
    obj.scale = (1.2, 1.2, 0.7)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # 2. Subdivide further to ensure the displacement is smooth and detailed
    subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 2

    # 3. Displacement Textures for Brain Patterns
    # Musgrave is the key to "labyrinthine" folds
    tex_folds = bpy.data.textures.new("CoralFolds", type='MUSGRAVE')
    tex_folds.noise_scale = 1.8
    tex_folds.lacunarity = 2.5
    
    # Clouds for general organic lumpiness
    tex_bulk = bpy.data.textures.new("CoralBulk", type='CLOUDS')
    tex_bulk.noise_scale = 3.0

    # Apply Labyrinth Folds first (Stronger)
    disp_folds = obj.modifiers.new(name="DispFolds", type='DISPLACE')
    disp_folds.texture = tex_folds
    disp_folds.strength = 0.25

    # Apply Bulk lumps second (Subtler)
    disp_bulk = obj.modifiers.new(name="DispBulk", type='DISPLACE')
    disp_bulk.texture = tex_bulk
    disp_bulk.strength = 0.1

    # Final smoothing pass
    subdiv_final = obj.modifiers.new(name="SmoothFinal", type='SUBSURF')
    subdiv_final.levels = 1

    # Apply all modifiers to freeze the high-detail geometry
    bpy.context.view_layer.objects.active = obj
    mods = [m.name for m in obj.modifiers]
    for mod_name in mods:
        bpy.ops.object.modifier_apply(modifier=mod_name)

    bpy.ops.object.shade_smooth()

    # Material Assignment
    mat = create_coral_material()
    obj.data.materials.append(mat)

def main():
    clear_scene()
    create_brain_coral()

if __name__ == "__main__":
    main()
