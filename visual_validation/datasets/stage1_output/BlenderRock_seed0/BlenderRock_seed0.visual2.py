import bpy
import bmesh
import math
import random
from mathutils import Vector, noise

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_rock():
    """Constructs a natural sedimentary rock with organic layers and rough textures."""
    # 1. Base Parameters
    SUBDIVISIONS = 5
    RADIUS = 1.2
    
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=SUBDIVISIONS, radius=RADIUS)
    rock_obj = bpy.context.active_object
    rock_obj.name = "NaturalRock"

    # Break the sphere symmetry immediately with random scaling
    rock_obj.scale = (random.uniform(0.7, 1.3), random.uniform(0.6, 1.2), random.uniform(0.5, 0.9))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bm = bmesh.new()
    bm.from_mesh(rock_obj.data)

    # 2. Geological Deformation
    for v in bm.verts:
        pos = v.co.copy()
        norm = pos.normalized()
        
        # A: Large scale organic distortion (low freq)
        bulk = noise.noise(pos * 0.4 + Vector((1.2, 3.4, 5.6))) * 0.5
        
        # B: Sedimentary layering (sinusoidal waves mixed with noise to create ridges)
        # We vary the frequency and phase slightly across XY to prevent perfect planes
        layer_freq = 4.0
        layer_phase = noise.noise(Vector((pos.x * 0.5, pos.y * 0.5, 0))) * 1.5
        layering = math.sin(pos.z * layer_freq + layer_phase) * 0.25
        
        # C: High frequency roughness/grit
        grit = noise.noise(pos * 3.0) * 0.15
        
        # D: Deep crevices (using a high-contrast noise approach)
        crevice_noise = noise.noise(pos * 2.0)
        crevices = (abs(crevice_noise) - 0.5) * 0.3 if abs(crevice_noise) < 0.5 else 0
        
        # Combine deformations along the normal
        total_disp = bulk + layering + grit + crevices
        v.co += norm * total_disp

    # 3. Create a Flat Base
    z_coords = [v.co.z for v in bm.verts]
    min_z = min(z_coords)
    max_z = max(z_coords)
    bottom_threshold = min_z + (max_z - min_z) * 0.1
    
    for v in bm.verts:
        if v.co.z < bottom_threshold:
            # Snap to a flat plane for the base
            v.co.z = min_z
            # Slightly jitter the edges of the base so it's not a perfect circle
            dist = Vector((v.co.x, v.co.y, 0)).length
            if dist > RADIUS * 0.5:
                v.co.x += random.uniform(-0.05, 0.05)
                v.co.y += random.uniform(-0.05, 0.05)

    bm.to_mesh(rock_obj.data)
    bm.free()

    # Avoid over-smoothing the ridges; use moderate subdivision
    subsurf = rock_obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    bpy.ops.object.shade_smooth()

    # 4. Material with Weathered Tonal Variation
    mat = bpy.data.materials.new(name="StoneMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes:
        nodes.remove(n)
        
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    noise_tex = nodes.new('ShaderNodeTexNoise')
    color_ramp = nodes.new('ShaderNodeValToRGB')
    
    # High contrast noise for "weathered" look
    noise_tex.inputs['Scale'].default_value = 8.0
    noise_tex.inputs['Detail'].default_value = 15.0
    noise_tex.inputs['Roughness'].default_value = 0.6
    
    # Color Ramp: Dark gray, Mid gray, Light highlight
    elements = color_ramp.color_ramp.elements
    elements[0].position = 0.3
    elements[0].color = (0.12, 0.13, 0.12, 1.0) # Dark crevices
    elements[1].position = 0.7
    elements[1].color = (0.45, 0.46, 0.44, 1.0) # Mid stone
    
    # Add a third stop for weathered highlights
    highlight = elements.new(0.9)
    highlight.color = (0.6, 0.62, 0.58, 1.0)

    bsdf.inputs['Roughness'].default_value = 0.9
    bsdf.inputs['Specular IOR Level'].default_value = 0.2
    
    links.new(noise_tex.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    rock_obj.data.materials.append(mat)

if __name__ == "__main__":
    clear_scene()
    create_rock()
