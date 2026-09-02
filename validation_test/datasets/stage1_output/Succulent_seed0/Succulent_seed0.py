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
        # Soft pale pink color
        bsdf.inputs['Base Color'].default_value = color
        # Waxy/fleshy properties
        bsdf.inputs['Roughness'].default_value = 0.35
        bsdf.inputs['Specular IOR Level'].default_value = 0.4
    return mat

def create_fleshy_petal(name, scale_factor):
    """Creates a thick, obovate succulent leaf."""
    bm = bmesh.new()
    # Start with a UV sphere for volume
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=1.0)
    
    for v in bm.verts:
        x, y, z = v.co
        
        # We want the leaf to extend from Z=0 up to Z=1.0 * scale_factor
        # Map original sphere Z [-1, 1] -> [0, 1]
        norm_z = (z + 1) / 2.0
        
        # Shape: narrow at base (Z=0), widest near top, rounded tip
        # Width profile for a succulent leaf (spatulate/obovate)
        width_factor = 0.6 * (norm_z**0.7) * (1.0 - 0.3 * norm_z)
        x_new = x * width_factor * scale_factor
        y_new = y * (width_factor * 0.6) * scale_factor # Slightly flatter petal
        
        # Length: stretch along Z, but add a slight curve/taper
        z_new = norm_z * 1.2 * scale_factor
        
        # Add very subtle surface jitter for "detail"
        jitter = (random.random() - 0.5) * 0.01
        v.co = Vector((x_new + jitter, y_new + jitter, z_new))

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for poly in obj.data.polygons:
        poly.use_smooth = True
        
    return obj

def create_filament():
    """Creates a small protruding center filament with a bulbous tip."""
    bm = bmesh.new()
    # Stem
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.02, radius2=0.01, depth=0.3)
    # Shift stem up so base is at 0
    for v in bm.verts:
        v.co.z += 0.15
        
    # Tip (small sphere)
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=8, radius=0.04)
    for v in bm.verts:
        if v.co.z < 0: # only move the new sphere verts roughly
            pass 
    # Actually simpler to just add a separate mesh or shift existing
    # For simplicity in one bmesh, we'll just use the cone and manually bump the top vertices
    for v in bm.verts:
        if v.co.z > 0.29:
            v.co += Vector((0, 0, 0.05))

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
    
    # Soft pale pink (R, G, B, A)
    pink_mat = create_material("SucculentPink", (1.0, 0.88, 0.92, 1.0))
    
    num_leaves = 72
    golden_angle = math.radians(137.5)
    
    # Create the rosette from outer/bottom to inner/top
    for i in range(num_leaves):
        t = i / float(num_leaves) # 0 (outer) to 1 (inner)
        
        angle = i * golden_angle
        # Radius: Outer leaves far, inner close. Use a softer curve for compact look.
        radius = 1.8 * (1.0 - t**0.6)
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        z_pos = t * 0.4 # Slight rise towards center
        
        # Size: Outer leaves larger, inner smaller
        scale = 1.2 * (1.0 - t*0.5)
        
        petal = create_fleshy_petal(f"Leaf_{i}", scale)
        petal.data.materials.append(pink_mat)
        
        # Positioning
        petal.location = (x, y, z_pos)
        
        # Orientation
        petal.rotation_mode = 'XYZ'
        petal.rotation_euler[2] = angle # Point away from center
        
        # Tilt: Outer leaves are almost flat (0 rad), inner ones more upright
        # Since leaf grows along Z, rotation around X/Y tilts it
        tilt = 0.2 + (t * 1.3) # Range ~ 0.2 to 1.5 radians
        petal.rotation_euler[0] = tilt
        
    # Center filaments: Clearly protruding from the top center
    num_filaments = 14
    for i in range(num_filaments):
        f = create_filament()
        f.data.materials.append(pink_mat)
        
        angle = i * (2 * math.pi / num_filaments)
        # Place them tightly at center, but above the inner leaves' bases
        r = 0.1 + (random.random() * 0.15)
        f.location = (r * math.cos(angle), r * math.sin(angle), 0.6)
        
        # Tilt them slightly outward
        f.rotation_mode = 'XYZ'
        f.rotation_euler[0] = 0.4 + random.random()*0.3
        f.rotation_euler[2] = angle

    # Final assembly: Join all to one object for a clean scene
    bpy.ops.object.select_all(action='SELECT')
    if bpy.context.selected_objects:
        bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
        bpy.ops.object.join()
        final_obj = bpy.context.active_object
        final_obj.name = "SucculentPlant"

if __name__ == "__main__":
    assemble_succulent()
