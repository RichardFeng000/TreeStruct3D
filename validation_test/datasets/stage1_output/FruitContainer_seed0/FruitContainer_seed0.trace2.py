import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    objs = [obj for obj in bpy.data.objects]
    for obj in objs:
        bpy.data.objects.remove(obj, do_unlink=True)
    
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)

def create_bowl():
    """
    Creates a wide shallow bowl with a rim using the Screw modifier.
    Corrected the axis assignment to use string enum 'Z'.
    """
    # Define the profile of the bowl's wall and base (X=radius, Z=height)
    # Cross-section from center bottom to top outer edge, then back in for thickness.
    profile_points = [
        (0.0, 0.0, 0.0),      # Inner bottom center
        (1.5, 0.0, 0.0),      # Bottom inner edge
        (1.6, 0.0, 0.02),     # Bottom outer corner
        (2.2, 0.0, 0.6),      # Top outer rim side
        (2.3, 0.0, 0.7),      # Top outer rim peak
        (2.1, 0.0, 0.7),      # Top inner rim edge
        (1.9, 0.0, 0.5),      # Interior wall slope
        (1.4, 0.0, 0.05),     # Inside bottom corner
        (0.0, 0.0, 0.05)      # Back to center (filling the base)
    ]

    mesh = bpy.data.meshes.new("BowlMesh")
    obj = bpy.data.objects.new("FruitBowl", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    
    # Create vertices for the profile
    verts = []
    for p in profile_points:
        verts.append(bm.verts.new(p))
    
    # Connect them into an edge chain
    for i in range(len(verts) - 1):
        bm.edges.new((verts[i], verts[i+1]))

    bm.to_mesh(mesh)
    bm.free()

    # Apply Screw Modifier to rotate the profile 360 degrees around Z axis
    screw_mod = obj.modifiers.new(name="Screw", type='SCREW')
    screw_mod.angle = 2 * math.pi
    screw_mod.steps = 64
    screw_mod.render_steps = 64
    # FIX: The axis property is a string enum ('X', 'Y', 'Z'), not a tuple/vector.
    screw_mod.axis = 'Z'

    # Apply the modifier to make it a real mesh
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=screw_mod.name)
    
    # Smooth shading for the bowl
    for poly in obj.data.polygons:
        poly.use_smooth = True

    return obj

def create_fruit(name, radius, location):
    """Creates a smooth spherical fruit."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, 
        location=location, 
        segments=32, 
        ring_count=16
    )
    fruit = bpy.context.active_object
    fruit.name = name
    
    # Set smooth shading
    for poly in fruit.data.polygons:
        poly.use_smooth = True
        
    return fruit

def populate_bowl():
    """Places several spherical fruits randomly inside the bowl."""
    num_fruits = 25
    # Bowl interior radius is roughly 1.5, height varies from 0.05 to 0.7
    inner_radius = 1.4
    min_z = 0.1
    max_z = 0.6

    fruits_data = []
    for i in range(num_fruits):
        # Random radius for variety
        r = random.uniform(0.12, 0.25)
        
        placed = False
        attempts = 0
        while not placed and attempts < 100:
            # Random position within the bowl's footprint
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, inner_radius - r)
            x = math.cos(angle) * dist
            y = math.sin(angle) * dist
            z = random.uniform(min_z, max_z)
            
            loc = Vector((x, y, z))
            
            # Collision check: ensure spheres don't overlap too much
            too_close = False
            for other_r, other_loc in fruits_data:
                if (loc - other_loc).length < (r + other_r) * 0.85:
                    too_close = True
                    break
            
            # Heuristic to keep them below the rim based on distance from center
            # The wall slopes up from z=0.1 at r=1.4 to z=0.7 at r=2.1 (simplified)
            # We constrain height for fruits near the center
            if dist < 0.5 and z > 0.4: 
                too_close = True

            if too_close:
                attempts += 1
            else:
                fruits_data.append((r, loc))
                create_fruit(f"Fruit_{i}", r, loc)
                placed = True

def main():
    # Clean the environment
    clear_scene()
    
    # Create bowl geometry
    bowl = create_bowl()
    
    # Populate with fruits
    populate_bowl()
    
    # Update scene
    bpy.context.view_layer.update()

if __name__ == "__main__":
    main()
