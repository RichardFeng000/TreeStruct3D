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

    # Parameters
    num_nodes = 30
    spikelets_per_node = 2
    rachis_height = 12.0
    curve_amplitude = 0.8
    
    color_gold = (0.8, 0.7, 0.3, 1.0)
    color_green = (0.4, 0.5, 0.2, 1.0)
    mat_grain = create_material("GrainMat", color_gold)
    mat_stem = create_material("StemMat", color_green)

    # Rachis Path Calculation
    segments = 60
    rachis_points = []
    for i in range(segments + 1):
        t = i / segments
        z = t * rachis_height
        x = math.sin(t * math.pi * 0.8) * curve_amplitude * (t**1.2)
        y = math.cos(t * math.pi * 0.5) * 0.2 * t
        rachis_points.append(Vector((x, y, z)))

    # --- Create Rachis Mesh ---
    rachis_bm = bmesh.new()
    radius = 0.05
    for i in range(segments):
        p1 = rachis_points[i]
        p2 = rachis_points[i+1]
        v_dir = (p2 - p1).normalized()
        
        # Local Frame
        up_ref = Vector((0, 0, 1)) if abs(v_dir.dot(Vector((0, 0, 1)))) < 0.9 else Vector((0, 1, 0))
        right = v_dir.cross(up_ref).normalized()
        up = v_dir.cross(right).normalized()

        ring_res = 6
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
        # Find point on rachis path
        idx = int(t * segments)
        p = rachis_points[idx]
        v_dir = (rachis_points[min(idx+1, segments)] - p).normalized()
        
        scale = 1.0 - (t**2) * 0.4 # Tapering at the top
        
        # Frame for placement
        up_ref = Vector((0, 0, 1)) if abs(v_dir.dot(Vector((0, 0, 1)))) < 0.9 else Vector((0, 1, 0))
        right = v_dir.cross(up_ref).normalized()
        up = v_dir.cross(right).normalized()

        for s in range(spikelets_per_node):
            # Alternating pattern
            angle = (math.pi * s / spikelets_per_node) + (n * 0.5)
            offset_vec = (right * math.cos(angle) + up * math.sin(angle))
            pos = p + offset_vec * radius
            
            # Orientation of the grain: mostly along rachis, slightly angled out
            grain_up = (v_dir * 0.8 + offset_vec * 0.2).normalized()
            
            # Local Transform Matrix for a single spikelet component
            z_axis = grain_up
            x_axis = Vector((1, 0, 0)) if abs(z_axis.dot(Vector((1, 0, 0)))) < 0.9 else Vector((0, 1, 0))
            x_axis = z_axis.cross(x_axis).normalized()
            y_axis = z_axis.cross(x_axis).normalized()
            mat_local = Matrix((x_axis, y_axis, z_axis)).to_4x4() @ Matrix.Translation(pos)

            # 1. The Grain (Seed)
            grain_temp = bmesh.new()
            bmesh.ops.create_uvsphere(grain_temp, u_segments=6, v_segments=6, radius=0.12 * scale)
            for v in grain_temp.verts:
                v.co.z *= 2.2 # Elongate
                v.co.x *= 0.7
                v.co.y *= 0.7
                v.co = mat_local @ v.co
            
            # Merge grain into spikelet_bm
            verts_map = []
            for v in grain_temp.verts:
                verts_map.append(spikelet_bm.verts.new(v.co))
            for f in grain_temp.faces:
                spikelet_bm.faces.new([verts_map[vi] for vi in f.verts])
            grain_temp.free()

            # 2. The Glumes (Husks)
            for g_idx in range(2):
                glume_temp = bmesh.new()
                bmesh.ops.create_cube(glume_temp, size=1.0)
                for v in glume_temp.verts:
                    v.co.z = (v.co.z + 0.5) * 0.35 * scale
                    v.co.x *= 0.06 * scale
                    v.co.y *= 0.12 * scale
                    # Taper the top of the glume
                    t_factor = (v.co.z + 0.17) / 0.35
                    v.co.x *= (1.0 - t_factor * 0.6)
                    # Shift and rotate slightly relative to grain
                    if g_idx == 0: v.co.y += 0.04
                    else: v.co.y -= 0.04
                    v.co.z -= 0.15
                    v.co = mat_local @ v.co

                g_verts_map = []
                for v in glume_temp.verts:
                    g_verts_map.append(spikelet_bm.verts.new(v.co))
                for f in glume_temp.faces:
                    spikelet_bm.faces.new([g_verts_map[vi] for vi in f.verts])
                glume_temp.free()

            # 3. The Awn (Bristle)
            awn_len = (1.2 + random.random()) * scale
            v_start = spikelet_bm.verts.new(mat_local @ Vector((0, 0, 0.15)))
            v_end = spikelet_bm.verts.new(mat_local @ Vector((0, 0, 0.15 + awn_len)))
            spikelet_bm.edges.new((v_start, v_end))

    # Create Spikelets Object
    mesh_spikelets = bpy.data.meshes.new("SpikeletsMesh")
    spikelet_bm.to_mesh(mesh_spikelets)
    obj_spikelets = bpy.data.objects.new("Spikelets", mesh_spikelets)
    bpy.context.collection.objects.link(obj_spikelets)
    obj_spikelets.data.materials.append(mat_grain)
    spikelet_bm.free()

    # Final scene adjustments
    rot_val = (math.radians(12), 0, math.radians(-8))
    obj_rachis.rotation_euler = rot_val
    obj_spikelets.rotation_euler = rot_val

if __name__ == "__main__":
    create_wheat_ear()
