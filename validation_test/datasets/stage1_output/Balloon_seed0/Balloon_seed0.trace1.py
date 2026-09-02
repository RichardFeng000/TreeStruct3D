import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clear all default objects from the scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic, roughness):
    """Create a Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_balloon_letter(char, index, navy_mat, vivid_mat):
    """Creates a single tubular balloon letter."""
    # Create Text object
    bpy.ops.object.text_add(location=(index * 1.3, 0, 0))
    obj = bpy.context.active_object
    obj.data.body = char
    
    # Set text properties for a rounded look
    obj.data.size = 1.0
    obj.data.extrude = 0.0  # We use curve bevel for tubularity
    
    # Convert to Curve to utilize the bevel_depth (tubular) property
    bpy.ops.object.convert(target='CURVE')
    curve = obj.data
    curve.fill_mode = 'NONE' # Only the outline, no filling
    curve.bevel_depth = 0.18
    curve.bevel_resolution = 6
    
    # Convert to Mesh for modifiers and final geometry
    bpy.ops.object.convert(target='MESH')
    
    # Add materials to the object slots
    # Slot 0: Navy Blue (Outer)
    # Slot 1: Vivid Blue (Inner)
    obj.data.materials.append(navy_mat)
    obj.data.materials.append(vivid_mat)
    
    # Subdivision Surface for the 'inflated' bubbly look
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    # Solidify to create an actual interior wall
    # This allows us to distinguish between the outer shell and inner cavity
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = -0.05 # Slight inward thickness
    solid.offset = 0
    # Material offset shifts the material index of generated faces
    # Original faces (outer) stay at Index 0, inner walls move to Index 0 + 1 = 1
    solid.material_offset = 1 
    
    # Shade smooth for that glossy balloon look
    bpy.ops.object.shade_smooth()
    
    return obj

def main():
    clear_scene()
    
    # Setup materials
    # Dark navy-blue glossy outer surface
    navy_mat = create_material(
        "NavyGloss", 
        (0.005, 0.01, 0.1, 1.0), # Deep navy blue
        0.1, 
        0.12
    )
    
    # Vivid blue-tinted reflective interior
    vivid_mat = create_material(
        "VividReflect", 
        (0.0, 0.4, 1.0, 1.0), # Bright vivid blue
        0.9, 
        0.05
    )
    
    text_string = "BALLOONS"
    letters = []
    
    # Create each character as a separate object to manage spacing and modifiers
    for i, char in enumerate(text_string):
        letter_obj = create_balloon_letter(char, i, navy_mat, vivid_mat)
        letters.append(letter_obj)
        
    # Calculate total width for centering
    total_width = (len(text_string) - 1) * 1.3
    offset_x = total_width / 2
    
    for obj in letters:
        obj.location.x -= offset_x
        
    # Join all letters into one coherent object
    bpy.ops.object.select_all(action='DESELECT')
    for obj in letters:
        obj.select_set(True)
        
    if letters:
        bpy.context.view_layer.objects.active = letters[0]
        bpy.ops.object.join()
        final_obj = bpy.context.active_object
        final_obj.name = "BalloonSign"
        
        # To ensure the material offset from Solidify is baked and visible 
        # without needing a render engine, we apply modifiers.
        # However, applying them in order: Subdiv then Solidify (or vice versa)
        # Let's apply for final result.
        bpy.ops.object.modifier_apply(modifier="Subdiv")
        bpy.ops.object.modifier_apply(modifier="Solidify")

if __name__ == "__main__":
    main()
