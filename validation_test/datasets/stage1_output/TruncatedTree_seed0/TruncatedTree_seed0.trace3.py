import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    # Ensure we remove orphaned data
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
    radius = 1.2
    height = 3.0
    segments = 64
    rings = 60  # Vertical resolution for bark
    
    # Materials
    bark_mat = create_material("BarkMat", (0.45, 0.35, 0.2, 1.0)) # Sandy tan-brown
    splinter_mat = create_material("SplinterMat", (0.9, 0.85, 0.7, 1.0)) # Pale cream

    # Mesh setup
    mesh = bpy.data.meshes.new("TreeStumpMesh")
    obj = bpy.data.objects.new("TreeStump", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # 1. Create the base cylinder structure
    verts_per_ring = segments
    all_rings_verts = []
    for i in range(rings + 1):
        z = (i / rings) * height
        # Subtle taper: slightly thinner at top
        taper = 1.0 - (i / rings) * 0.2
        ring = []
        for j in range(verts_per_ring):
            angle = (j / verts_per_ring) * 2 * math.pi
            x = radius * taper * math.cos(angle)
            y = radius * taper * math.sin(angle)
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

    # Create the bottom cap
    bottom_ring = all_rings_verts[0]
    bm.faces.new(reversed(bottom_ring))

    # 2. Bark Geometry: Coarse Displacement on lower and middle half
    for i in range(rings + 1):
        z_val = (i / rings) * height
        # Influence fades as we go up to the break point
        weight = 0.0
        if z_val < height * 0.8:
            # Max bark effect at bottom, fading out near the top
            weight = 1.0 - (z_val / (height * 0.8))
            for v in all_rings_verts[i]:
                angle = math.atan2(v.co.y, v.co.x)
                # Coarse vertical ridges: low frequency sine + noise
                ridge = 0.3 * math.sin(angle * 5 + random.uniform(-0.1, 0.1))
                noise = (random.random() - 0.5) * 0.2
                normal = Vector((v.co.x, v.co.y, 0)).normalized()
                v.co += normal * (ridge + noise) * weight

    # 3. The "Break" and Splinters
    top_ring = all_rings_verts[-1]
    
    # Make the break point jagged and irregular
    for v in top_ring:
        v.co.z += random.uniform(-0.7, 0.3)
        v.co.x += random.uniform(-0.2, 0.2)
        v.co.y += random.uniform(-0.2, 0.2)

    # Create the jagged top cross-section face (triangulate manually to avoid errors)
    center_v = bm.verts.new(Vector((0, 0, height * 0.9)))
    for j in range(verts_per_ring):
        v1 = top_ring[j]
        v2 = top_ring[(j + 1) % verts_per_ring]
        bm.faces.new((center_v, v1, v2))

    # Generate splinter shards projecting upward for explosive silhouette
    num_splinters = 80
    for _ in range(num_splinters):
        # Pick a random base vertex from the top ring
        base_v = random.choice(top_ring)
        
        # Create a tapered spike
        extrude_h = random.uniform(0.4, 2.5)
        jitter_x = random.uniform(-0.3, 0.3)
        jitter_y = random.uniform(-0.3, 0.3)
        tip_v = bm.verts.new(base_v.co + Vector((jitter_x, jitter_y, extrude_h)))
        
        # To give the splinter some volume, use adjacent vertices from the top ring
        idx = top_ring.index(base_v)
        v_prev = top_ring[(idx - 1) % verts_per_ring]
        v_next = top_ring[(idx + 1) % verts_per_ring]
        
        try:
            bm.faces.new((base_v, v_next, tip_v))
            bm.faces.new((base_v, v_prev, tip_v))
            bm.faces.new((v_next, v_prev, tip_v))
        except ValueError:
            pass # Skip if face already exists

    # Finalize mesh and apply to object
    bm.to_mesh(mesh)
    bm.free()

    # Assign materials based on Z height of the polygons
    obj.data.materials.append(bark_mat)
    obj.data.materials.append(splinter_mat)
    
    for poly in obj.data.polygons:
        # Calculate average z-coordinate of polygon vertices to determine material
        sum_z = 0.0
        for v_idx in poly.vertices:
            sum_z += obj.data.vertices[v_idx].co.z
        avg_z = sum_z / len(poly.vertices)
        
        # Upper part and splinters get the cream material
        if avg_z > height * 0.6:
            poly.material_index = 1
        else:
            poly.material_index = 0

    # Center object geometry at origin for final result
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')
    obj.location = (0, 0, 0)

if __name__ == "__main__":
    generate_stump()
