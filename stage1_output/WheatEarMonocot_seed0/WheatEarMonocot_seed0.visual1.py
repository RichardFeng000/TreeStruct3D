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
    num_nodes = 50  # Increased for tighter packing
    spikelets_per_node = 2
    rachis_height = 8.0
    curve_amplitude = 0.8
    
    color_gold = (0.7, 0.6, 0.3, 1.0) # Muted gold
    color_green = (0.3, 0.4, 0.15, 1.0) # Muted green
    mat_grain = create_material("GrainMat", color_gold)
    mat_stem = create_material("StemMat", color_green)

    # --- Rachis Path Calculation ---
    segments = 80
    rachis_points = []
    for i in range(segments + 1):
        t = i / segments
        z = t * rachis_height
        # Slight upward curve
        x = math.sin(t * math.pi * 0.7) * curve_amplitude * (t**2)
        y = math.cos(t * math.pi * 0.5) * 0.3 * t
        rachis_points.append(Vector((x, y, z)))

    # --- Create Rachis Mesh ---
    rachis_bm = bmesh.new()
    radius = 0.08
    for i in range(segments):
        p1 = rachis_points[i]
        p2 = rachis_points[i+1]
        v_dir = (p2 - p1).normalized()
        
        up_ref = Vector((0, 0, 1)) if abs(v_dir.dot(Vector((0, 0, 1)))) < 0.9 else Vector((0, 1, 0))
        right = v_dir.cross(up_ref).normalized()
        up = v_dir.cross(right).normalized()

        ring_res = 8
        r1 = []
        r2 = []
        for j in range(ring_res):
            angle = (2 * math.pi * j) / ring_res
            v1 = p1 + (right * math.cos(angle) + up * math.sin(angle)) * radius
            v2 = p2 + (right * math.cos(angle) + up * math.sin(angle)) * radius
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
    
    for n in range(num_nodes):
        t = n / num_nodes
        idx = int(t * segments)
        p = rachis_points[min(idx, segments)]
        v_dir = (rachis_points[min(idx+1, segments)] - p).normalized()
        
        # Tapering scale: smaller at the top
        scale = 1.0 - (t**2) * 0.5
        
        up_ref = Vector((0, 0, 1)) if abs(v_dir.dot(Vector((0, 0, 1)))) < 0.9 else Vector((0, 1, 0))
        right = v_dir.cross(up_ref).normalized()
        up = v_dir.cross(right).normalized()

        for s in range(spikelets_per_node):
            # Alternating phyllotaxis pattern for tight packing
            angle = (math.pi * s / spikelets_per_node) + (n * 1.5) # Spiraling offset
            offset_vec = (right * math.cos(angle) + up * math.sin(angle))
            # Position exactly on the surface of the rachis
            pos = p + offset_vec * radius
            
            # Orientation: tilt outwards and upwards
            grain_up = (v_dir * 0.7 + offset_vec * 0.5).normalized()
            z_axis = grain_up
            x_axis = Vector((1, 0, 0)) if abs(z_axis.dot(Vector((1, 0, 0)))) < 0.9 else Vector((0, 1, 0))
            x_axis = z_axis.cross(x_axis).normalized()
            y_axis = z_axis.cross(x_axis).normalized()
            mat_local = Matrix((x_axis, y_axis, z_axis)).to_4x4() @ Matrix.Translation(pos)

            # 1. The Grain/Seed - Elongated teardrop shape
            grain_temp = bmesh.new()
            bmesh.ops.create_uvsphere(grain_temp, u_segments=8, v_segments=6, radius=0.12 * scale)
            for v in grain_temp.verts:
                v.co.z *= 2.5 # Elongate
                v.co.x *= 0.6
                v.co.y *= 0.6
                # Taper the base to attach better
                if v.co.z < 0:
                    v.co.x *= (1.0 + v.co.z * 2.0)
                    v.co.y *= (1.0 + v.co.z * 2.0)
                v.co = mat_local @ v.co
            
            vert_map = {}
            for v in grain_temp.verts:
                vert_map[v] = spikelet_bm.verts.new(v.co)
            for f in grain_temp.faces:
                spikelet_bm.faces.new([vert_map[v] for v in f.verts])
            grain_temp.free()

            # 2. The Glumes (Husks) - wrap around the seed
            for g_idx in range(2):
                glume_temp = bmesh.new()
                bmesh.ops.create_cube(glume_temp, size=1.0)
                for v in glume_temp.verts:
                    v.co.z = (v.co.z + 0.5) * 0.4 * scale
                    v.co.x *= 0.08 * scale
                    v.co.y *= 0.18 * scale
                    # Taper the tip heavily for "chaff" look
                    t_factor = (v.co.z / (0.4 * scale))
                    v.co.x *= (1.0 - t_factor * 0.8)
                    v.co.y *= (1.0 - t_factor * 0.5)
                    if g_idx == 0: v.co.y += 0.06
                    else: v.co.y -= 0.06
                    v.co.z -= 0.1 # Shift to overlap grain base
                    v.co = mat_local @ v.co

                g_vert_map = {}
                for v in glume_temp.verts:
                    g_vert_map[v] = spikelet_bm.verts.new(v.co)
                for f in glume_temp.faces:
                    spikelet_bm.faces.new([g_vert_map[v] for v in f.verts])
                glume_temp.free()

            # 3. Awns (Bristles) - thinner and more integrated
            awn_len = (0.8 + random.random() * 0.7) * scale
            v_start = spikelet_bm.verts.new(mat_local @ Vector((0, 0, 0.3)))
            v_end = spikelet_bm.verts.new(mat_local @ Vector((0, 0, 0.3 + awn_len)))
            spikelet_bm.edges.new((v_start, v_end))

    mesh_spikelets = bpy.data.meshes.new("SpikeletsMesh")
    spikelet_bm.to_mesh(mesh_spikelets)
    obj_spikelets = bpy.data.objects.new("Spikelets", mesh_spikelets)
    bpy.context.collection.objects.link(obj_spikelets)
    obj_spikelets.data.materials.append(mat_grain)
    spikelet_bm.free()

    # Final orientation for elevated perspective
    rot_val = (math.radians(20), 0, math.radians(-15))
    obj_rachis.rotation_euler = rot_val
    obj_spikelets.rotation_euler = rot_val

if __name__ == "__main__":
    create_wheat_ear()
