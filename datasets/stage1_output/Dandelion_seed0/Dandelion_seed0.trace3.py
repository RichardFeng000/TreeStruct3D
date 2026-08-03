import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_tube(bm, start, end, radius, segments=6):
    """Helper to add a small cylinder tube to a BMesh."""
    # Create rings at start and end
    ring1 = []
    ring2 = []
    for i in range(segments):
        angle = (2 * math.pi / segments) * i
        # Calculate orthogonal vectors for the circle orientation
        direction = (end - start).normalized()
        up = Vector((0, 0, 1)) if abs(direction.z) < 0.9 else Vector((0, 1, 0))
        v1 = up.cross(direction).normalized()
        v2 = direction.cross(v1).normalized()
        offset = (v1 * math.cos(angle) + v2 * math.sin(angle)) * radius
        ring1.append(bm.verts.new(start + offset))
        ring2.append(bm.verts.new(end + offset))

    # Connect rings with faces
    for i in range(segments):
        v1 = ring1[i]
        v2 = ring1[(i + 1) % segments]
        v3 = ring2[(i + 1) % segments]
        v4 = ring2[i]
        bm.faces.new((v1, v2, v3, v4))

def create_stem(start, end, radius=0.02):
    """Creates a curving stem as a mesh."""
    bm = bmesh.new()
    
    # Create a curved path of points
    num_segments = 20
    mid = (start + end) * 0.5 + Vector((0.3, 0.1, 0)) # Curvature offset
    path = []
    for i in range(num_segments + 1):
        t = i / num_segments
        # Quadratic Bezier interpolation for a gentle curve
        p = (1 - t)**2 * start + 2 * (1 - t) * t * mid + t**2 * end
        path.append(p)

    # Create the tube along the path
    for i in range(num_segments):
        create_tube(bm, path[i], path[i+1], radius, segments=8)

    mesh = bpy.data.meshes.new("StemMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Stem", mesh)
    bpy.context.collection.objects.link(obj)
    
    mat = create_material('StemGreen', (0.1, 0.3, 0.05, 1.0))
    obj.data.materials.append(mat)
    return obj

def create_puffball(center, radius, seed_count=150, scale=1.0, flattened=False):
    """Creates a spherical cluster of dandelion seeds as a single mesh."""
    bm = bmesh.new()
    
    # Central core (tiny sphere)
    core_radius = 0.05 * scale
    segments = 8
    for i in range(segments):
        phi = math.pi * i / segments
        for j in range(segments):
            theta = 2 * math.pi * j / segments
            # Simple core geometry is implicit in the seeds' start points, 
            # but we can add a small central hub if needed.

    for _ in range(seed_count):
        # Random direction on sphere
        phi = random.uniform(0, 2 * math.pi)
        cos_theta = random.uniform(-1, 1)
        sin_theta = math.sqrt(max(0, 1 - cos_theta**2))
        dir_vec = Vector((
            sin_theta * math.cos(phi),
            sin_theta * math.sin(phi),
            cos_theta
        ))
        
        start_p = center
        end_p = center + dir_vec * (radius * scale)
        if flattened:
            # Squash the Z component for fallen seed heads
            end_p.z = center.z + (end_p.z - center.z) * 0.3
        
        # Seed stalk (the beak) - thin cylinder
        create_tube(bm, start_p, end_p, radius * 0.015, segments=4)
        
        # Parachute hairs (pappus) at the tip
        hair_count = random.randint(6, 12)
        hair_length = radius * 0.4 * scale
        
        # Create local basis for hairs
        up = Vector((0, 0, 1)) if abs(dir_vec.z) < 0.9 else Vector((0, 1, 0))
        v1 = up.cross(dir_vec).normalized()
        v2 = dir_vec.cross(v1).normalized()
        
        for j in range(hair_count):
            angle = (2 * math.pi / hair_count) * j
            # Spread hairs outwards from the stalk's direction
            spread = 0.7
            hair_dir = (dir_vec + v1 * math.cos(angle) * spread + v2 * math.sin(angle) * spread).normalized()
            hair_end = end_p + hair_dir * hair_length
            # Very thin tubes for hairs
            create_tube(bm, end_p, hair_end, radius * 0.005, segments=3)

    mesh = bpy.data.meshes.new("PuffballMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Puffball", mesh)
    bpy.context.collection.objects.link(obj)
    
    mat = create_material('SeedWhite', (0.9, 0.9, 0.9, 1.0))
    obj.data.materials.append(mat)
    return obj

def main():
    clear_scene()
    
    # Dimensions and positions
    stem_start = Vector((0, 0, 0))
    stem_end = Vector((0.2, -0.1, 4.0))
    puffball_radius = 0.6
    
    # 1. Stem
    create_stem(stem_start, stem_end)
    
    # 2. Main puffball head
    create_puffball(stem_end, puffball_radius, seed_count=200)
    
    # 3. Fallen puffball at the base
    fallen_center = Vector((0.8, 0.5, 0))
    create_puffball(fallen_center, puffball_radius * 0.7, seed_count=100, scale=0.8, flattened=True)

if __name__ == "__main__":
    main()
