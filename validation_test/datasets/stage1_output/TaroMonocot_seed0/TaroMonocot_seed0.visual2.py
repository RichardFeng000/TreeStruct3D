import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, color):
    """Creates a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_leaf(name, size=1.0):
    """Creates a taro-style arrowhead leaf with smooth geometry."""
    bm = bmesh.new()
    
    # Define the outline of an arrow/heart shape
    # Normalized coordinates: Tip at top (Y+), Notch at bottom (Y-)
    points = [
        Vector((0, 2.0)),      # Tip
        Vector((0.7, 1.6)),    # Shoulder
        Vector((1.3, 0.6)),    # Side width
        Vector((1.1, -0.7)),   # Bottom outer
        Vector((0, -0.3)),     # Notch (stem attachment)
        Vector((-1.1, -0.7)),  # Bottom outer
        Vector((-1.3, 0.6)),   # Side width
        Vector((-0.7, 1.6)),   # Shoulder
    ]
    
    res = 48
    outline_verts = []
    for i in range(res):
        t = (i / res) * len(points)
        idx = int(t) % len(points)
        next_idx = (idx + 1) % len(points)
        alpha = t - int(t)
        p = points[idx].lerp(points[next_idx], alpha)
        outline_verts.append(bm.verts.new(Vector((p.x * size, p.y * size, 0))))

    # To avoid the "pinched" look, we create concentric rings of vertices instead of one center point
    rings = []
    num_rings = 4
    for r in range(num_rings):
        ring_verts = []
        scale = (r + 1) / num_rings
        for i in range(res):
            # Interpolate between center (0,0) and the outline
            p_out = outline_verts[i].co
            p_in = Vector((0, -0.2 * size)) # Stem attachment point offset
            v = bm.verts.new(p_in.lerp(p_out, scale))
            ring_verts.append(v)
        rings.append(ring_verts)

    # Connect the rings into faces
    for r in range(num_rings - 1):
        for i in range(res):
            v1 = rings[r][i]
            v2 = rings[r][(i + 1) % res]
            v3 = rings[r+1][(i + 1) % res]
            v4 = rings[r+1][i]
            bm.faces.new((v1, v2, v3, v4))

    # Connect the innermost ring to a single center point for clean topology at the stem
    center_v = bm.verts.new(Vector((0, -0.2 * size, 0)))
    for i in range(res):
        bm.faces.new((center_v, rings[0][(i + 1) % res], rings[0][i]))

    # Apply organic curvature (bending and drooping)
    for v in bm.verts:
        x, y, z = v.co
        dist_sq = x*x + y*y
        # Parabolic dome for the leaf surface
        v.co.z += (1.0 - (dist_sq / (4.0 * size**2))) * 0.4 * size
        # Add a slight fold/droop: lower the edges relative to center
        v.co.z -= abs(x) * 0.15 * size

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for poly in obj.data.polygons:
        poly.use_smooth = True
        
    return obj

def create_petiole(name, length=3.0, radius=0.07):
    """Creates a long, tapered stem."""
    bm = bmesh.new()
    segments = 16
    ring_res = 12
    rings = []
    
    for i in range(segments + 1):
        t = i / segments
        z = t * length
        # Organic gentle curve away from origin
        cx = math.sin(t * math.pi * 0.5) * 0.3
        cy = math.cos(t * math.pi * 0.5) * 0.1
        
        ring = []
        for j in range(ring_res):
            angle = (j / ring_res) * 2 * math.pi
            # Taper: slightly thinner at the top
            r = radius * (0.8 + 0.2 * t)
            vx = cx + math.cos(angle) * r
            vy = cy + math.sin(angle) * r
            vz = z
            ring.append(bm.verts.new(Vector((vx, vy, vz))))
        rings.append(ring)

    for i in range(len(rings) - 1):
        for j in range(ring_res):
            v1 = rings[i][j]
            v2 = rings[i][(j+1)%ring_res]
            v3 = rings[i+1][(j+1)%ring_res]
            v4 = rings[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def assemble_taro():
    clear_scene()
    
    # Vibrant light green coloring
    leaf_mat = create_material("LeafMat", (0.6, 0.9, 0.3, 1.0)) 
    stem_mat = create_material("StemMat", (0.4, 0.7, 0.2, 1.0))
    
    # Base corm
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(0, 0, 0))
    corm = bpy.context.active_object
    corm.name = "TaroBase"
    corm.scale = (1.2, 1.2, 0.6)
    corm.data.materials.append(stem_mat)

    num_leaves = 7
    for i in range(num_leaves):
        angle = (i / num_leaves) * 2 * math.pi
        length = random.uniform(3.5, 4.8)
        size = random.uniform(1.6, 2.3)
        
        # Petiole - angled more outward to prevent bunching
        petiole = create_petiole(f"Petiole_{i}", length=length)
        petiole.data.materials.append(stem_mat)
        
        # Distribute around Z axis and tilt significantly outward
        petiole.rotation_euler[2] = angle
        petiole.rotation_euler[0] = math.radians(random.uniform(25, 40)) 
        
        # Calculate world position of the stem tip
        # The petiole is created along Z axis; its tip is at (cx, cy, length)
        tip_local = Vector((0.3 * math.sin(math.pi*0.5), 0.1 * math.cos(math.pi*0.5), length))
        tip_world = petiole.matrix_world @ tip_local
        
        # Leaf - placed at stem tip and drooped outward
        leaf = create_leaf(f"Leaf_{i}", size=size)
        leaf.data.materials.append(leaf_mat)
        leaf.location = tip_world
        
        # Align leaf to point away from the center of the plant
        leaf.rotation_euler[2] = angle + math.pi/2
        leaf.rotation_euler[0] = math.radians(random.uniform(30, 50)) # Tilt outward
        leaf.rotation_euler[1] = math.radians(random.uniform(40, 70)) # Droop downward

if __name__ == "__main__":
    assemble_taro()
