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
    """Creates a taro-style arrowhead leaf using BMesh."""
    bm = bmesh.new()
    
    # Define key points for an arrow/heart shape (Taro style)
    # Normalized coordinates: Tip at top, lobes at bottom
    points = [
        Vector((0, 2.0)),      # Tip
        Vector((0.8, 1.5)),    # Upper shoulder
        Vector((1.2, 0.5)),    # Middle width
        Vector((1.0, -0.8)),   # Lower lobe outer
        Vector((0, -0.4)),     # Stem indentation (the 'heart' notch)
        Vector((-1.0, -0.8)),  # Lower lobe outer
        Vector((-1.2, 0.5)),   # Middle width
        Vector((-0.8, 1.5)),   # Upper shoulder
    ]
    
    # Interpolate points to create a smooth outline
    res = 64
    outline_verts = []
    for i in range(res):
        t = (i / res) * len(points)
        idx = int(t) % len(points)
        next_idx = (idx + 1) % len(points)
        alpha = t - int(t)
        p = points[idx].lerp(points[next_idx], alpha)
        # Scale by size and flatten slightly
        outline_verts.append(bm.verts.new(Vector((p.x * 0.6 * size, p.y * 0.7 * size, 0))))

    # Create the main face
    face = bm.faces.new(outline_verts)
    
    # Subdivide for bending/deformation
    bmesh.ops.subdivide_edges(bm, edges=face.edges, cuts=2) # Not quite enough, let's do a grid-like fill
    
    # To get better deformation, we replace the single face with a grid of triangles from center
    center_v = bm.verts.new(Vector((0, 0, -0.3 * size)) ) # Offset slightly for base
    bm.faces.ensure_lookup_table()
    edges = list(face.edges)
    bm.faces.remove(face)
    for edge in edges:
        bm.faces.new((edge.verts[0], edge.verts[1], center_v))

    # Add a slight convex curvature to the leaf (the "droop" and organic feel)
    for v in bm.verts:
        dist = v.co.length
        # Parabolic bend: higher in middle, lower at edges
        v.co.z += (1.0 - (dist / (2.0 * size))**2) * 0.3 * size
        if v == center_v:
            v.co.z = 0

    # Give the leaf very slight thickness
    bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    for v in bm.verts:
        # Move extruded vertices slightly
        if v not in outline_verts and v != center_v:
            # This is a simplified way to shift the extruded layer
            pass

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    # Smooth shading
    for poly in obj.data.polygons:
        poly.use_smooth = True
        
    return obj

def create_petiole(name, length=3.0, radius=0.06):
    """Creates a long, slightly curved upright stem."""
    bm = bmesh.new()
    
    segments = 15
    ring_res = 8
    rings = []
    
    for i in range(segments + 1):
        t = i / segments
        z = t * length
        # Organic slight curve
        cx = math.sin(t * math.pi) * 0.2
        cy = math.cos(t * math.pi) * 0.1
        
        ring = []
        for j in range(ring_res):
            angle = (j / ring_res) * 2 * math.pi
            vx = cx + math.cos(angle) * radius * (1.0 - t*0.5) # Tapered stem
            vy = cy + math.sin(angle) * radius * (1.0 - t*0.5)
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
    
    # Light green colors as requested
    leaf_mat = create_material("LeafMat", (0.5, 0.8, 0.3, 1.0)) # Light Green
    stem_mat = create_material("StemMat", (0.4, 0.6, 0.2, 1.0)) # Muted Green
    
    # Base corm
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(0, 0, 0))
    corm = bpy.context.active_object
    corm.name = "TaroBase"
    corm.scale = (1, 1, 0.5)
    corm.data.materials.append(stem_mat)

    num_leaves = 6
    for i in range(num_leaves):
        angle = (i / num_leaves) * 2 * math.pi + random.uniform(-0.1, 0.1)
        length = random.uniform(3.0, 4.5)
        size = random.uniform(1.5, 2.2)
        
        # Petiole
        petiole = create_petiole(f"Petiole_{i}", length=length)
        petiole.data.materials.append(stem_mat)
        
        # Rotate petiole to spread around base
        rot_z = angle
        petiole.rotation_euler[2] = rot_z
        # Tilt outward for an "upright but spreading" look
        petiole.rotation_euler[0] = random.uniform(0.1, 0.3)
        
        # Calculate top position in world space
        top_local = Vector((math.sin(math.pi)*0.2, math.cos(math.pi)*0.1, length))
        top_world = petiole.matrix_world @ top_local
        
        # Leaf
        leaf = create_leaf(f"Leaf_{i}", size=size)
        leaf.data.materials.append(leaf_mat)
        leaf.location = top_world
        
        # Align leaf to the end of the petiole and droop it outward
        leaf.rotation_euler[2] = rot_z + math.pi/2
        leaf.rotation_euler[0] = math.radians(random.uniform(15, 35)) # Tilt away from center
        leaf.rotation_euler[1] = math.radians(random.uniform(30, 60)) # Droop downward

if __name__ == "__main__":
    assemble_taro()
