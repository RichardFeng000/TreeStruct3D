import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Clear all objects from the current scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def add_pad(bm, center, scale, rotation):
    """Creates a flattened oval pad in the provided BMesh."""
    # Record starting index to identify new vertices
    start_index = len(bm.verts)
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12)
    
    # Rotation matrix
    rot_mat = Matrix.Rotation(rotation[0], 4, 'X') @ \
              Matrix.Rotation(rotation[1], 4, 'Y') @ \
              Matrix.Rotation(rotation[2], 4, 'Z')
              
    # Apply transformation to new vertices only
    for v in bm.verts[start_index:]:
        # Scale into an oval (X: width, Y: thickness, Z: height)
        v.co.x *= scale[0]
        v.co.y *= scale[1]
        v.co.z *= scale[2]
        # Rotate and Translate
        v.co = (rot_mat @ v.co) + center

def add_spine(bm, start_pos, normal, length):
    """Creates a thin cone as a spine."""
    radius = 0.005
    segments = 4
    
    # Create base vertices around the normal
    base_verts = []
    perp = Vector((0, 0, 1)) if abs(normal.z) < 0.9 else Vector((0, 1, 0))
    side_a = normal.cross(perp).normalized()
    side_b = normal.cross(side_a).normalized()
    
    for i in range(segments):
        angle = (2 * math.pi / segments) * i
        offset = (side_a * math.cos(angle) + side_b * math.sin(angle)) * radius
        base_verts.append(bm.verts.new(start_pos + offset))

    # Create tip vertex
    tip = bm.verts.new(start_pos + normal * length)

    # Connect faces
    for i in range(segments):
        try:
            bm.faces.new((base_verts[i], base_verts[(i+1)%segments], tip))
        except ValueError:
            pass # Face already exists

def generate_cactus():
    clear_scene()
    
    # Create main mesh and object
    mesh = bpy.data.meshes.new("PricklyPear")
    obj = bpy.data.objects.new("PricklyPear", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    # Growth Parameters
    base_scale = Vector((1.0, 0.3, 1.2)) # Width, Thickness, Height
    max_depth = 5
    
    # queue for growth: (position, rotation, current_scale)
    growth_queue = [(Vector((0, 0, 0)), Vector((0, 0, 0)), base_scale)]
    
    # To track which pads we've created to avoid overcrowding
    active_pads = []

    for depth in range(max_depth):
        next_queue = []
        taper = 0.8 ** depth
        layer_scale = Vector((base_scale.x * taper, base_scale.y * taper, base_scale.z * taper))
        
        for pos, rot, scale in growth_queue:
            # Slight organic variation in rotation for each pad
            rand_rot = Vector((
                rot.x + random.uniform(-0.3, 0.3),
                rot.y + random.uniform(-0.3, 0.3),
                rot.z + random.uniform(-0.5, 0.5)
            ))
            
            # Create the pad geometry
            add_pad(bm, pos, layer_scale, rand_rot)
            
            # Calculate growth point for next pads (top of current pad)
            rot_mat = Matrix.Rotation(rand_rot.x, 4, 'X') @ \
                      Matrix.Rotation(rand_rot.y, 4, 'Y') @ \
                      Matrix.Rotation(rand_rot.z, 4, 'Z')
            world_up = (rot_mat @ Vector((0, 0, 1))).to_3d()
            top_center = pos + world_up * layer_scale.z
            
            # Decide how many branches to sprout on top/edges
            if depth < max_depth - 1:
                num_branches = random.randint(1, 2) if depth > 0 else 2
                for i in range(num_branches):
                    offset_dir = Vector((random.uniform(-1, 1), random.uniform(-1, 1), 0)).normalized()
                    child_pos = top_center + (offset_dir * (layer_scale.x * 0.4))
                    next_queue.append((child_pos, rand_rot, layer_scale))
        
        growth_queue = next_queue

    # Finalize vertices for spine placement
    bm.verts.ensure_lookup_table()
    if len(bm.verts) == 0:
        # Fallback if growth failed
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12)
    
    # Distribute spines (areoles)
    num_spines = 1500
    verts_list = bm.verts[:]
    for _ in range(num_spines):
        v = random.choice(verts_list)
        
        # Compute vertex normal for spine direction
        normal = v.calc_normal() if hasattr(v, 'calc_normal') else Vector((0, 1, 0))
        if not normal: # Handle zero vectors
            normal = (v.co).normalized()

        # Mix of long needles and short bristles
        if random.random() > 0.85:
            length = random.uniform(0.2, 0.4) # Long needle
        else:
            length = random.uniform(0.03, 0.1) # Short bristle
            
        add_spine(bm, v.co, normal, length)

    # Final mesh preparation
    bm.to_mesh(mesh)
    bm.free()
    
    # Center the cactus on the ground (Z=0)
    bbox = obj.bound_box
    min_z = min([v[2] for v in bbox])
    obj.location.z = -min_z

if __name__ == "__main__":
    generate_cactus()
