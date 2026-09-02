import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default scene of all objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_barrel_body(num_ribs=16, rib_amplitude=0.15, squatness=0.7):
    """Creates the main ribbed body of the barrel cactus."""
    # Create a UV sphere as the base
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0)
    obj = bpy.context.active_object
    obj.name = "CactusBody"

    # Scale it to be squat/oval
    obj.scale[2] = squatness
    bpy.ops.object.transform_apply(scale=True)

    # Use BMesh to deform the vertices into ribs
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    for v in bm.verts:
        # Calculate angle around Z axis
        angle = math.atan2(v.co.y, v.co.x)
        # Displacement based on sine wave for ribs
        displacement = 1.0 + rib_amplitude * math.cos(num_ribs * angle)
        
        # Apply displacement to X and Y coordinates
        # We maintain the Z coordinate to keep the squat shape
        v.co.x *= displacement
        v.co.y *= displacement

    bm.to_mesh(obj.data)
    bm.free()
    return obj

def create_spine(location, normal):
    """Creates a single thin spine cone."""
    # Length and radius of the spine
    length = random.uniform(0.15, 0.35)
    radius = 0.008
    
    # Create a small cone for the spine
    bpy.ops.mesh.primitive_cone_add(
        vertices=4, 
        radius1=radius, 
        radius2=0, 
        depth=length, 
        location=(0, 0, 0)
    )
    spine = bpy.context.active_object
    spine.name = "Spine"

    # Align spine to the normal vector
    # The default cone is aligned along Z
    rotation_vec = Vector((0, 0, 1))
    rotation_quat = rotation_vec.rotation_difference(normal)
    spine.rotation_mode = 'QUATERNION'
    spine.rotation_quaternion = rotation_quat

    # Move spine so base is at location
    # Shift by half length along the normal because cone origin is center
    spine.location = location + (normal * (length / 2))

def create_areoles_and_spines(body_obj):
    """Adds areoles and clusters of spines to the ribs."""
    bm = bmesh.new()
    bm.from_mesh(body_obj.data)
    
    # We only want to place areoles on the ridges (peaks of the ribbing)
    # Identify vertices that are relatively far from center in XY plane
    # and distributed vertically.
    
    # To avoid too many spines, we sample a subset of ridge vertices
    ridge_verts = []
    for v in bm.verts:
        # Check if vertex is roughly on a rib peak (high radius relative to neighbors)
        # In our simple case, we can just check the distance from center
        dist = math.sqrt(v.co.x**2 + v.co.y**2)
        if dist > 0.9: # Only place on the protruding parts
            ridge_verts.append(v)

    # Subsample ridge vertices to create discrete areoles
    # Group them by approximate vertical position and angle
    areole_positions = []
    used_indices = set()
    
    # Sort by Z to distribute vertically
    ridge_verts.sort(key=lambda v: v.co.z)
    
    # Simple grid-like sampling for areoles
    for i in range(0, len(ridge_verts), 12): # Jump to space them out
        v = ridge_verts[i]
        # Check if this vertex is significantly far from already placed areoles
        is_too_close = False
        for pos in areole_positions:
            if (Vector(v.co) - pos).length < 0.25:
                is_too_close = True
                break
        
        if not is_too_close:
            areole_positions.append(Vector(v.co))

    bm.free()

    # Create spines for each areole position
    for pos in areole_positions:
        # Calculate surface normal at this point (roughly the direction from center)
        normal = (pos - Vector((0, 0, 0))).normalized()
        
        # Each areole has a cluster of 5-10 spines
        num_spines = random.randint(5, 10)
        for _ in range(num_spines):
            # Create a slightly randomized normal for each spine to radiate outward
            rand_normal = Vector((
                normal.x + random.uniform(-0.4, 0.4),
                normal.y + random.uniform(-0.4, 0.4),
                normal.z + random.uniform(-0.4, 0.4)
            )).normalized()
            
            create_spine(pos, rand_normal)

def main():
    clear_scene()

    # Create the body of the cactus
    body = create_barrel_body(num_ribs=14, rib_amplitude=0.2, squatness=0.75)
    
    # Add areoles and spines
    create_areoles_and_spines(body)

    # Join all spines into one object to keep scene clean
    bpy.ops.object.select_all(action='DESELECT')
    # Select all objects except the body
    for obj in bpy.data.objects:
        if obj.name != "CactusBody":
            obj.select_set(True)
            
    # Join selected spines into a single mesh object for efficiency
    if len([o for o in bpy.data.objects if o.name != "CactusBody"]) > 0:
        bpy.context.view_layer.objects.active = [o for o in bpy.data.objects if o.name == "Spine"][0]
        bpy.ops.object.join()
        bpy.context.active_object.name = "Spines"

    # Center everything and ensure it's at the origin
    # The body is already centered. 
    # We can set a material-like look via colors if allowed, but prompt says untextured.

if __name__ == "__main__":
    main()
