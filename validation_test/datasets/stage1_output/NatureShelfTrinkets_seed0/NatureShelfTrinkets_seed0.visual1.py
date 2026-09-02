import bpy
import bmesh
import math
import random

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
    """Creates a cylinder and scales it to form an oval disc."""
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
    
    # Bevel edges for a nature-inspired feel
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.03
    bevel.segments = 3
    bpy.ops.object.modifier_apply(modifier="Bevel")
    
    if material:
        obj.data.materials.append(material)
        
    return obj

def create_ridge_ring(radius_factor, rx, ry, thickness, z_pos):
    """Creates a ring that follows the oval proportions."""
    bpy.ops.mesh.primitive_torus_add(
        align='WORLD', 
        location=(0, 0, z_pos), 
        major_radius=radius_factor, 
        minor_radius=thickness / 2.0, 
        major_segments=64, 
        minor_segments=16
    )
    ring = bpy.context.active_object
    ring.scale = (rx, ry, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return ring

def main():
    clear_scene()

    # Materials
    cream_mat = create_material("CreamMat", (0.96, 0.94, 0.86, 1.0)) # Beige/Cream
    charcoal_mat = create_material("CharcoalMat", (0.15, 0.15, 0.17, 1.0)) # Dark Charcoal

    # Proportions: Top disc larger than base
    base_rx, base_ry, base_h = 0.8, 0.6, 0.2
    top_rx, top_ry, top_h = 1.2, 1.0, 0.3
    
    # Create the dark charcoal base disc
    base_disc = create_oval_disc("BaseDisc", base_rx, base_ry, base_h, 0, charcoal_mat)
    
    # Create the cream upper disc
    top_disc = create_oval_disc("TopDisc", top_rx, top_ry, top_h, base_h, cream_mat)
    
    # Calculate Z position for ridges (on top surface)
    actual_surface_z = base_h + top_h
    
    ridge_thickness = 0.03
    num_ridges = 12
    
    ridges = []
    for i in range(1, num_ridges + 1):
        # Tree ring jitter
        jitter = random.uniform(-0.03, 0.03)
        radius_factor = (i / num_ridges) * (top_rx * 0.9) + jitter
        if radius_factor < 0.05: radius_factor = 0.05
        
        ring = create_ridge_ring(
            radius_factor, 
            top_rx, 
            top_ry, 
            ridge_thickness, 
            actual_surface_z + (ridge_thickness * 0.2) # Slightly embedded
        )
        ridges.append(ring)

    # Join ridges to the top disc and assign material
    bpy.context.view_layer.objects.active = top_disc
    for ridge in ridges:
        ridge.select_set(True)
    
    bpy.ops.object.join()
    top_disc.data.materials[0] = cream_mat # Ensure consistency

if __name__ == "__main__":
    main()
