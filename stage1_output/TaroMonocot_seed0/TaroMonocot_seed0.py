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
    
    # Define the outline of an arrow/heart shape using 3D vectors to avoid ValueError
    points = [
        Vector((0, 2.0, 0)),      # Tip
        Vector((0.7, 1.6, 0)),    # Shoulder
        Vector((1.3, 0.6, 0)),    # Side width
        Vector((1.1, -0.7, 0)),   # Bottom outer
        Vector((0, -0.3, 0)),     # Notch (stem attachment)
        Vector((-1.1, -0.7, 0)),  # Bottom outer
        Vector((-1.3, 0.6, 0)),   # Side width
        Vector((-0.7, 1.6, 0)),   # Shoulder
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

    # Create concentric rings to fill the leaf surface
    rings = []
    num_rings = 6
    for r in range(num_rings):
        ring_verts = []
        scale = (r + 1) / num_rings
        for i in range(res):
            p_out = outline_verts[i].co
            # Stem attachment point offset as a 3D vector
            p_in = Vector((0, -0.2 * size, 0)) 
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
    segments = 20
    ring_res = 12
    rings = []
    
    for i in range(segments + 1):
        t = i / segments
        z = t * length
        # Organic gentle curve away from origin
        cx = math.sin(t * math.pi * 0.5) * 0.4
        cy = math.cos(t * math.pi * 0.5) * 0.2
        
        ring = []
        for j in range(ring_res):
            angle = (j / ring_res) * 2 * math.pi
            # Taper: slightly thinner at the top
            r = radius * (0.7 + 0.3 * t)
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
    
    # Light green materials
    leaf_mat = create_material("LeafMat", (0.65, 0.95, 0.35, 1.0)) 
    stem_mat = create_material("StemMat", (0.45, 0.75, 0.25, 1.0))
    
    # Base corm
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(0, 0, 0))
    corm = bpy.context.active_object
    corm.name = "TaroBase"
    corm.scale = (1.2, 1.2, 0.6)
    corm.data.materials.append(stem_mat)

    num_leaves = 8
    for i in range(num_leaves):
        angle = (i / num_leaves) * 2 * math.pi
        length = random.uniform(3.5, 4.5)
        size = random.uniform(1.7, 2.2)
        
        # Petiole - angled outward
        petiole = create_petiole(f"Petiole_{i}", length=length)
        petiole.data.materials.append(stem_mat)
        
        # Position the stem around the center and tilt it
        petiole.rotation_euler[2] = angle
        petiole.rotation_euler[0] = math.radians(random.uniform(30, 45)) 
        
        # Calculate world position of the stem tip for leaf attachment
        # The petiole's length is along Z in its local space
        tip_local = Vector((0.4 * math.sin(math.pi*0.5), 0.2 * math.cos(math.pi*0.5), length))
        tip_world = petiole.matrix_world @ tip_local
        
        # Leaf - placed at stem tip and drooped outward
        leaf = create_leaf(f"Leaf_{i}", size=size)
        leaf.data.materials.append(leaf_mat)
        leaf.location = tip_world
        
        # Orient leaf to face away from center and droop
        leaf.rotation_euler[2] = angle + math.pi/2
        leaf.rotation_euler[0] = math.radians(random.uniform(35, 55)) # Tilt outward
        leaf.rotation_euler[1] = math.radians(random.uniform(45, 80)) # Droop downward

if __name__ == "__main__":
    assemble_taro()
