import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    # Use a list to avoid mutation during iteration
    objs = [obj for obj in bpy.data.objects]
    for obj in objs:
        bpy.data.objects.remove(obj, do_unlink=True)
    
    # Clear meshes and materials just in case
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)

def create_bowl():
    """
    Creates a wide shallow bowl with a rim using a screw modifier approach 
    via BMesh for precision.
    """
    # Define the profile of the bowl's wall and base (X=radius, Y=0, Z=height)
    # The sequence follows the cross-section from center bottom to top outer edge, then back in.
    profile_points = [
        (0.0, 0.0, 0.0),      # Inner bottom center
        (1.6, 0.0, 0.0),      # Bottom inner edge
        (1.7, 0.0, 0.05),     # Bottom outer corner
        (2.1, 0.0, 0.7),      # Top outer rim edge (lower part)
        (2.3, 0.0, 0.8),      # Top outer rim peak
        (2.1, 0.0, 0.8),      # Top inner rim edge
        (1.8, 0.0, 0.5),      # Interior wall slope
        (1.6, 0.0, 0.1),      # Inside bottom corner
        (0.0, 0.0, 0.1)       # Back to center (filling the base)
    ]

    mesh = bpy.data.meshes.new("BowlMesh")
    obj = bpy.data.objects.new("FruitBowl", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    
    # Create vertices for the profile in 3D space
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
    screw_mod.axis = (0, 0, 1)

    # Apply the modifier to make it a real mesh
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Screw")
    
    return obj

def create_fruit(name, radius, location):
    """Creates a smooth spherical fruit."""
    # Use bpy.ops for simple primitive creation
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, 
        location=location, 
        segments=32, 
        ring_count=16
    )
    fruit = bpy.context.active_object
    fruit.name = name
    
    # Set smooth shading for all polygons
    for poly in fruit.data.polygons:
        poly.use_smooth = True
        
    return fruit

def populate_bowl():
    """Places several spherical fruits randomly inside the bowl."""
    num_fruits = 20
    # Bowl interior radius is approx 1.6, height ranges from 0.1 to 0.8
    inner_radius = 1.5
    min_z = 0.15 # Slightly above base center (0.1)
    max_z = 0.7

    fruits_data = []
    for i in range(num_fruits):
        # Random radius for variety to look natural
        r = random.uniform(0.15, 0.28)
        
        placed = False
        attempts = 0
        while not placed and attempts < 60:
            # Random position in circular area
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, inner_radius - r)
            x = math.cos(angle) * dist
            y = math.sin(angle) * dist
            z = random.uniform(min_z, max_z)
            
            loc = Vector((x, y, z))
            
            # Basic collision check to prevent severe overlap
            too_close = False
            for other_r, other_loc in fruits_data:
                if (loc - other_loc).length < (r + other_r) * 0.75:
                    too_close = True
                    break
            
            # Also check if fruit is too high for its radial distance 
            # (simple approximation of bowl slope)
            # Slope from z=0.1 at r=1.6 to z=0.8 at r=2.1
            # we just constrain height roughly relative to dist
            if too_close:
                attempts += 1
            else:
                fruits_data.append((r, loc))
                create_fruit(f"Fruit_{i}", r, loc)
                placed = True
                attempts += 1

def main():
    # Clean the environment
    clear_scene()
    
    # Create the wide shallow bowl geometry
    bowl = create_bowl()
    
    # Populate with spheres (fruits)
    populate_bowl()
    
    # Final scene update
    bpy.context.view_layer.update()

if __name__ == "__main__":
    main()
