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

def create_cactus():
    # Parameters
    height = 6.0
    radius = 0.5
    ribs_count = 16
    segments_z = 40
    amplitude = 0.07
    
    mesh = bpy.data.meshes.new("CactusBody")
    obj = bpy.data.objects.new("Cactus", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Main Stem
    rings = []
    for z_idx in range(segments_z + 1):
        z = (z_idx / segments_z) * height
        # Organic vertical variation
        z_offset = math.sin(z * 0.6) * 0.15
        
        ring = []
        for r_idx in range(ribs_count):
            angle = (r_idx / ribs_count) * 2 * math.pi
            # Ribbing: sin wave for ridges and valleys
            mod = math.sin(angle * ribs_count) * amplitude
            # Add noise
            noise = random.uniform(-0.02, 0.02)
            r = radius + mod + noise
            
            x = math.cos(angle) * r
            y = math.sin(angle) * r
            ring.append(bm.verts.new(Vector((x, y, z + z_offset))))
        rings.append(ring)

    # Face the main stem
    for i in range(segments_z):
        for j in range(ribs_count):
            v1 = rings[i][j]
            v2 = rings[i][(j+1)%ribs_count]
            v3 = rings[i+1][(j+1)%ribs_count]
            v4 = rings[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    # Arm - curving from lower left
    arm_segments = 20
    arm_radius = radius * 0.7
    arm_height = 3.5
    arm_ribs = 12
    
    # Starting position on the body (around z=2.0, angle ~ 180deg)
    start_z_idx = int(segments_z * 0.33)
    start_angle_idx = int(ribs_count * 0.5) # -X direction
    base_pos = rings[start_z_idx][start_angle_idx].co
    
    arm_rings = []
    for s in range(arm_segments + 1):
        t = s / arm_segments
        # Path: start at base, move left (-X), then curve up (+Z)
        cx = base_pos.x - (t * 1.2)
        cy = base_pos.y + math.sin(t * math.pi * 0.5) * 0.4
        cz = base_pos.z + (t * arm_height * 0.8)
        
        ring = []
        for r_idx in range(arm_ribs):
            angle = (r_idx / arm_ribs) * 2 * math.pi
            mod = math.sin(angle * arm_ribs) * (amplitude * 0.7)
            r = arm_radius + mod
            ring.append(bm.verts.new(Vector((
                cx + math.cos(angle)*r,
                cy + math.sin(angle)*r,
                cz
            ))))
        arm_rings.append(ring)
    
    for i in range(arm_segments):
        for j in range(arm_ribs):
            v1 = arm_rings[i][j]
            v2 = arm_rings[i][(j+1)%arm_ribs]
            v3 = arm_rings[i+1][(j+1)%arm_ribs]
            v4 = arm_rings[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    # Close tops
    bm.faces.new(rings[-1])
    bm.faces.new(arm_rings[-1])
    
    bm.to_mesh(mesh)
    bm.free()
    
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    return obj

def create_spines(cactus_obj):
    # We generate spines as small cylinders/cones clustered on the ridges
    spine_mesh = bpy.data.meshes.new("Spines")
    spine_obj = bpy.data.objects.new("Spines", spine_mesh)
    bpy.context.collection.objects.link(spine_obj)
    
    bm = bmesh.new()
    body_mesh = cactus_obj.data
    
    # Saguaro spines are on ridges. Ridges are vertices where the radius is maxed.
    # Instead of complex logic, we sample points and check their local curvature or just place them
    # along the rib lines (the high points of the sine wave).
    
    # We'll iterate through all vertices and pick those that likely belong to ridges
    ridge_verts = []
    for v in body_mesh.vertices:
        # Ridges are further from the center
        if v.co.length > 0.5: # Approximate filter for ridges
            ridge_verts.append(v.co)

    # Sample a subset of vertices to act as 'areoles' (spine clusters)
    num_clusters = min(len(ridge_verts), 600)
    sampled_points = random.sample(ridge_verts, num_clusters)
    
    for p in sampled_points:
        # Normal at the point (approximate by distance from origin for columnar shape)
        normal = (p - Vector((0,0,0))).normalized() 
        # Correct normal if it's too vertical since it's a column
        if abs(normal.z) > 0.5:
            normal.z *= 0.2
            normal = normal.normalized()

        # Number of spines per areole
        spines_in_cluster = random.randint(4, 10)
        for _ in range(spines_in_cluster):
            # Perturb the direction slightly
            dir = Vector((
                normal.x + random.uniform(-0.4, 0.4),
                normal.y + random.uniform(-0.4, 0.4),
                normal.z + random.uniform(-0.4, 0.4)
            )).normalized()
            
            length = random.uniform(0.06, 0.18)
            radius_s = 0.003
            
            # Create a very thin cylinder for the spine
            # Vertices for a tiny circle at base and tip
            base_ring = []
            for i in range(4): # 4 sides is enough for such small objects
                angle = (i / 4) * 2 * math.pi
                # Orthogonal vector to direction
                ortho1 = Vector((0, 1, 0)) if abs(dir.y) < 0.9 else Vector((1, 0, 0))
                right = dir.cross(ortho1).normalized()
                up = dir.cross(right).normalized()
                offset = (right * math.cos(angle) + up * math.sin(angle)) * radius_s
                base_ring.append(bm.verts.new(p + offset))
            
            tip_ring = []
            for i in range(4):
                angle = (i / 4) * 2 * math.pi
                ortho1 = Vector((0, 1, 0)) if abs(dir.y) < 0.9 else Vector((1, 0, 0))
                right = dir.cross(ortho1).normalized()
                up = dir.cross(right).normalized()
                offset = (right * math.cos(angle) + up * math.sin(angle)) * (radius_s * 0.3)
                tip_ring.append(bm.verts.new(p + dir * length + offset))
            
            # Faces for the spine cylinder
            for i in range(4):
                bm.faces.new((base_ring[i], base_ring[(i+1)%4], tip_ring[(i+1)%4], tip_ring[i]))
            bm.faces.new(tip_ring)

    bm.to_mesh(spine_mesh)
    bm.free()
    return spine_obj

def main():
    clear_scene()
    
    green_mat = create_material("CactusGreen", (0.15, 0.35, 0.1, 1.0))
    white_mat = create_material("SpineWhite", (0.9, 0.9, 0.8, 1.0))
    
    cactus = create_cactus()
    cactus.data.materials.append(green_mat)
    
    spines = create_spines(cactus)
    spines.data.materials.append(white_mat)
    
    # Final polish on body
    subsurf = cactus.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1

if __name__ == "__main__":
    main()
