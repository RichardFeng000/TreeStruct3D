import bpy
import bmesh
import math
import random
import numpy as np
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
        bsdf.inputs['Roughness'].default_value = 0.8
        bsdf.inputs['Specular IOR Level'].default_value = 0.2
    return mat

def generate_honeycomb_coral():
    # Parameters
    DOME_RADIUS = 2.0
    SEGMENTS = 64
    RINGS = 32
    NUM_CELLS = 150
    CELL_SIZE = 0.4
    PIT_DEPTH = 0.3
    RIDGE_HEIGHT = 0.15

    # Materials
    mat_beige = create_material("CoralBeige", (0.8, 0.7, 0.6, 1.0))
    mat_green = create_material("CoralGreen", (0.3, 0.4, 0.2, 1.0))

    # Create base dome
    bpy.ops.mesh.primitive_uv_sphere_add(segments=SEGMENTS, ring_count=RINGS, radius=DOME_RADIUS)
    dome_obj = bpy.context.active_object
    me = dome_obj.data
    bm = bmesh.new()
    bm.from_mesh(me)

    # Flatten bottom and remove lower hemisphere
    verts_to_delete = [v for v in bm.verts if v.co.z < -0.1]
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')
    for v in bm.verts:
        if v.co.z < 0:
            v.co.z = 0

    # Ensure base is filled
    base_verts = [v for v in bm.verts if abs(v.co.z) < 0.01]
    if base_verts:
        bmesh.ops.contextual_create(bm, geom=base_verts)

    # Numpy optimization for Voronoi displacement
    # Extract vertices and normals as arrays
    verts = np.array([v.co[:] for v in bm.verts])
    norms = np.array([v.normal[:] for v in bm.verts])
    
    # Generate seed points on the dome surface
    seeds = []
    for _ in range(NUM_CELLS):
        phi = random.uniform(0, math.pi / 2)
        theta = random.uniform(0, 2 * math.pi)
        p = np.array([
            DOME_RADIUS * math.sin(phi) * math.cos(theta),
            DOME_RADIUS * math.sin(phi) * math.sin(theta),
            DOME_RADIUS * math.cos(phi)
        ])
        seeds.append(p)
    seeds = np.array(seeds)

    # Vectorized distance calculation: find min dist to any seed for each vertex
    # Dist^2 = |V|^2 + |S|^2 - 2VS^T
    v_sq = np.sum(verts**2, axis=1)[:, np.newaxis]
    s_sq = np.sum(seeds**2, axis=1)
    dist_sq = v_sq + s_sq - 2 * np.dot(verts, seeds.T)
    min_dist_sq = np.min(dist_sq, axis=1)
    min_dist = np.sqrt(np.maximum(min_dist_sq, 0))

    # Calculate displacement values based on distances
    norm_dist = min_dist / CELL_SIZE
    # Use a combination of cosine and exponential for the pit/ridge look
    disp_vals = -PIT_DEPTH * np.cos(norm_dist * np.pi * 0.5) + RIDGE_HEIGHT * (1 - np.exp(-norm_dist * 3))
    
    # Apply displacements only to vertices above base level
    for i, v in enumerate(bm.verts):
        if v.co.z > 0.1:
            v.co += v.normal * disp_vals[i]

    # Assign materials based on depth/location
    me.materials.append(mat_beige) # Index 0
    me.materials.append(mat_green)  # Index 1
    for face in bm.faces:
        center = face.calc_center_median()
        if center.z < 0.2:
            face.material_index = 0
        elif center.length < DOME_RADIUS * 0.95:
            face.material_index = 1
        else:
            face.material_index = 0

    bm.to_mesh(me)
    bm.free()

    # Integrated Polyps (Bumpy clusters)
    num_clusters = 12
    polyps_objs = []
    for _ in range(num_clusters):
        phi_c = random.uniform(0, math.pi / 2)
        theta_c = random.uniform(0, 2 * math.pi)
        center = Vector((
            DOME_RADIUS * math.sin(phi_c) * math.cos(theta_c),
            DOME_RADIUS * math.sin(phi_c) * math.sin(theta_c),
            DOME_RADIUS * math.cos(phi_c)
        ))
        
        for _ in range(random.randint(3, 6)):
            offset = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), random.uniform(-0.1, 0.1)))
            pos = (center + offset).normalized() * DOME_RADIUS
            
            bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(0.05, 0.13), location=pos)
            p_obj = bpy.context.active_object
            p_obj.data.materials.append(mat_beige)
            polyps_objs.append(p_obj)

    # Join all parts
    bpy.ops.object.select_all(action='DESELECT')
    dome_obj.select_set(True)
    for p in polyps_objs: 
        p.select_set(True)
    bpy.context.view_layer.objects.active = dome_obj
    bpy.ops.object.join()

    # Final polish
    subsurf = dome_obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    clear_scene()
    generate_honeycomb_coral()
