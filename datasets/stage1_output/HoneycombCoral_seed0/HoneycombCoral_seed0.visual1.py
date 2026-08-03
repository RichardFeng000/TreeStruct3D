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
        bsdf.inputs['Roughness'].default_value = 0.9
    return mat

def generate_honeycomb_coral():
    # --- Parameters ---
    DOME_RADIUS = 2.0
    SEGMENTS = 160 # Higher resolution for better pitting detail
    RINGS = 80
    NUM_CELLS = 250
    CELL_DEPTH = 0.35
    CELL_SIZE = 0.25
    NUM_CLUSTERS = 12
    POLYPS_PER_CLUSTER = 6
    POLYP_RADIUS = 0.08

    # Materials
    mat_beige = create_material("CoralBeige", (0.88, 0.78, 0.62, 1.0))
    mat_green = create_material("CoralGreen", (0.35, 0.4, 0.25, 1.0))

    # 1. Base Dome
    bpy.ops.mesh.primitive_uv_sphere_add(segments=SEGMENTS, ring_count=RINGS, radius=DOME_RADIUS)
    dome_obj = bpy.context.active_object
    me = dome_obj.data
    bm = bmesh.new()
    bm.from_mesh(me)

    # Flatten bottom and close base
    verts_to_delete = [v for v in bm.verts if v.co.z < -0.1]
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')
    for v in bm.verts:
        if v.co.z < 0: v.co.z = 0
    base_verts = [v for v in bm.verts if abs(v.co.z) < 0.01]
    if base_verts:
        bmesh.ops.contextual_create(bm, geom=base_verts)

    # Generate cell seed points on the dome surface
    seeds = []
    for _ in range(NUM_CELLS):
        phi = random.uniform(0, math.pi / 2)
        theta = random.uniform(0, 2 * math.pi)
        p = Vector((
            DOME_RADIUS * math.sin(phi) * math.cos(theta),
            DOME_RADIUS * math.sin(phi) * math.sin(theta),
            DOME_RADIUS * math.cos(phi)
        ))
        seeds.append(p)

    # Honeycomb Displacement Logic
    for v in bm.verts:
        if v.co.z <= 0.1: continue # Skip the base
        
        # Find distance to nearest seed for a cellular effect
        min_dist = 1e10
        for s in seeds:
            d = (v.co - s).length
            if d < min_dist: min_dist = d
        
        # Create "scooped" pit with a ridge
        # A function that dips at the center and rises slightly before falling off
        if min_dist < CELL_SIZE * 1.5:
            # normalized distance relative to cell size
            n = min_dist / CELL_SIZE
            # Pitted shape: deep in middle, higher at walls (approximate Voronoi wall)
            factor = (1.0 - math.exp(-n*3)) * math.exp(-n*2) 
            # Simpler pit: smooth dip
            dip = -CELL_DEPTH * math.exp(-(min_dist**2) / (CELL_SIZE**2))
            v.co += v.normal * dip

    bm.to_mesh(me)
    bm.free()

    # 2. Polyp Clusters
    polyps = []
    for _ in range(NUM_CLUSTERS):
        # Cluster center
        phi_c = random.uniform(0, math.pi / 2)
        theta_c = random.uniform(0, 2 * math.pi)
        center = Vector((
            DOME_RADIUS * math.sin(phi_c) * math.cos(theta_c),
            DOME_RADIUS * math.sin(phi_c) * math.sin(theta_c),
            DOME_RADIUS * math.cos(phi_c)
        ))
        
        for _ in range(POLYPS_PER_CLUSTER):
            # Offset from center slightly
            offset = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), random.uniform(-0.1, 0.1)))
            pos = (center + offset).normalized() * DOME_RADIUS
            
            bpy.ops.mesh.primitive_uv_sphere_add(radius=POLYP_RADIUS * random.uniform(0.7, 1.3), location=pos)
            p_obj = bpy.context.active_object
            polyps.append(p_obj)

    # Join polyps to dome
    bpy.ops.object.select_all(action='DESELECT')
    dome_obj.select_set(True)
    for p in polyps: p.select_set(True)
    bpy.context.view_layer.objects.active = dome_obj
    bpy.ops.object.join()

    # 3. Material Assignment based on depth/geometry
    me = dome_obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    me.materials.append(mat_beige) # Index 0
    me.materials.append(mat_green)  # Index 1

    for face in bm.faces:
        center = face.calc_center_median()
        # Pits are deeper (closer to origin than DOME_RADIUS + small margin)
        dist_to_origin = center.length
        if dist_to_origin < DOME_RADIUS * 0.92 and center.z > 0.1:
            face.material_index = 1 # Green in pits
        else:
            face.material_index = 0 # Beige on surface

    bm.to_mesh(me)
    bm.free()

    # Final organic smoothing
    subsurf = dome_obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    clear_scene()
    generate_honeycomb_coral()
