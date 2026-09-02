import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Clear the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_trunk():
    """Creates a tall, curved, ringed palm trunk."""
    bm = bmesh.new()
    
    height = 8.0
    segments = 50
    rings_count = 24
    base_radius = 0.35
    top_radius = 0.2
    curve_amplitude = 0.7
    
    prev_ring = []
    for i in range(segments + 1):
        z = (i / segments) * height
        # Calculate curvature offset for a natural bend
        offset_x = math.sin(z * 0.4) * curve_amplitude
        offset_y = math.cos(z * 0.3) * (curve_amplitude * 0.5)
        center = Vector((offset_x, offset_y, z))
        
        # Ringed texture effect: modulates radius periodically
        ring_mod = 1.0 + 0.06 * math.sin(i * 2.0) 
        radius = (base_radius + (top_radius - base_radius) * (i / segments)) * ring_mod
        
        current_ring = []
        for j in range(rings_count):
            angle = (j / rings_count) * 2 * math.pi
            vx = center.x + math.cos(angle) * radius
            vy = center.y + math.sin(angle) * radius
            vz = center.z
            current_ring.append(bm.verts.new((vx, vy, vz)))
        
        if prev_ring:
            for j in range(rings_count):
                v1 = prev_ring[j]
                v2 = prev_ring[(j + 1) % rings_count]
                v3 = current_ring[(j + 1) % rings_count]
                v4 = current_ring[j]
                bm.faces.new((v1, v2, v3, v4))
        
        prev_ring = current_ring

    # Cap the top
    bm.faces.new(prev_ring)
    
    mesh = bpy.data.meshes.new("PalmTrunk")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("PalmTrunk", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_crown_base(center):
    """Creates a small, rough bulb at the top of the trunk."""
    bm = bmesh.new()
    # A slightly irregular sphere/ellipsoid
    segments = 12
    rings = 8
    radius = 0.4
    
    for i in range(rings + 1):
        phi = (i / rings) * math.pi
        ring_verts = []
        for j in range(segments):
            theta = (j / segments) * 2 * math.pi
            # Add some noise for 'fibrous/rough' look
            noise = random.uniform(0.8, 1.2)
            x = radius * math.sin(phi) * math.cos(theta) * noise
            y = radius * math.sin(phi) * math.sin(theta) * noise
            z = radius * math.cos(phi) * noise
            ring_verts.append(bm.verts.new((center.x + x, center.y + y, center.z + z)))
        
        if i > 0:
            prev_ring = list(bm.verts)[(i-1)*segments : i*segments] # approximation
            # This is sloppy; let's use a more robust way to track rings
    
    # Redoing crown base simply with a bmesh sphere and then adding noise
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=0.35)
    for v in bm.verts:
        v.co += Vector((random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05)))
        # Shift to crown center
        v.co += center

    mesh = bpy.data.meshes.new("CrownBase")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("CrownBase", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_frond(origin, direction):
    """Creates a feathery pinnate frond with actual geometry."""
    bm = bmesh.new()
    
    stem_segments = 12
    stem_length = 3.0
    droop = 1.2
    
    # 1. Create the Spine (Rachis) as a thin tube
    spine_verts = []
    for i in range(stem_segments + 1):
        t = i / stem_segments
        pos = origin + direction * (t * stem_length)
        pos.z -= (t**2 * droop) # Curve downwards
        spine_verts.append(bm.verts.new(pos))

    # Create volume for the spine
    for i in range(stem_segments):
        v1 = spine_verts[i]
        v2 = spine_verts[i+1]
        # Small ring around spine to give it thickness
        ring_r = 0.03
        dir_vec = (v2.co - v1.co).normalized()
        ortho = Vector((0,0,1)).cross(dir_vec).normalized() if abs(dir_vec.z) < 0.9 else Vector((1,0,0)).cross(dir_vec).normalized()
        side = dir_vec.cross(ortho).normalized()
        
        p1 = v1.co + ortho * ring_r
        p2 = v1.co - ortho * ring_r
        p3 = v2.co - ortho * ring_r
        p4 = v2.co + ortho * ring_r
        
        # Just a simple quad for the stem thickness
        bm.faces.new((bm.verts.new(p1), bm.verts.new(p2), bm.verts.new(p3), bm.verts.new(p4)))

    # 2. Create Leaflets (Pinnae)
    leaflet_count = 30
    leaflet_len = 0.8
    width = 0.06
    
    for i in range(1, leaflet_count):
        t = i / leaflet_count
        # Find closest spine vertex
        spine_idx = int(t * stem_segments)
        if spine_idx >= stem_segments: spine_idx = stem_segments - 1
        start_p = spine_verts[spine_idx].co
        
        # Direction of the leaflet: mostly down, slightly outwards
        leaf_dir = Vector((0,0,-1)) + (direction * 0.4)
        leaf_dir.normalize()
        # Vary leaf dir along the stem for "V" shape
        leaf_dir.z -= (t * 0.5)
        leaf_dir.normalize()

        # Create a thin rectangle for each leaflet
        v1 = bm.verts.new(start_p)
        v2 = bm.verts.new(start_p + leaf_dir * leaflet_len)
        # Width offset
        side_vec = direction.cross(leaf_dir).normalized() * width
        v3 = bm.verts.new(v2.co + side_vec)
        v4 = bm.verts.new(v1.co + side_vec)
        bm.faces.new((v1, v2, v3, v4))

    mesh = bpy.data.meshes.new("Frond")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Frond", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def assemble_palm():
    clear_scene()
    
    trunk = create_trunk()
    
    # Top center for crown placement
    top_z = 8.0
    top_x = math.sin(top_z * 0.4) * 0.7
    top_y = math.cos(top_z * 0.3) * (0.7 * 0.5)
    crown_center = Vector((top_x, top_y, top_z))
    
    create_crown_base(crown_center)
    
    num_fronds = 14
    for i in range(num_fronds):
        angle = (i / num_fronds) * 2 * math.pi
        angle += random.uniform(-0.1, 0.1)
        direction = Vector((math.cos(angle), math.sin(angle), 0))
        # Slight upward start angle
        direction.z = random.uniform(0.2, 0.5)
        direction.normalize()
        
        frond_obj = create_frond(crown_center, direction)
        s = random.uniform(0.8, 1.2)
        frond_obj.scale = (s, s, s)

if __name__ == "__main__":
    assemble_palm()
