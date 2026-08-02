import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix, Quaternion

def clear_scene():
    """Clears all objects from the current Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_pad_mesh(name="Pad"):
    """
    Creates a single cactus pad as a flattened, slightly pinched elliptical form.
    """
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    
    # Base UV sphere for the pad
    segments = 32
    rings = 16
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    
    for v in bm.verts:
        # Flatten into a disk
        v.co.z *= 0.25
        # Stretch into an oval (elliptical form)
        v.co.x *= 1.3 
        v.co.y *= 1.0
        
        # "Pinch" effect: modify the curvature to make it look less like a pill 
        # and more organic/pinched at the edges
        dist = Vector((v.co.x, v.co.y, 0)).length
        if dist > 0.5:
            pinch = 1.0 - (dist - 0.5) * 0.2
            v.co.x *= pinch
            v.co.y *= pinch
    
    bm.to_mesh(mesh)
    bm.free()
    return obj

def get_growth_point(parent_obj, angle_deg):
    """
    Calculates a point on the perimeter of the parent pad to attach a child.
    """
    # The pads are stretched along X (local), so we account for that in radius
    rad = math.radians(angle_deg)
    # Radius is approx 1.3 on X, 1.0 on Y
    offset = Vector((math.cos(rad) * 1.2, math.sin(rad) * 0.9, 0))
    
    world_matrix = parent_obj.matrix_world
    # Transform the local perimeter point to world space
    world_pos = world_matrix @ offset
    return world_pos

def assemble_cactus():
    """Builds a structured prickly pear cactus."""
    # Create Root pad
    root = create_pad_mesh("RootPad")
    root.location = (0, 0, 0)
    # Tilt it slightly for natural look
    root.rotation_euler = (0.1, 0.1, 0)
    
    active_pads = [root]
    max_generations = 3
    gen = 0
    
    while gen < max_generations and active_pads:
        next_gen = []
        for parent in active_pads:
            # Number of children per pad (1-3)
            num_children = random.randint(1, 3)
            
            # Distribute children around the perimeter
            # We prefer growth generally "upwards" relative to world Z
            angles = [0, 120, 240] if num_children == 3 else \
                     [0, 180] if num_children == 2 else [0]
            
            # Randomize angles slightly
            angles = [a + random.uniform(-20, 20) for a in angles]

            for angle in angles:
                pos = get_growth_point(parent, angle)
                
                child = create_pad_mesh(f"Pad_{gen}_{len(next_gen)}")
                child.location = pos
                
                # Rotate child to be connected "at the end"
                # The child's local -X axis should point towards parent center
                # and its Z axis should generally point up.
                parent_rot = parent.rotation_euler
                
                # Set a rotation that makes it stack vertically/outwards
                child.rotation_euler = (
                    random.uniform(-0.4, 0.4), 
                    random.uniform(-0.4, 0.4), 
                    math.radians(angle) + random.uniform(-0.2, 0.2)
                )
                
                # Scale slightly smaller as we go up the plant
                s = 1.0 - (gen * 0.15)
                child.scale = (s, s, s)
                
                next_gen.append(child)
        
        active_pads = next_gen
        gen += 1

    # Join all pads into a single base mesh object
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if "Pad" in obj.name:
            obj.select_set(True)
    
    # Ensure the root is active before joining
    if 'RootPad' in bpy.data.objects:
        bpy.context.view_layer.objects.active = bpy.data.objects['RootPad']
        bpy.ops.object.join()
        final_obj = bpy.context.active_object
        final_obj.name = "PricklyPearCactus"
        # Clean transformations
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

if __name__ == "__main__":
    clear_scene()
    assemble_cactus()
