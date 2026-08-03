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
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Base Color'].default_value = color
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_trunk():
    # Parameters
    height = 8.0
    base_radius = 0.35
    bulge_amount = 0.4
    bulge_center = height * 0.5
    bulge_width = 1.2
    segments = 32
    rings = 80

    bm = bmesh.new()

    for i in range(rings):
        z = (i / (rings - 1)) * height
        dist_from_mid = abs(z - bulge_center)
        # Bulge curve
        bulge = bulge_amount * math.exp(-(dist_from_mid**2) / (2 * bulge_width**2))
        # Horizontal ridging: sine wave on the radius
        ridge = 0.05 * math.sin(i * 1.2)
        
        current_radius = base_radius + bulge + ridge
        
        for j in range(segments):
            angle = (j / segments) * 2 * math.pi
            x = math.cos(angle) * current_radius
            y = math.sin(angle) * current_radius
            bm.verts.new((x, y, z))

    bm.verts.ensure_lookup_table()

    for i in range(rings - 1):
        for j in range(segments):
            v1 = bm.verts[i * segments + j]
            v2 = bm.verts[i * segments + (j + 1) % segments]
            v3 = bm.verts[(i + 1) * segments + (j + 1) % segments]
            v4 = bm.verts[(i + 1) * segments + j]
            bm.faces.new((v1, v2, v3, v4))

    mesh = bpy.data.meshes.new("TrunkMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Trunk", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def add_fibrous_stubs():
    # Create clustered brown fibrous stubs around the bulging mid-section
    bm = bmesh.new()
    height = 8.0
    bulge_center = height * 0.5
    bulge_width = 1.4 # Area of distribution
    num_stubs = 600

    for _ in range(num_stubs):
        # Sample Z around the bulge
        z = random.uniform(bulge_center - bulge_width, bulge_center + bulge_width)
        angle = random.uniform(0, 2 * math.pi)
        
        # Radius logic matching trunk to place them on surface
        dist_from_mid = abs(z - bulge_center)
        bulge = 0.4 * math.exp(-(dist_from_mid**2) / (2 * 1.2**2))
        r = 0.35 + bulge # base_radius + bulge
        
        base_pos = Vector((math.cos(angle)*r, math.sin(angle)*r, z))
        norm = base_pos.normalized()
        
        # Stub geometry: small tapered cylinders/cones
        s_len = random.uniform(0.1, 0.25)
        s_rad = random.uniform(0.02, 0.05)
        
        # Create a simple cone (4-sided pyramid for efficiency)
        up = Vector((0,0,1))
        tan = norm.cross(up) if abs(norm.dot(up)) < 0.9 else norm.cross(Vector((1,0,0)))
        bitan = norm.cross(tan)
        
        # Base vertices
        v1 = bm.verts.new(base_pos + tan * s_rad)
        v2 = bm.verts.new(base_pos + bitan * s_rad)
        v3 = bm.verts.new(base_pos - tan * s_rad)
        v4 = bm.verts.new(base_pos - bitan * s_rad)
        # Tip vertex
        tip = bm.verts.new(base_pos + norm * s_len)
        
        bm.faces.new((v1, v2, tip))
        bm.faces.new((v2, v3, tip)) # Adjusted index order for a basic box-cone
        # To be safe with face creation:
        bm.faces.new((v2, v4, tip)) 
        bm.faces.new((v4, v1, tip))
        # We skip the bottom face as it's inside the trunk

    mesh = bpy.data.meshes.new("StubsMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("FibrousStubs", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_fan_frond(name, rotation_angle):
    # Create a fan-shaped leaf with actual faces
    bm = bmesh.new()
    
    stem_length = 2.5
    segments = 10
    rib_verts = []
    for i in range(segments + 1):
        t = i / segments
        # Stem curves slightly
        x = t * stem_length
        y = math.sin(t * math.pi * 0.5) * 0.3
        z = -math.pow(t, 2) * 0.5 # Droop
        rib_verts.append(bm.verts.new((x, y, z)))

    # Leaflets (the fan part) radiating from the stem
    num_leaflets = 18
    for i in range(num_leaflets):
        t = (i / (num_leaflets - 1)) * stem_length
        rib_idx = int((t / stem_length) * segments)
        start_v = rib_verts[min(rib_idx, segments)]
        
        # Fan spread: leaflets move further apart towards the end of the stem
        spread_angle = (i - num_leaflets // 2) * (math.pi / 10)
        leaflet_len = 1.2 * (0.5 + t/stem_length)
        
        # Vector for leaflet direction in a fan shape (mostly X-Y plane)
        dir_vec = Vector((math.cos(spread_angle), math.sin(spread_angle), -0.2)).normalized()
        
        # Create a small quad for each leaflet
        width = 0.1
        v1 = bm.verts.new(start_v.co)
        v2 = bm.verts.new(start_v.co + Vector((0, width, 0))) # thickness/width
        v3 = bm.verts.new(start_v.co + dir_vec * leaflet_len + Vector((0, width, 0)))
        v4 = bm.verts.new(start_v.co + dir_vec * leaflet_len)
        
        bm.faces.new((v1, v2, v3, v4))

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    # Position at top of trunk (8.0)
    obj.location = (0, 0, 8.0)
    obj.rotation_euler[2] = rotation_angle
    # Tilt the whole frond outwards from center
    obj.rotation_euler[1] = math.radians(30)
    
    return obj

def main():
    clear_scene()
    
    trunk = create_trunk()
    stubs = add_fibrous_stubs()
    
    mat_trunk = create_material("TrunkMat", (0.25, 0.18, 0.1, 1.0))
    mat_stubs = create_material("StubsMat", (0.35, 0.25, 0.15, 1.0))
    mat_leaves = create_material("LeavesMat", (0.12, 0.3, 0.08, 1.0))
    
    trunk.data.materials.append(mat_trunk)
    stubs.data.materials.append(mat_stubs)
    
    num_fronds = 7
    for i in range(num_fronds):
        angle = (i / num_fronds) * 2 * math.pi
        frond = create_fan_frond(f"Frond_{i}", angle)
        frond.data.materials.append(mat_leaves)

if __name__ == "__main__":
    main()
