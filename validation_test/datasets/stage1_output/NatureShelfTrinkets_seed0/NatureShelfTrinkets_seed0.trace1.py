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

def create_oval_disc(name, rx, ry, height, z_offset):
    """Creates a cylinder and scales it to form an oval disc with beveled edges."""
    # Create base cylinder
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
    
    # Add a small bevel to the top and bottom edges for high fidelity/nature feel
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.02
    bevel.segments = 3
    bpy.ops.object.modifier_apply(modifier="Bevel")
    
    return obj

def create_ridge_ring(radius_factor, rx, ry, thickness, z_pos):
    """Creates a ring that follows the oval proportions of the discs."""
    # major_segments and minor_segments are correct for Blender 4.0+ / 5.0
    bpy.ops.mesh.primitive_torus_add(
        align='WORLD', 
        location=(0, 0, z_pos), 
        major_radius=radius_factor, 
        minor_radius=thickness / 2.0, 
        major_segments=64, 
        minor_segments=16
    )
    ring = bpy.context.active_object
    
    # Scale the ring to match the oval proportions of the main disc
    ring.scale = (rx, ry, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return ring

def main():
    clear_scene()

    # Parameters for the trinket
    # The base is slightly smaller than the top disc
    base_rx = 0.95
    base_ry = 0.75
    base_h = 0.2
    base_z = 0.0
    
    top_rx = 1.2
    top_ry = 1.0
    top_h = 0.3
    top_z = base_h # Sits on top of the base
    
    # Create the dark charcoal base disc (geometry only)
    base_disc = create_oval_disc("BaseDisc", base_rx, base_ry, base_h, base_z)
    
    # Create the cream upper disc (geometry only)
    top_disc = create_oval_disc("TopDisc", top_rx, top_ry, top_h, top_z)
    
    # Generate concentric circular ridge patterns on the top surface of the upper disc
    surface_z = top_z + (top_h / 2) # Top face position relative to center if height was centered
    # Correction: create_oval_disc puts the cylinder from z_offset to z_offset+height.
    # The top surface is actually at top_z + top_h
    actual_surface_z = top_z + top_h
    
    ridge_thickness = 0.03
    num_ridges = 15
    
    ridges = []
    for i in range(1, num_ridges + 1):
        # Nature-inspired jitter for tree ring feel
        jitter = random.uniform(-0.02, 0.02)
        # Distribute radii from center outwards to the edge of top_rx
        radius_factor = (i / num_ridges) * (top_rx * 0.95) + jitter
        if radius_factor < 0.05: radius_factor = 0.05 # Avoid zero or negative radii
        
        # Place the ring so it sits partially embedded for better manifold joining
        ring = create_ridge_ring(
            radius_factor, 
            top_rx, 
            top_ry, 
            ridge_thickness, 
            actual_surface_z + (ridge_thickness * 0.2)
        )
        ridges.append(ring)

    # Join all ridges to the top disc for a single coherent object
    bpy.context.view_layer.objects.active = top_disc
    for ridge in ridges:
        ridge.select_set(True)
    
    bpy.ops.object.join()
    
    # Final naming and polishing
    top_disc.name = "NatureTrinket_Top"
    base_disc.name = "NatureTrinket_Base"

if __name__ == "__main__":
    main()
