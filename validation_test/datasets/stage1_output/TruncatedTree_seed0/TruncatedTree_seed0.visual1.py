import bpy
import bmesh
import random
import math
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
    radius = 1.3
    height = 2.8
    segments = 64
    rings = 70  # Higher resolution for more organic bark
    
    # Materials
    bark_mat = create_material("BarkMat", (0.4, 0.3, 0.18, 1.0)) # Sandy tan-brown
    splinter_mat = create_material("SplinterMat", (0.92, 0.88, 0.75, 1.0)) # Pale cream

    mesh = bpy.data.meshes.new("TreeStumpMesh")
    obj = bpy.data.objects.new("TreeStump", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # 1. Create the base cylinder structure (tapered slightly)
    all_rings_verts = []
    for i in range(rings + 1):
        z = (i / rings) * height
        taper = 1.0 - (i / rings) * 0.15
        ring = []
        for j in range(segments):
            angle = (j / segments) * 2 * math.pi
            x = radius * taper * math.cos(angle)
            y = radius * taper * math.sin(angle)
            v = bm.verts.new(Vector((x, y, z)))
            ring.append(v)
        all_rings_verts.append(ring)

    # Faces for sides
    for i in range(rings):
        for j in range(segments):
            v1 = all_rings_verts[i][j]
            v2 = all_rings_verts[i][(j + 1) % segments]
            v3 = all_rings_verts[i+1][(j + 1) % segments]
            v4 = all_rings_verts[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    # Bottom cap
    bm.faces.new(reversed(all_rings_verts[0]))

    # 2. Bark Geometry: Coarse and Bumpy (No horizontal rings)
    # We use randomized offsets weighted by height to create organic roughness
    for i in range(rings + 1):
        z_val = (i / rings) * height
        # Weight is strongest at bottom, fades toward the break point
        weight = max(0.0, 1.0 - (z_val / (height * 0.85)))
        for v in all_rings_verts[i]:
            normal = Vector((v.co.x, v.co.y, 0)).normalized()
            # Combine several noise frequencies for "coarse/large-grained" look
            noise_val = random.uniform(-0.25, 0.25) 
            # Add some larger lumps
            lump = 0.15 * math.sin(v.co.x * 2 + v.co.z * 3)
            v.co += normal * (noise_val + lump) * weight

    # 3. The "Break" and Splinters
    top_ring = all_rings_verts[-1]
    
    # Make the break point jagged
    for v in top_ring:
        v.co.z += random.uniform(-0.5, 0.4)
        v.co.x += random.uniform(-0.2, 0.2)
        v.co.y += random.uniform(-0.2, 0.2)

    # Fill the broken cross-section (center vertex)
    center_v = bm.verts.new(Vector((0, 0, height * 0.8)))
    for j in range(segments):
        bm.faces.new((center_v, top_ring[j], top_ring[(j + 1) % segments]))

    # Generate volumetric splinter shards for explosive silhouette
    num_splinters = 100
    for _ in range(num_splinters):
        # Base of the splinter: pick a point on the break surface
        base_v = random.choice(top_ring) if random.random() > 0.3 else center_v
        
        extrude_h = random.uniform(0.5, 2.2)
        # Random projection angle for "explosive" feel
        proj_dir = Vector((random.uniform(-1, 1), random.uniform(-1, 1), 1)).normalized()
        tip_v = bm.verts.new(base_v.co + proj_dir * extrude_h)
        
        # Add volume to the splinter by creating a small base pyramid/wedge
        if base_v != center_v:
            idx = top_ring.index(base_v)
            side_v = top_ring[(idx + 1) % segments]
            try:
                bm.faces.new((base_v, side_v, tip_v))
            except ValueError: pass
        else:
            # For center splinters, pick a random point on the ring to form a wedge
            edge_v = random.choice(top_ring)
            try:
                bm.faces.new((base_v, edge_v, tip_v))
            except ValueError: pass

    bm.to_mesh(mesh)
    bm.free()

    # Assign materials based on height
    obj.data.materials.append(bark_mat)
    obj.data.materials.append(splinter_mat)
    
    for poly in obj.data.polygons:
        avg_z = sum(obj.data.vertices[v].co.z for v in poly.vertices) / len(poly.vertices)
        if avg_z > height * 0.7: # Transition to cream material
            poly.material_index = 1
        else:
            poly.material_index = 0

    # Center and scale
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')
    obj.location = (0, 0, 0)

if __name__ == "__main__":
    generate_stump()
