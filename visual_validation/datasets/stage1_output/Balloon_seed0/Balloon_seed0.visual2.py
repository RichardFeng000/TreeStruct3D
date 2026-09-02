import bpy
import bmesh
import math

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

def create_bubble_letter(char, index, navy_mat, vivid_mat):
    """Creates an inflated, hollow bubble letter."""
    # Create Text object
    bpy.ops.object.text_add(location=(index * 1.6, 0, 0))
    obj = bpy.context.active_object
    obj.data.body = char
    
    # Inflated Bubble Geometry settings
    obj.data.size = 1.2
    obj.data.extrude = 0.4      # Depth of the letter (the "thin vertical column" profile)
    obj.data.bevel_depth = 0.15 # Makes it rounded/bubbly
    obj.data.bevel_resolution = 6
    
    # Convert to Mesh for modifiers
    bpy.ops.object.convert(target='MESH')
    
    # Material Slots: Slot 0 (Navy Outer), Slot 1 (Vivid Blue Inner)
    obj.data.materials.append(navy_mat)
    obj.data.materials.append(vivid_mat)
    
    # Solidify creates the interior cavity and wall thickness
    # This allows the vivid blue interior to be seen through the holes of 'B', 'A', 'O'
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = -0.1     # Thickness of the balloon skin
    solid.offset = 0           # Center thickness relative to original surface
    solid.material_offset = 1  # Assigns Material Index 1 (Vivid Blue) to the interior
    
    # Subdivision Surface for smooth, inflated look
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    bpy.ops.object.shade_smooth()
    
    return obj

def main():
    clear_scene()
    
    # Material Setup
    # Navy Glossy Outer
    navy_mat = create_material(
        "NavyGloss", 
        (0.005, 0.01, 0.15, 1.0), # Slightly brighter navy to ensure visibility
        0.1, 
        0.1
    )
    
    # Vivid Blue Reflective Interior
    vivid_mat = create_material(
        "VividReflect", 
        (0.0, 0.4, 1.0, 1.0), # Bright vivid blue
        1.0, 
        0.05
    )
    
    text_string = "BALLOONS"
    letters = []
    
    for i, char in enumerate(text_string):
        letter_obj = create_bubble_letter(char, i, navy_mat, vivid_mat)
        letters.append(letter_obj)
        
    # Centering the sign assembly
    total_width = (len(text_string) - 1) * 1.6
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
        
        # Apply modifiers to bake final geometry
        # Order: Solidify (hollow out) -> Subdiv (smooth the result)
        bpy.ops.object.modifier_apply(modifier="Solidify")
        bpy.ops.object.modifier_apply(modifier="Subdiv")

if __name__ == "__main__":
    main()
