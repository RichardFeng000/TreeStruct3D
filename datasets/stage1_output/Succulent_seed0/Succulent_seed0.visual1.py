import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a waxy pink material for the succulent."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Pale pink color
        bsdf.inputs['Base Color'].default_value = color
        # Waxy/fleshy properties
        bsdf.inputs['Roughness'].default_value = 0.3
        bsdf.inputs['Specular IOR Level'].default_value = 0.5
    return mat

def create_fleshy_petal(name, scale_factor):
    """Creates a thick, fleshy succulent leaf."""
    bm = bmesh.new()
    # Start with a UV sphere for volume
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=1.0)
    
    for v in bm.verts:
        # Local coordinates (before scaling)
        x, y, z = v.co
        
        # Transform sphere into an obovate/fleshy shape
        # Length is Z, Width is X, Thickness is Y
        # Stretch it out along Z
        z_new = z * 1.5
        
        # Shape the width (X) based on height (Z)
        # We want a bulbous end and a tapered base
        # Normalizing z to [0, 1] for easier shaping
        norm_z = (z + 1) / 2.0 
        
        # Width profile: wide at top, narrow at bottom
        # Use a polynomial or sine wave to create the fleshy swell
        width_factor = 0.7 * (norm_z**0.5) 
        x_new = x * width_factor * scale_factor
        
        # Thickness profile: thick in middle, thin at tips
        thickness_factor = 0.4 * (1.0 - abs(z)*0.5)
        y_new = y * thickness_factor * scale_factor
        
        v.co = Vector((x_new, y_new, z_new))

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    # Ensure it's smooth for that fleshy look
    for poly in obj.data.polygons:
        poly.use_smooth = True
        
    return obj

def create_filament():
    """Creates a small protruding center filament."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.03, radius2=0.0, depth=0.4)
    
    mesh = bpy.data.meshes.new("filament")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("filament", mesh)
    bpy.context.collection.objects.link(obj)
    for poly in obj.data.polygons:
        poly.use_smooth = True
        
    return obj

def assemble_succulent():
    clear_scene()
    
    # Pale pink color (R, G, B, A)
    pink_mat = create_material("SucculentPink", (1.0, 0.85, 0.9, 1.0))
    
    num_leaves = 64
    golden_angle = math.radians(137.5)
    
    # Create the rosette from outer/bottom to inner/top
    for i in range(num_leaves):
        t = i / float(num_leaves) # 0 (outer) to 1 (inner)
        
        angle = i * golden_angle
        # Radius decreases towards center
        radius = 2.8 * (1.0 - t**0.5)
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        z = t * 1.2 # Height rise
        
        # Size: Outer leaves are larger, inner smaller
        scale = 1.4 * (1.0 - t*0.6)
        
        petal = create_fleshy_petal(f"Leaf_{i}", scale)
        petal.data.materials.append(pink_mat)
        
        # Positioning
        petal.location = (x, y, z)
        
        # Orientation
        # Point the leaf away from center and tilt based on age (t)
        petal.rotation_mode = 'XYZ'
        petal.rotation_euler[2] = angle + math.pi/2
        # Outer leaves flatten out, inner ones stand up
        petal.rotation_euler[0] = 0.4 + (t * 1.1) 
        petal.rotation_euler[1] = (random.random() - 0.5) * 0.1

    # Center filaments: ensure they are visible and protruding from the top center
    num_filaments = 12
    for i in range(num_filaments):
        f = create_filament()
        f.data.materials.append(pink_mat)
        
        angle = i * (2 * math.pi / num_filaments)
        # Place them slightly above the highest leaves
        r = 0.1 + (random.random() * 0.1)
        f.location = (r * math.cos(angle), r * math.sin(angle), 1.3)
        f.rotation_mode = 'XYZ'
        # Tilt slightly outward for a blooming effect
        f.rotation_euler[0] = 0.3 + random.random()*0.2
        f.rotation_euler[2] = angle

    # Final assembly: Join all to one object
    bpy.ops.object.select_all(action='SELECT')
    if bpy.context.selected_objects:
        bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
        bpy.ops.object.join()
        final_obj = bpy.context.active_object
        final_obj.name = "SucculentPlant"

if __name__ == "__main__":
    assemble_succulent()
