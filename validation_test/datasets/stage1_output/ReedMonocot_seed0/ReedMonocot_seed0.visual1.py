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
        # Slightly increase roughness for a matte organic look
        bsdf.inputs['Roughness'].default_value = 0.8
    return mat

def create_leaf_geometry(name, material):
    """Creates a single long, narrow tapered reed leaf mesh."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Leaf dimensions: longer and slightly wider than previous version
    length = 2.8
    max_width = 0.25
    segments = 20
    
    left_side = []
    right_side = []
    
    for i in range(segments + 1):
        t = i / segments
        # Width: narrow at base, peaks early, then tapers slowly to a point
        w = max_width * math.sin(math.pi * t * 0.7 + 0.3) * (1.0 - t**2)**0.5
        if i == segments: w = 0 
        
        # X is length along the leaf
        x = t * length
        # Y creates a slight longitudinal curve (arching)
        y = 0.3 * math.sin(t * math.pi * 0.5)
        # Z creates a graceful droop/bend
        z = -0.6 * (t**1.5)
        
        v_left = bm.verts.new((x, w, z + y)) # Add some variance in the curve
        v_right = bm.verts.new((x, -w, z + y))
        left_side.append(v_left)
        right_side.append(v_right)

    for i in range(segments):
        bm.faces.new((left_side[i], left_side[i+1], right_side[i+1], right_side[i]))
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.data.materials.append(material)
    
    # Subdivision surface for organic smoothness
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    
    return obj

def create_reed():
    clear_scene()
    
    # Brightened muted green (RGBA) to ensure visibility in renders
    muted_green = (0.35, 0.45, 0.15, 1.0)
    mat = create_material("ReedGreen", muted_green)
    
    # --- Stalk Construction ---
    stalk_height = 7.0
    stalk_radius = 0.05
    segments = 32
    
    mesh = bpy.data.meshes.new("Stalk")
    stalk_obj = bpy.data.objects.new("Stalk", mesh)
    bpy.context.collection.objects.link(stalk_obj)
    
    bm = bmesh.new()
    
    # Path for the stalk with organic bend
    path_verts = []
    for i in range(segments + 1):
        z = (i / segments) * stalk_height
        x = 0.3 * math.sin(z * 0.4)
        y = 0.2 * math.cos(z * 0.3)
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
    leaf_pair_count = 7
    start_height = 1.2
    end_height = stalk_height * 0.85
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
            leaf.location = pos
            
            # Rotate to alternate sides and add natural variety
            angle_z = (i * 0.5) + (math.pi if side == -1 else 0)
            leaf.rotation_euler[2] = angle_z
            
            # Tilt them outward and slightly downward for "graceful" look
            leaf.rotation_euler[1] = math.radians(35 + random.uniform(-10, 10))
            leaf.rotation_euler[0] = math.radians(random.uniform(-15, 15))
            
            # Variety in scale (smaller leaves higher up)
            s = 1.2 - (i / leaf_pair_count) * 0.4
            leaf.scale = (s, s, s)
            
            leaf.parent = stalk_obj

    # Smooth shading for all generated meshes
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for poly in obj.data.polygons:
                poly.use_smooth = True

if __name__ == "__main__":
    create_reed()
