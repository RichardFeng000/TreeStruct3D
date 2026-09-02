import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    if bpy.context.active_object and bpy.context.active_object.mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.5, metallic=0.0):
    """Creates a Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        rgba = (*color, 1.0) if len(color) == 3 else color
        bsdf.inputs['Base Color'].default_value = rgba
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['Metallic'].default_value = metallic
    return mat

def create_apple_material():
    """Creates a material simulating a peachy pink apple with vertical cream streaks."""
    mat = bpy.data.materials.new(name="AppleMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    for node in nodes:
        nodes.remove(node)
        
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    
    # Colors: Warmer Peachy Pink and subtle Creamy White
    base_color = (1.0, 0.55, 0.45, 1.0) # Richer Warm Peachy Pink
    streak_color = (1.0, 0.95, 0.85, 1.0) # Subtle Creamy White
    
    # Setup procedural texture for vertical streaks
    tex_coord = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeMapping')
    noise = nodes.new('ShaderNodeTexNoise')
    color_ramp = nodes.new('ShaderNodeValToRGB')
    
    # Stretch noise to create vertical streaks (high scale X/Y, low Z)
    # Scale in mapping: High values mean more repetitions of the noise pattern
    mapping.inputs['Scale'].default_value = (15.0, 15.0, 1.0)
    noise.inputs['Scale'].default_value = 2.0
    noise.inputs['Detail'].default_value = 15.0
    
    # Color Ramp: Blend between Peachy Pink and Cream
    color_ramp.color_ramp.elements[0].position = 0.4
    color_ramp.color_ramp.elements[0].color = base_color
    color_ramp.color_ramp.elements[1].position = 0.7
    color_ramp.color_ramp.elements[1].color = streak_color
    
    # Glossy finish as requested
    bsdf.inputs['Roughness'].default_value = 0.2
    
    links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
    links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    return mat

def create_apple():
    """Creates the main body of the apple."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0)
    apple = bpy.context.active_object
    apple.name = "AppleBody"

    # Classic slightly flattened spherical shape
    apple.scale = (1.1, 1.1, 0.9)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bm = bmesh.new()
    bm.from_mesh(apple.data)
    
    for v in bm.verts:
        x, y, z = v.co
        # Top Crown Dimple (Indented crown)
        if z > 0.5:
            dist_sq = x**2 + y**2
            if dist_sq < 0.6:
                dip = 0.3 * (1.0 - (dist_sq / 0.6))
                v.co.z -= dip
        
        # Bottom Flattening for natural look
        if z < -0.8:
            v.co.z += (-z - 0.8) * 0.4

    bm.to_mesh(apple.data)
    bm.free()

    bpy.ops.object.shade_smooth()
    subsurf = apple.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    
    apple_mat = create_apple_material()
    apple.data.materials.append(apple_mat)

    return apple

def create_stem():
    """Creates the short, straight brown stem."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.035, depth=0.4)
    stem = bpy.context.active_object
    stem.name = "AppleStem"
    
    # Position at top center within the dimple
    stem.location = (0, 0, 0.8)
    
    bm = bmesh.new()
    bm.from_mesh(stem.data)
    for v in bm.verts:
        if v.co.z > 0:
            # Subtle taper and slight curve for realism
            scale_factor = 1.0 - (v.co.z * 0.4)
            v.co.x *= scale_factor
            v.co.y *= scale_factor
    bm.to_mesh(stem.data)
    bm.free()

    bpy.ops.object.shade_smooth()
    stem_mat = create_material("StemMat", (0.15, 0.08, 0.04), roughness=0.7)
    stem.data.materials.append(stem_mat)

def create_base():
    """Creates the small black circular base disc."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.45, depth=0.02)
    base = bpy.context.active_object
    base.name = "BaseDisc"
    # Place exactly at the bottom of the apple geometry (z ~ -1)
    base.location = (0, 0, -1.0)
    
    bpy.ops.object.shade_smooth()
    base_mat = create_material("BaseMat", (0.02, 0.02, 0.02), roughness=0.6)
    base.data.materials.append(base_mat)

def main():
    clear_scene()
    create_apple()
    create_stem()
    create_base()

if __name__ == "__main__":
    main()
