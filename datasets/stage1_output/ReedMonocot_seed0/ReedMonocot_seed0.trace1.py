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
    """Creates a simple material with a specific base color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_leaf_geometry(name, material):
    """Creates a single long, narrow tapered leaf mesh."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Leaf dimensions
    length = 1.8
    max_width = 0.12
    segments = 15
    
    left_side = []
    right_side = []
    
    for i in range(segments + 1):
        t = i / segments
        # Width tapers from base (small) -> middle (max) -> tip (zero)
        # Use a function that starts at ~0.2, peaks at mid, ends at 0
        w = max_width * math.sin(math.pi * t * 0.8 + 0.2) * (1.0 - t**0.5)
        if i == segments: w = 0 # Ensure pointed tip
        
        x = t * length
        # Create an organic arch/curve in the leaf's local space
        y = 0
        z = -0.2 * (t**2) # Curve downwards
        
        v_left = bm.verts.new((x, w, z))
        v_right = bm.verts.new((x, -w, z))
        left_side.append(v_left)
        right_side.append(v_right)

    for i in range(segments):
        bm.faces.new((left_side[i], left_side[i+1], right_side[i+1], right_side[i]))

    # Add a center line for better deformation/shading if needed, 
    # but simple strip is fine here.
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.data.materials.append(material)
    
    # Subdivision surface for organic look
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    
    return obj

def create_reed():
    clear_scene()
    
    # Muted green color (RGBA)
    muted_green = (0.2, 0.3, 0.1, 1.0)
    mat = create_material("ReedGreen", muted_green)
    
    # --- Stalk Construction ---
    stalk_height = 6.5
    stalk_radius = 0.04
    segments = 24
    
    mesh = bpy.data.meshes.new("Stalk")
    stalk_obj = bpy.data.objects.new("Stalk", mesh)
    bpy.context.collection.objects.link(stalk_obj)
    
    bm = bmesh.new()
    
    # Create a path for the stalk to give it an organic bend
    path_verts = []
    for i in range(segments + 1):
        z = (i / segments) * stalk_height
        # Slight S-curve
        x = 0.2 * math.sin(z * 0.4)
        y = 0.15 * math.cos(z * 0.3)
        path_verts.append(Vector((x, y, z)))

    # Tube geometry around the path
    ring_res = 8
    rings = []
    for v_pos in path_verts:
        ring = []
        for j in range(ring_res):
            angle = (j / ring_res) * 2 * math.pi
            ox = math.cos(angle) * stalk_radius
            oy = math.sin(angle) * stalk_radius
            # We assume the reed is mostly vertical, so cross sections are roughly XY planes
            ring.append(bm.verts.new(v_pos + Vector((ox, oy, 0))))
        rings.append(ring)

    for i in range(len(rings) - 1):
        for j in range(ring_res):
            v1 = rings[i][j]
            v2 = rings[i][(j + 1) % ring_res]
            v3 = rings[i+1][(j + 1) % ring_res]
            v4 = rings[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    bm.to_mesh(mesh)
    bm.free()
    stalk_obj.data.materials.append(mat)
    
    # --- Leaf Placement ---
    leaf_pair_count = 6
    start_height = 1.0
    end_height = stalk_height * 0.8
    interval = (end_height - start_height) / (leaf_pair_count - 1) if leaf_pair_count > 1 else 1.0
    
    for i in range(leaf_pair_count):
        z_pos = start_height + (i * interval)
        
        # Interpolate position on the stalk path
        t_idx = (z_pos / stalk_height) * segments
        low = int(math.floor(t_idx))
        high = int(math.ceil(t_idx))
        if low >= segments: low = segments - 1
        if high > segments: high = segments
        
        weight = t_idx - low
        pos = path_verts[low] * (1 - weight) + path_verts[high] * weight
        
        # Create a pair of leaves facing opposite directions
        for side in [-1, 1]:
            leaf = create_leaf_geometry(f"Leaf_{i}_{side}", mat)
            
            # Position the leaf at the calculated stalk point
            leaf.location = pos
            
            # Rotation logic: 
            # Z rotation to alternate sides (roughly 180 degrees apart)
            # Y/X rotations for graceful drooping/arching
            angle_z = (i * 0.6) + (math.pi if side == -1 else 0)
            leaf.rotation_euler[2] = angle_z
            
            # Tilt them outward and slightly upward
            leaf.rotation_euler[1] = math.radians(45 + random.uniform(-10, 10))
            leaf.rotation_euler[0] = math.radians(random.uniform(-10, 10))
            
            # Variety in size
            s = random.uniform(0.8, 1.2)
            leaf.scale = (s, s, s)
            
            leaf.parent = stalk_obj

    # Final Touch: Smooth shading for all generated meshes
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for poly in obj.data.polygons:
                poly.use_smooth = True

if __name__ == "__main__":
    create_reed()
