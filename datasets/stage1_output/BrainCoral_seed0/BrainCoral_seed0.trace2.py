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
    """Creates the organic coral material with ridge/valley coloring."""
    mat = bpy.data.materials.new(name="BrainCoralMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for node in nodes:
        nodes.remove(node)

    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_mix = nodes.new(type='ShaderNodeMixRGB')
    node_ao = nodes.new(type='ShaderNodeAmbientOcclusion')
    
    # Colors
    color_ridge = (0.85, 0.72, 0.55, 1.0) # Warm Beige/Tan
    color_valley = (0.45, 0.52, 0.35, 1.0) # Pale Green tints

    node_mix.inputs[1].default_value = color_ridge
    node_mix.inputs[2].default_value = color_valley

    # AO creates a mask: valleys are dark (0), ridges are bright (1)
    links.new(node_ao.outputs[0], node_mix.inputs[0])
    links.new(node_mix.outputs[0], node_bsdf.inputs['Base Color'])
    links.new(node_bsdf.outputs[0], node_output.inputs[0])

    node_bsdf.inputs['Roughness'].default_value = 0.8
    return mat

def create_brain_coral():
    """Generates the dome-shaped brain coral with labyrinthine geometry."""
    # 1. Create base sphere (the dome)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=64, ring_count=32, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "BrainCoral"

    # Flatten slightly to make it a dome (oblate spheroid)
    obj.scale = (1.2, 1.2, 0.75)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # 2. Subdivision for high vertex density needed for displacement
    subdiv_base = obj.modifiers.new(name="SubdivBase", type='SUBSURF')
    subdiv_base.levels = 3
    subdiv_base.render_levels = 3

    # 3. Displacement Textures
    # Large scale lumps (Clouds)
    tex_bulk = bpy.data.textures.new("CoralBulk", type='CLOUDS')
    tex_bulk.noise_scale = 1.5
    
    # Labyrinthine grooves (Musgrave - fixed properties for Blender 4/5 compatibility)
    tex_folds = bpy.data.textures.new("CoralFolds", type='MUSGRAVE')
    tex_folds.noise_scale = 3.0
    tex_folds.lacunarity = 2.0

    # Fine detail (Voronoi)
    tex_fine = bpy.data.textures.new("CoralFine", type='VORONOI')
    tex_fine.noise_scale = 8.0

    # 4. Apply Displacements
    disp_bulk = obj.modifiers.new(name="DispBulk", type='DISPLACE')
    disp_bulk.texture = tex_bulk
    disp_bulk.strength = 0.15

    disp_folds = obj.modifiers.new(name="DispFolds", type='DISPLACE')
    disp_folds.texture = tex_folds
    disp_folds.strength = 0.12

    disp_fine = obj.modifiers.new(name="DispFine", type='DISPLACE')
    disp_fine.texture = tex_fine
    disp_fine.strength = 0.04

    # Final smooth pass to soften edges
    subdiv_final = obj.modifiers.new(name="SmoothFinal", type='SUBSURF')
    subdiv_final.levels = 1

    # Apply all modifiers to freeze geometry
    bpy.context.view_layer.objects.active = obj
    for mod in obj.modifiers:
        bpy.ops.object.modifier_apply(modifier=mod.name)

    bpy.ops.object.shade_smooth()

    # 5. Material Assignment
    mat = create_coral_material()
    obj.data.materials.append(mat)

def main():
    clear_scene()
    create_brain_coral()

if __name__ == "__main__":
    main()
