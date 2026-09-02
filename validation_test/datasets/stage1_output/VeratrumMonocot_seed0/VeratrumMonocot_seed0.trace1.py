import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_leaf(name, angle_deg, scale=1.0, material=None):
    """Creates a broad, plicate (ribbed) Veratrum leaf using BMesh."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    
    # Leaf parameters
    segments_length = 40
    segments_width = 32
    leaf_len = 5.0 * scale
    leaf_max_w = 1.4 * scale
    num_pleats = 8

    verts = []
    for i in range(segments_length + 1):
        t = i / segments_length # 0 to 1
        
        # Width profile: narrow at base, wide middle, point at tip
        w_factor = math.sin(math.pi * (t**0.8)) if t > 0 else 0
        current_half_width = (leaf_max_w * 0.5) * w_factor
        
        # Arching curvature
        z_bend = -0.6 * (t**2) * scale
        y_offset = t * leaf_len
        
        row = []
        for j in range(segments_width + 1):
            u = (j / segments_width) - 0.5 # -0.5 to 0.5
            
            # Pleat effect: sine wave along the width, constant over length
            pleat_depth = 0.1 * math.sin(u * math.pi * num_pleats) * scale
            
            x_pos = u * 2.0 * current_half_width
            v = bm.verts.new(Vector((x_pos, y_offset, z_bend + pleat_depth)))
            row.append(v)
        verts.append(row)

    # Create faces
    for i in range(segments_length):
        for j in range(segments_width):
            bm.faces.new((
                verts[i][j],
                verts[i+1][j],
                verts[i+1][j+1],
                verts[i][j+1]
            ))

    # Smooth shading
    for f in bm.faces:
        f.smooth = True

    bm.to_mesh(mesh)
    bm.free()

    # Position and Rotate
    obj.rotation_euler[2] = math.radians(angle_deg)
    # Tilt outward from center
    obj.rotation_euler[0] = math.radians(-15 + random.uniform(-5, 5))
    
    if material:
        obj.data.materials.append(material)
    return obj

def create_stalk_mesh(name, points, radius, material):
    """Creates a stalk mesh by lofting circles along the provided points."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    res = 8
    
    prev_ring = []
    for i, p in enumerate(points):
        # Taper radius slightly as it goes up
        t = i / len(points)
        current_r = radius * (1.0 - 0.4 * t)
        
        ring = []
        for j in range(res):
            angle = (2 * math.pi * j) / res
            offset = Vector((math.cos(angle) * current_r, math.sin(angle) * current_r, 0))
            # We need to orient the ring perpendicular to the stalk direction
            if i < len(points) - 1:
                dir_vec = (points[i+1] - p).normalized()
            else:
                dir_vec = (p - points[i-1]).normalized()
            
            # Simple orthonormal basis for ring orientation
            up = Vector((0, 0, 1)) if abs(dir_vec.z) < 0.9 else Vector((0, 1, 0))
            right = dir_vec.cross(up).normalized()
            top = dir_vec.cross(right).normalized()
            
            actual_offset = (right * offset.x) + (top * offset.y)
            v = bm.verts.new(p + actual_offset)
            ring.append(v)
        
        if prev_ring:
            for j in range(res):
                bm.faces.new((
                    prev_ring[j], 
                    prev_ring[(j+1)%res], 
                    ring[(j+1)%res], 
                    ring[j]
                ))
        prev_ring = ring

    # Cap the top
    bm.faces.new(prev_ring[::-1])
    
    for f in bm.faces:
        f.smooth = True

    bm.to_mesh(mesh)
    bm.free()
    
    if material:
        obj.data.materials.append(material)
    return obj

def create_floret(pos, material):
    """Creates a single floret using BMesh (ico sphere)."""
    mesh = bpy.data.meshes.new("Floret")
    obj = bpy.data.objects.new("Floret", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.06, matrix=bpy.types.Object.matrix_world @ bpy.utils.import_api_if_available('mathutils').Matrix.Translation(pos)) 
    # Correction: simply use bmesh creation and then move the object or translate in BM
    
    # Redoing create_floret to avoid matrix issues from previous attempt
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.06)
    # Shift vertices manually
    for v in bm.verts:
        v.co += pos
        
    bm.to_mesh(mesh)
    bm.free()

    if material:
        obj.data.materials.append(material)
    return obj

def main():
    clear_scene()

    # Colors: Muted greens and pale yellow-greens
    leaf_green = create_material("LeafGreen", (0.12, 0.22, 0.08, 1.0))
    stalk_green = create_material("StalkGreen", (0.15, 0.28, 0.1, 1.0))
    floret_color = create_material("FloretColor", (0.4, 0.45, 0.2, 1.0))

    # Basal Leaves
    num_leaves = 16
    for i in range(num_leaves):
        angle = (360 / num_leaves) * i
        scale = random.uniform(0.8, 1.2)
        create_leaf(f"Leaf_{i}", angle, scale, leaf_green)

    # Stalk definition: Arching path
    # Start at origin, go up and curve outwards
    stalk_points = [
        Vector((0, 0, 0)),
        Vector((0.1, 0.2, 1.5)),
        Vector((0.3, 0.6, 3.0)),
        Vector((0.7, 1.2, 4.5)),
        Vector((1.2, 2.0, 5.8))
    ]
    # Interpolate for smoothness
    smooth_points = []
    for i in range(len(stalk_points)-1):
        p1 = stalk_points[i]
        p2 = stalk_points[i+1]
        for t in [x / 5.0 for x in range(5)]:
            smooth_points.append(p1 + (p2 - p1) * t)
    smooth_points.append(stalk_points[-1])

    create_stalk_mesh("FlowerStalk", smooth_points, 0.08, stalk_green)

    # Raceme: Clustered florets on the upper half of the stalk
    start_index = int(len(smooth_points) * 0.5)
    for i in range(start_index, len(smooth_points)):
        pos = smooth_points[i]
        # Cluster size increases slightly towards the tip then tapers
        cluster_size = random.randint(3, 7)
        for _ in range(cluster_size):
            offset = Vector((
                random.uniform(-0.18, 0.18),
                random.uniform(-0.18, 0.18),
                random.uniform(-0.15, 0.15)
            ))
            create_floret(pos + offset, floret_color)

if __name__ == "__main__":
    main()
