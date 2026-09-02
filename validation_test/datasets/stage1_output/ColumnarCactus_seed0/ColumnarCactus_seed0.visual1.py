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
    ribs_count = 12 # Fewer ribs, more pronounced
    segments_z = 60
    amplitude = 0.12 # Increased for visible pleats
    
    mesh = bpy.data.meshes.new("CactusBody")
    obj = bpy.data.objects.new("Cactus", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Main Stem
    rings = []
    for z_idx in range(segments_z + 1):
        z = (z_idx / segments_z) * height
        # Slight organic wobble
        z_offset = math.sin(z * 0.5) * 0.1
        
        ring = []
        for r_idx in range(ribs_count):
            angle = (r_idx / ribs_count) * 2 * math.pi
            # Pronounced ribbing: sin wave for ridges and valleys
            mod = math.cos(angle * ribs_count) * amplitude
            r = radius + mod
            
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

    # Arm - curving from lower left (around z=2.0)
    arm_segments = 40
    arm_radius = radius * 0.7
    arm_length = 3.0
    arm_ribs = 8
    
    start_z_idx = int(segments_z * 0.35)
    # Start on the left side (-X direction)
    start_angle_idx = int(ribs_count * 0.5) 
    base_pos = rings[start_z_idx][start_angle_idx].co
    
    arm_rings = []
    for s in range(arm_segments + 1):
        t = s / arm_segments
        # Curved Path: arcs from horizontal to vertical (quarter circle)
        # t=0: move -X; t=1: move +Z
        angle_progress = t * (math.pi / 2)
        cx = base_pos.x - math.sin(angle_progress) * arm_length
        cy = base_pos.y # Keep it mostly in X-Z plane for classic look
        cz = base_pos.z + (1 - math.cos(angle_progress)) * arm_length
        
        ring = []
        for r_idx in range(arm_ribs):
            # Orient the arm's local "up" to follow its path
            # The ring is perpendicular to the tangent of the curve (cos, 0, sin)
            tangent = Vector((math.cos(angle_progress), 0, math.sin(angle_progress)))
            
            angle = (r_idx / arm_ribs) * 2 * math.pi
            mod = math.cos(angle * arm_ribs) * (amplitude * 0.7)
            r = arm_radius + mod
            
            # Construct local coordinate system for the ring
            up = Vector((0, 1, 0)) # Global Y is always perpendicular to the X-Z arc
            right = tangent.cross(up).normalized()
            
            offset = (right * math.cos(angle) + up * math.sin(angle)) * r
            ring.append(bm.verts.new(Vector((cx, cy, cz)) + offset))
        arm_rings.append(ring)
    
    for i in range(arm_segments):
        for j in range(arm_ribs):
            v1 = arm_rings[i][j]
            v2 = arm_rings[i][(j+1)%arm_ribs]
            v3 = arm_rings[i+1][(j+1)%arm_ribs]
            v4 = arm_rings[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    # Close tops
    if len(rings[-1]) > 0: bm.faces.new(rings[-1])
    if len(arm_rings[-1]) > 0: bm.faces.new(arm_rings[-1])
    
    bm.to_mesh(mesh)
    bm.free()
    
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    return obj

def create_spines(cactus_obj):
    spine_mesh = bpy.data.meshes.new("Spines")
    spine_obj = bpy.data.objects.new("Spines", spine_mesh)
    bpy.context.collection.objects.link(spine_obj)
    
    bm = bmesh.new()
    body_mesh = cactus_obj.data
    
    # We place clusters on the ridges (vertices furthest from their ring center)
    # To simplify, we iterate through vertices and keep those with high local distance
    # or simply use a density-based sampling along the "peaks" of the mesh's ribs.
    
    # Saguaro spines appear in areoles along the ridges.
    # We sample points on the surface that coincide with the rib peaks.
    for v in body_mesh.vertices:
        # The vertex coordinates were built using cos(angle * count)
        # Ridge vertices have a larger radius from their local Z axis.
        # Since it's roughly columnar, we check distance to center (x=0, y=0).
        dist_sq = v.co.x**2 + v.co.y**2
        if dist_sq > (0.5 + 0.05)**2: # Only place on peaks/ridges
            # Probability check for cluster spacing
            if random.random() > 0.6:
                p = v.co
                # Calculate outward normal roughly
                normal = Vector((p.x, p.y, 0)).normalized()
                if normal.length < 0.1: normal = Vector((0,0,1))

                spines_in_cluster = random.randint(5, 12)
                for _ in range(spines_in_cluster):
                    # Jitter direction for a "burst" effect
                    dir = Vector((
                        normal.x + random.uniform(-0.3, 0.3),
                        normal.y + random.uniform(-0.3, 0.3),
                        random.uniform(-0.4, 0.4)
                    )).normalized()
                    
                    length = random.uniform(0.08, 0.2)
                    r_s = 0.004
                    
                    # Tiny cone for the spine
                    base_ring = []
                    for i in range(3): # Triangle base is enough
                        angle = (i / 3) * 2 * math.pi
                        ortho1 = Vector((0, 1, 0)) if abs(dir.y) < 0.9 else Vector((1, 0, 0))
                        right = dir.cross(ortho1).normalized()
                        up = dir.cross(right).normalized()
                        offset = (right * math.cos(angle) + up * math.sin(angle)) * r_s
                        base_ring.append(bm.verts.new(p + offset))
                    
                    tip = bm.verts.new(p + dir * length)
                    for i in range(3):
                        bm.faces.new((base_ring[i], base_ring[(i+1)%3], tip))

    bm.to_mesh(spine_mesh)
    bm.free()
    return spine_obj

def main():
    clear_scene()
    
    green_mat = create_material("CactusGreen", (0.1, 0.3, 0.05, 1.0))
    white_mat = create_material("SpineWhite", (0.95, 0.95, 0.9, 1.0))
    
    cactus = create_cactus()
    cactus.data.materials.append(green_mat)
    
    spines = create_spines(cactus)
    spines.data.materials.append(white_mat)
    
    # Use a very light subdivision to keep the ribs distinct but smooth
    subsurf = cactus.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1

if __name__ == "__main__":
    main()
