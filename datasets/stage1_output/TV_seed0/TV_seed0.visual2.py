import bpy
import bmesh
import math

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Creates a basic Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_artwork_material():
    """Creates a procedural abstract artwork material for the screen."""
    mat = bpy.data.materials.new(name="TV_Artwork")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    for n in nodes:
        nodes.remove(n)
        
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    
    # Abstract artwork using Noise and high contrast ColorRamp
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 3.0
    noise.inputs['Detail'].default_value = 16.0
    noise.inputs['Distortion'].default_value = 2.0
    
    ramp = nodes.new('ShaderNodeValToRGB')
    elements = ramp.color_ramp.elements
    # Palette: Deep Mauve, Vibrant Pink, Soft Rose
    elements[0].position = 0.3
    elements[0].color = (0.1, 0.02, 0.1, 1.0) # Deep Mauve
    elements[1].position = 0.7
    elements[1].color = (0.95, 0.8, 0.9, 1.0)   # Soft Rose/White
    
    mid_elem = elements.new(0.5)
    mid_elem.color = (0.8, 0.1, 0.5, 1.0)     # Vibrant Pink
    
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    
    # Emission to make the screen look like it's on
    if 'Emission Color' in bsdf.inputs:
        bsdf.inputs['Emission Color'].default_value = (0.5, 0.2, 0.4, 1.0)
        bsdf.inputs['Emission Strength'].default_value = 1.2
    elif 'Emission' in bsdf.inputs:
        bsdf.inputs['Emission'].default_value = (0.5, 0.2, 0.4, 1.0)
        bsdf.inputs['Emission Strength'].default_value = 1.2
        
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def create_tv():
    # Dimensions (m)
    width = 1.6
    height = 0.9
    depth = 0.03  # Thin profile
    bezel_thickness = 0.025 # Increased thickness for better visibility
    bottom_strip_h = 0.08
    
    # More saturated Gold
    mat_gold = create_material("GoldBezel", (1.0, 0.7, 0.1, 1.0), metallic=1.0, roughness=0.2)
    mat_dark = create_material("DarkMetal", (0.03, 0.03, 0.04, 1.0), metallic=1.0, roughness=0.3)
    mat_art = create_artwork_material()

    # --- Main Body (Chassis) ---
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    body = bpy.context.active_object
    body.name = "TV_Chassis"
    body.scale = (width, depth, height)
    bpy.ops.object.transform_apply(scale=True)
    body.data.materials.append(mat_dark)

    # --- Gold Bezel Frame ---
    # Creating a frame rather than just a slab to ensure it wraps the screen correctly
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    bezel = bpy.context.active_object
    bezel.name = "GoldBezel"
    bezel.scale = (width, 0.008, height)
    bezel.location.y = depth / 2 + 0.004
    bpy.ops.object.transform_apply(scale=True, location=True)
    bezel.data.materials.append(mat_gold)

    # --- The Display Screen (Artwork) ---
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    screen = bpy.context.active_object
    screen.name = "TV_Display"
    # Subtract bezel from both sides
    screen_w = width - (bezel_thickness * 2)
    screen_h = height - (bezel_thickness * 2)
    screen.scale = (screen_w, 0.006, screen_h)
    # Offset slightly in front of bezel to prevent z-fighting
    screen.location.y = depth / 2 + 0.007
    bpy.ops.object.transform_apply(scale=True, location=True)
    screen.data.materials.append(mat_art)

    # --- Bottom Strip (Dark Metallic) ---
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    strip = bpy.context.active_object
    strip.name = "BottomStrip"
    strip.scale = (width, depth + 0.005, bottom_strip_h)
    strip.location.z = -height/2 + (bottom_strip_h / 2)
    strip.location.y = 0
    bpy.ops.object.transform_apply(scale=True, location=True)
    strip.data.materials.append(mat_dark)

    # --- T-Shaped Feet ---
    def create_foot(x_offset):
        # Stem (Vertical part)
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        stem = bpy.context.active_object
        stem.scale = (0.02, 0.04, 0.15)
        stem.location = (x_offset, 0, -height/2 - 0.075)
        bpy.ops.object.transform_apply(scale=True, location=True)
        
        # Base (Horizontal part of T)
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        base = bpy.context.active_object
        base.scale = (0.02, 0.35, 0.02)
        base.location = (x_offset, 0, -height/2 - 0.15)
        bpy.ops.object.transform_apply(scale=True, location=True)
        
        # Join the two parts into one object
        stem.select_set(True)
        base.select_set(True)
        bpy.context.view_layer.objects.active = stem
        bpy.ops.object.join()
        stem.data.materials.append(mat_gold)
        return stem

    # Place feet at the corners (with small offset from extreme edge for realism)
    foot_x = (width / 2) - 0.1
    create_foot(foot_x)
    create_foot(-foot_x)

# Run the script
clear_scene()
create_tv()

# Final rotation to present from a slight angle
bpy.ops.object.select_all(action='SELECT')
bpy.ops.transform.rotate(value=math.radians(-25), orient_axis='Z')
bpy.ops.transform.rotate(value=math.radians(10), orient_axis='X')
