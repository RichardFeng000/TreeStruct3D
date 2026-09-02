import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple BSDF material with a specific color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.8
    return mat

def create_twig_coral():
    # 1. Materials
    # Reddish-brown for base, Dusty pink-beige for tips
    mat_base = create_material("CoralBase", (0.45, 0.25, 0.18, 1.0))
    mat_tip = create_material("CoralTip", (0.85, 0.65, 0.55, 1.0))

    # 2. Mesh Setup
    bm = bmesh.new()
    
    # Create a dense central base - lumpy organic mass
    base_radius = 0.6
    segments = 12
    rings = 6
    for i in range(rings):
        phi = math.pi * i / (rings - 1)
        r = base_radius * math.sin(phi)
        z = (i / rings - 0.5) * 0.4 # Flattened
        for j in range(segments):
            theta = 2 * math.pi * j / segments
            # Add some organic noise to the base
            noise = random.uniform(0.8, 1.2)
            x = r * math.cos(theta) * noise
            y = r * math.sin(theta) * noise
            bm.verts.new((x, y, z))
    
    bm.verts.ensure_lookup_table()
    for i in range(rings - 1):
        for j in range(segments):
            v1 = bm.verts[i * segments + j]
            v2 = bm.verts[i * segments + (j + 1) % segments]
            v3 = bm.verts[(i + 1) * segments + j]
            v4 = bm.verts[(i + 1) * segments + (j + 1) % segments]
            try:
                bm.faces.new((v1, v2, v4))
                bm.faces.new((v1, v4, v3))
            except ValueError:
                pass

    # Branching Logic
    def add_branch(start_pos, start_dir, length, radius, depth):
        if depth <= 0:
            return
        
        current_pos = Vector(start_pos)
        current_dir = Vector(start_dir).normalized()
        
        segments_per_branch = 3
        seg_len = length / segments_per_branch
        res = 6 # Low res, modifiers will smooth it
        
        prev_ring = None
        
        for s in range(segments_per_branch):
            # Randomize direction slightly for organic twist
            jitter = Vector((random.uniform(-0.4, 0.4), 
                            random.uniform(-0.4, 0.4), 
                            random.uniform(-0.4, 0.4)))
            current_dir = (current_dir + jitter * 0.5).normalized()
            
            # Create ring of vertices
            ring_verts = []
            basis_ref = Vector((0, 1, 0)) if abs(current_dir.dot(Vector((0, 1, 0)))) < 0.9 else Vector((1, 0, 0))
            u = current_dir.cross(basis_ref).normalized()
            v = current_dir.cross(u).normalized()
            
            current_radius = radius * (1.0 - (s / segments_per_branch) * 0.3)
            
            for i in range(res):
                angle = (2 * math.pi * i) / res
                offset = (u * math.cos(angle) + v * math.sin(angle)) * current_radius
                ring_verts.append(bm.verts.new(current_pos + offset))
            
            # Connect to previous ring
            if prev_ring:
                for i in range(res):
                    try:
                        bm.faces.new((prev_ring[i], prev_ring[(i+1)%res], ring_verts[(i+1)%res], ring_verts[i]))
                    except ValueError:
                        pass
            
            prev_ring = ring_verts
            current_pos += current_dir * seg_len

        # Recursive splitting
        num_splits = random.randint(1, 3)
        for _ in range(num_splits):
            split_dir = (current_dir + Vector((random.uniform(-0.8, 0.8), 
                                              random.uniform(-0.8, 0.8), 
                                              random.uniform(-0.8, 0.8)))).normalized()
            add_branch(current_pos, split_dir, length * 0.65, radius * 0.6, depth - 1)

    # Seed branches from the base mass
    num_main_stems = 15
    for _ in range(num_main_stems):
        # Pick a point on the upper surface of the base
        start_pos = Vector((random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4), random.uniform(-0.1, 0.1)))
        # Radiate outward and slightly upward (low growing colony)
        start_dir = Vector((start_pos.x * 2, start_pos.y * 2, random.uniform(0.1, 0.5))).normalized()
        add_branch(start_pos, start_dir, 1.4, 0.1, 3)

    # Finalize BMesh to Mesh object
    mesh = bpy.data.meshes.new("CoralMesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("TwigCoral", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Materials assignment based on distance from center (Gradient effect)
    obj.data.materials.append(mat_base)
    obj.data.materials.append(mat_tip)
    
    for poly in mesh.polygons:
        # Calculate centroid distance from origin
        poly_center = sum((mesh.vertices[v].co for v in poly.vertices), Vector()) / len(poly.vertices)
        dist = poly_center.length
        if dist < 1.0:
            poly.material_index = 0 # Base reddish-brown
        else:
            # Interpolate or just use tip color for outer branches
            poly.material_index = 1 # Tip pink-beige

    # --- Modifiers for Detail ---
    
    # 1. Subdivision Surface to smooth the low-res cylinder segments and base
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3
    
    # 2. Displace Modifier for "polyp bumps" and encrusted texture
    disp_mod = obj.modifiers.new(name="Encrust", type='DISPLACE')
    tex = bpy.data.textures.new("CoralNoise", type='STC_NOISE')
    tex.noise_scale = 0.05
    disp_mod.texture = tex
    disp_mod.strength = 0.04

    # Ensure the object is at center and oriented correctly
    obj.location = (0, 0, 0)
    
    return obj

if __name__ == "__main__":
    clear_scene()
    create_twig_coral()
