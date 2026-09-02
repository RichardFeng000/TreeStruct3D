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
    bpy.ops.object.text_add(location=(index * 1.4, 0, 0))
    obj = bpy.context.active_object
    obj.data.body = char
    
    # Set text properties for better legibility before conversion
    obj.data.size = 1.2
    obj.data.extrude = 0.0  
    
    # Convert to Curve to utilize the bevel_depth (tubular) property
    bpy.ops.object.convert(target='CURVE')
    curve = obj.data
    
    # To ensure a clean tube, we disable filling and set a specific bevel depth
    curve.fill_mode = 'NONE' 
    curve.bevel_depth = 0.12  # Reduced from 0.18 to prevent blobbing/merging
    curve.bevel_resolution = 12 # Higher resolution for smoother tubes without relying solely on Subdiv
    
    # Convert to Mesh for modifiers and final geometry
    bpy.ops.object.convert(target='MESH')
    
    # Material Slots: Slot 0 (Navy Outer), Slot 1 (Vivid Blue Inner)
    obj.data.materials.append(navy_mat)
    obj.data.materials.append(vivid_mat)
    
    # Solidify creates the inner wall of the balloon tube
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.06 # Give it a visible thickness for the interior material
    solid.offset = -1      # Push thickness inward
    solid.material_offset = 1 # Assigns Material Index 1 to the inner surface
    
    # Use Subdivision Surface sparingly to keep characters legible but rounded
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1 
    subsurf.render_levels = 2
    
    bpy.ops.object.shade_smooth()
    
    return obj

def main():
    clear_scene()
    
    # Material Setup
    navy_mat = create_material(
        "NavyGloss", 
        (0.005, 0.01, 0.1, 1.0), # Deep navy blue
        0.2, 
        0.1
    )
    
    vivid_mat = create_material(
        "VividReflect", 
        (0.0, 0.4, 1.0, 1.0), # Bright vivid blue
        0.9, 
        0.05
    )
    
    text_string = "BALLOONS"
    letters = []
    
    for i, char in enumerate(text_string):
        letter_obj = create_balloon_letter(char, i, navy_mat, vivid_mat)
        letters.append(letter_obj)
        
    # Centering the sign
    total_width = (len(text_string) - 1) * 1.4
    offset_x = total_width / 2
    
    for obj in letters:
        obj.location.x -= offset_x
        
    # Join into one object for a coherent assembly
    bpy.ops.object.select_all(action='DESELECT')
    for obj in letters:
        obj.select_set(True)
        
    if letters:
        bpy.context.view_layer.objects.active = letters[0]
        bpy.ops.object.join()
        final_obj = bpy.context.active_object
        final_obj.name = "BalloonSign"
        
        # Apply modifiers to bake geometry for the final result
        # Order is critical: Solidify first (create inner wall), then Subdiv (smooth)
        bpy.ops.object.modifier_apply(modifier="Solidify")
        bpy.ops.object.modifier_apply(modifier="Subdiv")

if __name__ == "__main__":
    main()
