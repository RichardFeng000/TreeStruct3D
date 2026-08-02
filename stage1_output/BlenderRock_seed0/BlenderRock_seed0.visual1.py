import bpy
import bmesh
import math
import random
from mathutils import Vector, noise

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    # Clear orphan data
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_rock():
    """Constructs a natural sedimentary rock with organic layers and tonal variation."""
    # 1. Base Parameters
    SUBDIVISIONS = 5 # IcoSphere detail
    RADIUS = 1.5
    
    # Create base geometry
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=SUBDIVISIONS, radius=RADIUS)
    rock_obj = bpy.context.active_object
    rock_obj.name = "NaturalRock"

    # Apply non-uniform scaling to break the sphere shape immediately
    rock_obj.scale = (random.uniform(0.8, 1.2), random.uniform(0.7, 1.1), random.uniform(0.6, 0.9))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bm = bmesh.new()
    bm.from_mesh(rock_obj.data)

    # 2. Organic Displacement
    for v in bm.verts:
        pos = v.co.copy()
        norm = pos.normalized()
        
        # General organic bulk (Low freq)
        bulk_noise = noise.noise(pos * 0.5) * 0.4
        
        # Sedimentary layering: Noise that varies primarily along Z, but shifts in XY
        # We use a stretched coordinate system to create "slabs"
        layer_coord = Vector((pos.x * 0.2, pos.y * 0.2, pos.z * 3.5))
        layering = noise.noise(layer_coord) * 0.3
        
        # Surface grit (High freq)
        grit = noise.noise(pos * 4.0) * 0.12
        
        v.co += norm * (bulk_noise + layering + grit)

    # 3. Flatten and Fix Base
    z_coords = [v.co.z for v in bm.verts]
    min_z = min(z_coords)
    max_z = max(z_coords)
    bottom_cutoff = min_z + (max_z - min_z) * 0.15

    for v in bm.verts:
        if v.co.z < bottom_cutoff:
            # Snap to base but add a tiny bit of random jitter to avoid vertical lines/combing
            v.co.z = min_z + random.uniform(-0.02, 0.02)
            
            # Pull the footprint inward slightly for a more grounded look
            dist_from_center = Vector((v.co.x, v.co.y, 0)).length
            if dist_from_center > RADIUS * 0.8:
                v.co.x *= 0.9
                v.co.y *= 0.9

    bm.to_mesh(rock_obj.data)
    bm.free()

    # Smoothing and refinement
    subsurf = rock_obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    bpy.ops.object.shade_smooth()

    # 4. Advanced Material with Tonal Variation
    mat = bpy.data.materials.new(name="StoneMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    for n in nodes:
        nodes.remove(n)
        
    # Node Setup
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    noise_tex = nodes.new('ShaderNodeTexNoise')
    color_ramp = nodes.new('ShaderNodeValToRGB')
    
    # Configure Noise Texture for tonal variation
    noise_tex.inputs['Scale'].default_value = 2.0
    noise_tex.inputs['Detail'].default_value = 5.0
    
    # Configure Color Ramp (Dark Gray to Light Gray)
    color_ramp.color_ramp.elements[0].color = (0.15, 0.16, 0.15, 1.0) # Dark stone
    color_ramp.color_ramp.elements[1].color = (0.4, 0.42, 0.38, 1.0)   # Light weathered stone
    
    # BSDF settings
    bsdf.inputs['Roughness'].default_value = 0.95
    bsdf.inputs['Specular IOR Level'].default_value = 0.1
    
    # Links: Noise -> Ramp -> Base Color
    links.new(noise_tex.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    rock_obj.data.materials.append(mat)

if __name__ == "__main__":
    clear_scene()
    create_rock()
