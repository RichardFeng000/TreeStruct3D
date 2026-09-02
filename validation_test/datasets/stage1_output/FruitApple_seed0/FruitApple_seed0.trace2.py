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
    """Creates a Principled BSDF material with RGBA support."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Ensure color is RGBA (4 items)
        if len(color) == 3:
            rgba = (*color, 1.0)
        else:
            rgba = color
        bsdf.inputs['Base Color'].default_value = rgba
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['Metallic'].default_value = metallic
    return mat

def create_apple_material():
    """Creates a more complex material for the apple to simulate blush and streaks."""
    mat = bpy.data.materials.new(name="AppleMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    for node in nodes:
        nodes.remove(node)
        
    # Create Nodes
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    
    # Base peachy pink
    base_color = (1.0, 0.75, 0.6, 1.0) # Warm Peachy Pink
    streak_color = (1.0, 0.95, 0.8, 1.0) # Creamy White
    
    # Procedural streaks using noise and coordinate mapping
    tex_coord = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeMapping')
    noise = nodes.new('ShaderNodeTexNoise')
    color_ramp = nodes.new('ShaderNodeValToRGB')
    mix = nodes.new('ShaderNodeMixRGB')
    
    # Noise settings for vertical streaks
    noise.inputs['Scale'].default_value = 2.0
    noise.inputs['Detail'].default_value = 15.0
    
    # Stretch the mapping to make it look like vertical streaks
    mapping.inputs['Scale'].default_value = (0.2, 0.2, 1.0)
    
    # Color Ramp for high contrast streaks
    color_ramp.color_ramp.elements[0].position = 0.4
    color_ramp.color_ramp.elements[0].color = base_color
    color_ramp.color_ramp.elements[1].position = 0.6
    color_ramp.color_ramp.elements[1].color = streak_color
    
    # BSDF settings
    bsdf.inputs['Roughness'].default_value = 0.3
    
    # Links
    links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
    links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    return mat

def create_apple():
    """Creates the main body of the apple."""
    # Create a sphere as the base
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0)
    apple = bpy.context.active_object
    apple.name = "AppleBody"

    # Slightly flatten and widen to get that apple silhouette
    apple.scale = (1.1, 1.1, 0.9)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Use BMesh to sculpt the top dimple and bottom flatten
    bm = bmesh.new()
    bm.from_mesh(apple.data)
    
    for v in bm.verts:
        x, y, z = v.co
        # Top Crown Dimple: Push vertices down near the top center
        if z > 0.6:
            dist_sq = x**2 + y**2
            # Create a parabolic dip at the top
            if dist_sq < 0.5:
                dip = 0.2 * (1.0 - (dist_sq / 0.5))
                v.co.z -= dip
        
        # Bottom Flattening: Squash the very bottom slightly
        if z < -0.8:
            v.co.z += (-z - 0.8) * 0.4

    bm.to_mesh(apple.data)
    bm.free()

    # Smooth shading
    bpy.ops.object.shade_smooth()
    
    # High fidelity surface
    subsurf = apple.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2

    # Material: Procedural Blush Apple
    apple_mat = create_apple_material()
    apple.data.materials.append(apple_mat)

    return apple

def create_stem():
    """Creates the stem of the apple."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.035, depth=0.4)
    stem = bpy.context.active_object
    stem.name = "AppleStem"
    
    # Position it at the top crown center (approx z=0.8 because of dimple)
    stem.location = (0, 0, 0.85)
    
    # Slight taper and a very subtle lean for natural look
    bm = bmesh.new()
    bm.from_mesh(stem.data)
    for v in bm.verts:
        if v.co.z > 0: # Upper part of stem
            v.co.x += 0.05 * (v.co.z / 0.2)
            v.co.y += 0.03 * (v.co.z / 0.2)
            # Taper the tip
            scale_factor = 1.0 - (v.co.z * 0.5)
            v.co.x *= scale_factor
            v.co.y *= scale_factor
    bm.to_mesh(stem.data)
    bm.free()

    bpy.ops.object.shade_smooth()
    
    # Material: Brown (RGBA)
    stem_mat = create_material("StemMat", (0.2, 0.1, 0.05), roughness=0.8)
    stem.data.materials.append(stem_mat)

def create_base():
    """Creates the small black circular base disc."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.45, depth=0.015)
    base = bpy.context.active_object
    base.name = "BaseDisc"
    
    # Place it at the bottom of the apple body
    base.location = (0, 0, -0.92)
    
    bpy.ops.object.shade_smooth()
    
    # Material: Black (RGBA)
    base_mat = create_material("BaseMat", (0.01, 0.01, 0.01), roughness=0.6)
    base.data.materials.append(base_mat)

def main():
    clear_scene()
    create_apple()
    create_stem()
    create_base()

if __name__ == "__main__":
    main()
