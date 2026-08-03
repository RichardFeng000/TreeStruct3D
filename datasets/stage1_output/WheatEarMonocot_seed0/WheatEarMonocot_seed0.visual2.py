import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

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

def create_wheat_ear():
    clear_scene()

    # --- Parameters ---
    num_grains = 120 # Increased significantly for density
    rachis_height = 8.0
    curve_amplitude = 0.6
    radius_base = 0.12
    
    color_gold = (0.75, 0.65, 0.3, 1.0) # Muted gold
    color_green = (0.35, 0.45, 0.2, 1.0) # Muted green
    mat_grain = create_material("GrainMat", color_gold)
    mat_stem = create_material("StemMat", color_green)

    # --- Rachis Path Calculation ---
    segments = 64
    rachis_points = []
    for i in range(segments + 1):
        t = i / segments
        z = t * rachis_height
        x = math.sin(t * math.pi * 0.8) * curve_amplitude * (t**1.5)
        y = math.cos(t * math.pi * 0.5) * 0.2 * t
        rachis_points.append(Vector((x, y, z)))

    # --- Create Rachis Mesh ---
    rachis_bm = bmesh.new()
    for i in range(segments):
        p1 = rachis_points[i]
        p2 = rachis_points[i+1]
        v_dir = (p2 - p1).normalized()
        
        up_ref = Vector((0, 0, 1)) if abs(v_dir.dot(Vector((0, 0, 1)))) < 0.9 else Vector((0, 1, 0))
        right = v_dir.cross(up_ref).normalized()
        up = v_dir.cross(right).normalized()

        ring_res = 8
        r1, r2 = [], []
        for j in range(ring_res):
            angle = (2 * math.pi * j) / ring_res
            v1 = p1 + (right * math.cos(angle) + up * math.sin(angle)) * radius_base
            v2 = p2 + (right * math.cos(angle) + up * math.sin(angle)) * radius_base
            r1.append(rachis_bm.verts.new(v1))
            r2.append(rachis_bm.verts.new(v2))
        for j in range(ring_res):
            rachis_bm.faces.new((r1[j], r1[(j+1)%ring_res], r2[(j+1)%ring_res], r2[j]))

    mesh_rachis = bpy.data.meshes.new("RachisMesh")
    rachis_bm.to_mesh(mesh_rachis)
    obj_rachis = bpy.data.objects.new("Rachis", mesh_rachis)
    bpy.context.collection.objects.link(obj_rachis)
    obj_rachis.data.materials.append(mat_stem)
    rachis_bm.free()

    # --- Create Spikelets Mesh ---
    spikelet_bm = bmesh.new()
    
    # Golden angle for dense phyllotaxis packing
    golden_angle = math.pi * (3 - math.sqrt(5)) 
    
    for i in range(num_grains):
        t = i / num_grains
        # Tapered distribution: more concentrated at bottom/middle, thinner at top
        z_pos = t * rachis_height * 0.9
        idx = int((t * 0.9) * segments)
        p = rachis_points[min(idx, segments)]
        v_dir = (rachis_points[min(idx+1, segments)] - p).normalized()
        
        # Tapering size of grains as we go up
        scale = 1.0 - (t * 0.4)
        
        up_ref = Vector((0, 0, 1)) if abs(v_dir.dot(Vector((0, 0, 1)))) < 0.9 else Vector((0, 1, 0))
        right = v_dir.cross(up_ref).normalized()
        up = v_dir.cross(right).normalized()

        # Phyllotaxis spiral placement
        angle = i * golden_angle
        dist = radius_base * (0.8 + 0.2 * math.sin(t*math.pi))
        pos = p + (right * math.cos(angle) + up * math.sin(angle)) * dist
        
        # Orientation: tilt slightly outwards and upwards along the spike
        grain_up = (v_dir * 0.8 + (pos - p).normalized() * 0.4).normalized()
        z_axis = grain_up
        x_axis = Vector((1, 0, 0)) if abs(z_axis.dot(Vector((1, 0, 0)))) < 0.9 else Vector((0, 1, 0))
        x_axis = z_axis.cross(x_axis).normalized()
        y_axis = z_axis.cross(x_axis).normalized()
        mat_local = Matrix((x_axis, y_axis, z_axis)).to_4x4() @ Matrix.Translation(pos)

        # 1. Grain Core (The seed)
        grain_temp = bmesh.new()
        bmesh.ops.create_uvsphere(grain_temp, u_segments=8, v_segments=6, radius=0.15 * scale)
        for v in grain_temp.verts:
            v.co.z *= 2.2 # Elongated shape
            v.co.x *= 0.7
            v.co.y *= 0.7
            if v.co.z < 0: # Taper bottom
                v.co.x *= (1.0 + v.co.z * 2.0)
                v.co.y *= (1.0 + v.co.z * 2.0)
            v.co = mat_local @ v.co
        
        vert_map = {}
        for v in grain_temp.verts: vert_map[v] = spikelet_bm.verts.new(v.co)
        for f in grain_temp.faces: spikelet_bm.faces.new([vert_map[v] for v in f.verts])
        grain_temp.free()

        # 2. Glumes (The husks/chaff) - Two elongated shells wrapping the seed
        for side in [-1, 1]:
            glume_temp = bmesh.new()
            bmesh.ops.create_cube(glume_temp, size=1.0)
            for v in glume_temp.verts:
                # Transform cube into a long thin husk
                vz = (v.co.z + 0.5) * 0.4 * scale
                vx = v.co.x * 0.06 * scale
                vy = v.co.y * 0.18 * scale
                # Taper the tip of the husk
                t_factor = vz / (0.4 * scale)
                vx *= (1.0 - t_factor * 0.7)
                vy *= (1.0 - t_factor * 0.5)
                
                # Offset to wrap around the seed
                v.co = Vector((vx, vy * side + 0.08 * scale, vz - 0.1))
                v.co = mat_local @ v.co

            g_vert_map = {}
            for v in glume_temp.verts: g_vert_map[v] = spikelet_bm.verts.new(v.co)
            for f in glume_temp.faces: spikelet_bm.faces.new([g_vert_map[v] for v in f.verts])
            glume_temp.free()

        # 3. Awns (The long bristles)
        awn_len = (1.2 + random.random() * 0.8) * scale
        v_start = spikelet_bm.verts.new(mat_local @ Vector((0, 0, 0.2)))
        v_end = spikelet_bm.verts.new(mat_local @ Vector((0, 0, 0.2 + awn_len)))
        spikelet_bm.edges.new((v_start, v_end))

    mesh_spikelets = bpy.data.meshes.new("SpikeletsMesh")
    spikelet_bm.to_mesh(mesh_spikelets)
    obj_spikelets = bpy.data.objects.new("Spikelets", mesh_spikelets)
    bpy.context.collection.objects.link(obj_spikelets)
    obj_spikelets.data.materials.append(mat_grain)
    spikelet_bm.free()

    # Final orientation for perspective
    rot = (math.radians(25), 0, math.radians(-10))
    obj_rachis.rotation_euler = rot
    obj_spikelets.rotation_euler = rot

if __name__ == "__main__":
    create_wheat_ear()
