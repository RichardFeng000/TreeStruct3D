import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple material with the given color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def generate_stump():
    clear_scene()

    # Parameters
    radius = 1.2
    height = 3.0
    segments = 64
    rings = 32  # Vertical resolution for the bark displacement
    
    # Materials
    bark_mat = create_material("BarkMat", (0.4, 0.3, 0.2, 1.0)) # Sandy tan-brown
    splinter_mat = create_material("SplinterMat", (0.9, 0.85, 0.75, 1.0)) # Pale cream

    # Create a mesh manually with vertical rings for displacement
    mesh = bpy.data.meshes.new("TreeStumpMesh")
    obj = bpy.data.objects.new("TreeStump", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # Generate vertices in rings
    verts_per_ring = segments
    all_rings_verts = []
    for i in range(rings + 1):
        z = (i / rings) * height
        ring = []
        for j in range(verts_per_ring):
            angle = (j / verts_per_ring) * 2 * math.pi
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            v = bm.verts.new(Vector((x, y, z)))
            ring.append(v)
        all_rings_verts.append(ring)

    # Create faces for the cylinder sides
    for i in range(rings):
        for j in range(verts_per_ring):
            v1 = all_rings_verts[i][j]
            v2 = all_rings_verts[i][(j + 1) % verts_per_ring]
            v3 = all_rings_verts[i+1][(j + 1) % verts_per_ring]
            v4 = all_rings_verts[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    # Create the top cap (to be splintered later)
    top_ring = all_rings_verts[-1]
    top_face = bm.faces.new(top_ring)
    
    # Create the bottom cap
    bottom_ring = all_rings_verts[0]
    bm.faces.new(reversed(bottom_ring))

    # 1. Bark Geometry: Displacement on the lower half
    for i in range(rings + 1):
        z_val = (i / rings) * height
        if z_val < height * 0.7: # Apply bark to most of the bottom and mid section
            weight = 1.0 - (z_val / (height * 0.8))
            for v in all_rings_verts[i]:
                # Coarse bumpy displacement
                angle = math.atan2(v.co.y, v.co.x)
                # Create vertical "ridges"
                groove = 0.2 * math.sin(angle * 7) * random.uniform(0.5, 1.5)
                noise = random.uniform(-0.15, 0.15)
                
                normal = (v.co - Vector((0, 0, v.co.z))).normalized()
                displacement = (groove + noise) * weight
                v.co += normal * displacement

    # 2. Splintering: Transform the top section
    # We'll pick vertices from the top ring and extrude them into shards
    num_splinters = 45
    for _ in range(num_splinters):
        # Pick a seed vertex on the top ring
        seed_v = random.choice(top_ring)
        
        # Create a small cluster around the seed
        cluster = [seed_v]
        # To find neighbors safely without .other()
        for edge in seed_v.link_edges:
            if random.random() > 0.4:
                # Find vertex in edge not equal to seed_v
                for v in edge.verts:
                    if v != seed_v:
                        cluster.append(v)
                        break
        
        # Extrude the cluster upward into a sharp shard
        extrude_h = random.uniform(0.5, 2.5)
        center = Vector((0, 0, 0))
        for v in cluster:
            center += v.co
        center /= len(cluster)
        
        # Jitter the tip
        tip_pos = center + Vector((
            random.uniform(-0.3, 0.3),
            random.uniform(-0.3, 0.3),
            extrude_h
        ))
        
        tip_v = bm.verts.new(tip_pos)
        
        # Create faces connecting cluster to tip (triangulating the shard)
        for i in range(len(cluster)):
            v1 = cluster[i]
            v2 = cluster[(i + 1) % len(cluster)]
            bm.faces.new((v1, v2, tip_v))

    # Make the "break" irregular by jittering the top ring's Z and XY
    for v in top_ring:
        v.co.z += random.uniform(-0.6, 0.3)
        v.co.x += random.uniform(-0.2, 0.2)
        v.co.y += random.uniform(-0.2, 0.2)

    # Finalize mesh
    bm.to_mesh(mesh)
    bm.free()

    # Assign materials based on height
    obj.data.materials.append(bark_mat)
    obj.data.materials.append(splinter_mat)
    
    for poly in obj.data.polygons:
        center_z = sum([v.co.z for v in poly.vertices]) / len(poly.vertices)
        # Top half (approximate) gets the pale cream splinter material
        if center_z > height * 0.6:
            poly.material_index = 1
        else:
            poly.material_index = 0

    # Center object geometry at origin
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')
    obj.location = (0, 0, 0)

if __name__ == "__main__":
    generate_stump()
