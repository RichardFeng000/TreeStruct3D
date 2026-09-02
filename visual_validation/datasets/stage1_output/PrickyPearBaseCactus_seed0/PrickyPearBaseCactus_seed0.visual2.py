import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Clears all objects from the current Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_pad_mesh(name="Pad"):
    """
    Creates a single cactus pad as a flattened, slightly pinched elliptical form.
    The 'flat' faces are the top/bottom (Z axis).
    """
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    # UV sphere for the pad base
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0)
    
    for v in bm.verts:
        # Flatten into a disk (Z is thickness)
        v.co.z *= 0.2
        # Stretch into an oval along X
        v.co.x *= 1.4 
        v.co.y *= 1.0
        
        # Simple pinch effect to make it organic
        dist = Vector((v.co.x, v.co.y, 0)).length
        if dist > 0.7:
            pinch = 1.0 - (dist - 0.7) * 0.3
            v.co.x *= pinch
            v.co.y *= pinch
    
    bm.to_mesh(mesh)
    bm.free()
    return obj

def assemble_cactus():
    """Builds a vertically stacked prickly pear cactus."""
    # Root pad
    root = create_pad_mesh("RootPad")
    root.location = (0, 0, 0)
    # Start it slightly tilted for naturalism
    root.rotation_euler = (0.2, 0, 0)
    
    active_pads = [root]
    max_generations = 4
    gen = 0
    
    while gen < max_generations and active_pads:
        next_gen = []
        for parent in active_pads:
            # Each pad typically produces 1-3 new pads from its edges
            num_children = random.randint(1, 3)
            
            # Angles around the perimeter of the oval (X=1.4, Y=1.0)
            angles = []
            if num_children == 1:
                angles = [0] # Top/Front
            elif num_children == 2:
                angles = [-math.pi/3, math.pi/3]
            else:
                angles = [-2*math.pi/3, 0, 2*math.pi/3]

            for angle in angles:
                # Jitter the angle for organic look
                angle += random.uniform(-0.3, 0.3)
                
                # Local offset to place child at the edge of parent
                # We use a vector on the XY plane (the 'flat' part of the pad)
                local_pos = Vector((math.cos(angle) * 1.2, math.sin(angle) * 0.8, 0))
                
                # Calculate world position using parent's matrix
                world_pos = parent.matrix_world @ local_pos
                
                child = create_pad_mesh(f"Pad_{gen}_{len(next_gen)}")
                child.location = world_pos
                
                # Orientation: 
                # The child should be tilted relative to the parent and generally "upwards"
                # We start with the parent's rotation and add a tilt away from center
                tilt_x = random.uniform(0.3, 0.8) # Tilt upwards/outwards
                tilt_y = random.uniform(-0.4, 0.4)
                
                child.rotation_euler = (
                    parent.rotation_euler[0] + tilt_x,
                    parent.rotation_euler[1] + tilt_y,
                    angle + random.uniform(-0.2, 0.2)
                )
                
                # Scale pads down as they grow higher
                s = max(0.5, 1.0 - (gen * 0.15))
                child.scale = (s, s, s)
                
                next_gen.append(child)
        
        active_pads = next_gen
        gen += 1

    # Join all pads into a single mesh object
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if "Pad" in obj.name:
            obj.select_set(True)
    
    if 'RootPad' in bpy.data.objects:
        bpy.context.view_layer.objects.active = bpy.data.objects['RootPad']
        bpy.ops.object.join()
        final_obj = bpy.context.active_object
        final_obj.name = "PricklyPearCactus"
        # Apply transformations to bake the positions into the mesh geometry
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

if __name__ == "__main__":
    clear_scene()
    assemble_cactus()
