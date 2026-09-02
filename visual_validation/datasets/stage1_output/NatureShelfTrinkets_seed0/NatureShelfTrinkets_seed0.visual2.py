import bpy
import bmesh
import math

def clear_scene():
    """Clears all objects from the current scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_oval_disc(name, rx, ry, height, z_offset, material):
    """Creates an oval disc using a scaled cylinder."""
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=128, 
        radius=1.0, 
        depth=height, 
        location=(0, 0, z_offset + height / 2)
    )
    obj = bpy.context.active_object
    obj.name = name
    
    # Scale to oval shape
    obj.scale = (rx, ry, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Bevel for organic feel
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.02
    bevel.segments = 3
    bpy.ops.object.modifier_apply(modifier="Bevel")
    
    if material:
        obj.data.materials.append(material)
        
    return obj

def create_ridge(radius_factor, rx, ry, thickness, z_pos):
    """Creates a ring that blends better with the surface."""
    bpy.ops.mesh.primitive_torus_add(
        align='WORLD', 
        location=(0, 0, z_pos), 
        major_radius=radius_factor, 
        minor_radius=thickness / 2.0, 
        major_segments=64, 
        minor_segments=12
    )
    ring = bpy.context.active_object
    ring.scale = (rx, ry, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return ring

def main():
    clear_scene()

    # Materials - using more distinct colors to ensure render visibility
    # Cream/Beige: slightly more yellow/brown than white
    cream_mat = create_material("CreamMat", (0.85, 0.78, 0.65, 1.0)) 
    # Dark Charcoal: very dark grey
    charcoal_mat = create_material("CharcoalMat", (0.05, 0.05, 0.06, 1.0))

    # Dimensions
    base_rx, base_ry, base_h = 0.8, 0.6, 0.2
    top_rx, top_ry, top_h = 1.1, 0.9, 0.25
    
    # Base Disc (Dark Charcoal)
    base_disc = create_oval_disc("BaseDisc", base_rx, base_ry, base_h, 0, charcoal_mat)
    
    # Top Disc (Cream/Beige)
    top_disc = create_oval_disc("TopDisc", top_rx, top_ry, top_h, base_h, cream_mat)
    
    # Surface of the top disc where ridges will sit
    surface_z = base_h + top_h
    
    ridge_thickness = 0.02
    num_ridges = 15
    
    ridges = []
    for i in range(1, num_ridges + 1):
        # Tree-ring style spacing (closer together near the outside)
        radius_factor = (i / num_ridges)**0.7 * (top_rx * 0.92)
        
        # Create ring slightly embedded into the top surface for better blending
        ring = create_ridge(
            radius_factor, 
            top_rx, 
            top_ry, 
            ridge_thickness, 
            surface_z - (ridge_thickness * 0.3)
        )
        ridges.append(ring)

    # Join and assign material to ensure consistent coloring
    bpy.context.view_layer.objects.active = top_disc
    for ridge in ridges:
        ridge.select_set(True)
    
    bpy.ops.object.join()
    top_disc.data.materials[0] = cream_mat

if __name__ == "__main__":
    main()
