import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Metallic'].default_value = metallic
    node_principled.inputs['Roughness'].default_value = roughness
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def build_staircase():
    clear_scene()
    
    # Parameters
    num_steps = 30
    inner_radius = 2.5
    outer_radius = 4.5
    step_height = 0.18
    total_angle = math.pi * 1.2  # ~216 degrees
    angle_per_step = total_angle / num_steps
    baluster_height = 0.9
    rail_radius = 0.07
    
    # Materials
    mat_wood = create_material("DarkWood", (0.15, 0.08, 0.05, 1.0), metallic=0.1, roughness=0.3)
    mat_gold = create_material("GoldTrim", (0.8, 0.6, 0.2, 1.0), metallic=1.0, roughness=0.2)

    mesh = bpy.data.meshes.new("ElegantStairs")
    obj = bpy.data.objects.new("ElegantStairs", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    # 1. Solid Steps
    for i in range(num_steps):
        angle = i * angle_per_step
        z = i * step_height
        a1, a2 = angle, angle + angle_per_step
        
        # Tread (top) - give it thickness
        t_thick = 0.05
        v1 = bm.verts.new(Vector((inner_radius * math.cos(a1), inner_radius * math.sin(a1), z)))
        v2 = bm.verts.new(Vector((outer_radius * math.cos(a1), outer_radius * math.sin(a1), z)))
        v3 = bm.verts.new(Vector((outer_radius * math.cos(a2), outer_radius * math.sin(a2), z)))
        v4 = bm.verts.new(Vector((inner_radius * math.cos(a2), inner_radius * math.sin(a2), z)))
        bm.faces.new((v1, v2, v3, v4))
        
        # Bottom of tread
        v5 = bm.verts.new(Vector((inner_radius * math.cos(a1), inner_radius * math.sin(a1), z - t_thick)))
        v6 = bm.verts.new(Vector((outer_radius * math.cos(a1), outer_radius * math.sin(a1), z - t_thick)))
        v7 = bm.verts.new(Vector((outer_radius * math.cos(a2), outer_radius * math.sin(a2), z - t_thick)))
        v8 = bm.verts.new(Vector((inner_radius * math.cos(a2), inner_radius * math.sin(a2), z - t_thick)))
        bm.faces.new((v5, v8, v7, v6))
        
        # Side walls of tread
        bm.faces.new((v1, v2, v6, v5))
        bm.faces.new((v2, v3, v7, v6))
        bm.faces.new((v3, v4, v8, v7))
        bm.faces.new((v4, v1, v5, v8))

        # Riser (vertical) - fills gap between this tread and previous
        if i > 0:
            prev_z = (i-1) * step_height
            vr1 = bm.verts.new(Vector((inner_radius * math.cos(a1), inner_radius * math.sin(a1), prev_z)))
            vr2 = bm.verts.new(Vector((outer_radius * math.cos(a1), outer_radius * math.sin(a1), prev_z)))
            bm.faces.new((vr1, vr2, v6, v5)) # Simplification: connects to tread bottom

    # 2. Dramatic Bowing Base (Sculptural Wall)
    # Create a thick volumetric base that bows outward dramatically at the center of the arc
    res = 60
    base_thickness = 0.3
    base_width = 0.6
    verts_bottom_inner, verts_bottom_outer = [], []
    verts_top_inner, verts_top_outer = [], []

    for i in range(res + 1):
        t = i / res
        ang = t * total_angle
        # The "bow": dramatic outward shift at mid-arc
        bow = 1.5 * math.sin(math.pi * t)
        r_base = inner_radius - base_width + bow
        z_top = (t * num_steps) * step_height
        
        vbi = bm.verts.new(Vector((r_base * math.cos(ang), r_base * math.sin(ang), 0)))
        vbo = bm.verts.new(Vector(((r_base + base_thickness) * math.cos(ang), (r_base + base_thickness) * math.sin(ang), 0)))
        vti = bm.verts.new(Vector((inner_radius * math.cos(ang), inner_radius * math.sin(ang), z_top)))
        vto = bm.verts.new(Vector(((inner_radius + base_thickness) * math.cos(ang), (inner_radius + base_thickness) * math.sin(ang), z_top)))
        
        verts_bottom_inner.append(vbi)
        verts_bottom_outer.append(vbo)
        verts_top_inner.append(vti)
        verts_top_outer.append(vto)

    for i in range(res):
        # Outer face of the bowing base
        bm.faces.new((verts_bottom_outer[i], verts_bottom_outer[i+1], verts_top_outer[i+1], verts_top_outer[i]))
        # Inner face
        bm.faces.new((verts_bottom_inner[i], verts_top_inner[i], verts_top_inner[i+1], verts_bottom_inner[i+1]))
        # Bottom cap
        bm.faces.new((verts_bottom_inner[i], verts_bottom_outer[i], verts_bottom_outer[i+1], verts_bottom_inner[i+1]))
        # Top cap
        bm.faces.new((verts_top_inner[i], verts_top_inner[i+1], verts_top_outer[i+1], verts_top_outer[i]))

    # 3. Balusters and Handrail (Outer edge)
    handrail_points = []
    for i in range(num_steps):
        angle = i * angle_per_step
        z = i * step_height
        pos = Vector((outer_radius * math.cos(angle), outer_radius * math.sin(angle), z))
        
        # Baluster (turned spindle)
        b_res = 8
        b_segs = 10
        b_rad = 0.04
        prev_ring = []
        for s in range(b_segs + 1):
            curr_z = z + (s / b_segs) * baluster_height
            r = b_rad * (1.2 if (s == 0 or s == b_segs) else 0.7)
            ring = []
            for j in range(b_res):
                a = (j / b_res) * 2 * math.pi
                v = bm.verts.new(pos + Vector((r * math.cos(a), r * math.sin(a), 0))) # Relative to pos, but needs z offset
                # Actually add the Z correctly
                v.co.z = curr_z
                ring.append(v)
            if prev_ring:
                for j in range(b_res):
                    bm.faces.new((prev_ring[j], prev_ring[(j+1)%b_res], ring[(j+1)%b_res], ring[j]))
            prev_ring = ring
        
        handrail_points.append(pos + Vector((0, 0, baluster_height)))

    # Handrail (Swept tube)
    hr_res = 8
    prev_hr_ring = []
    for i in range(len(handrail_points)):
        p = handrail_points[i]
        if i < len(handrail_points) - 1:
            tangent = (handrail_points[i+1] - p).normalized()
        else:
            tangent = (p - handrail_points[i-1]).normalized()
        
        # Orientation frame
        up = Vector((0,0,1))
        right = tangent.cross(up).normalized()
        true_up = right.cross(tangent).normalized()
        
        ring = []
        for j in range(hr_res):
            a = (j/hr_res) * 2 * math.pi
            v = bm.verts.new(p + right * math.cos(a) * rail_radius + true_up * math.sin(a) * rail_radius)
            ring.append(v)
        
        if prev_hr_ring:
            for j in range(hr_res):
                bm.faces.new((prev_hr_ring[j], prev_hr_ring[(j+1)%hr_res], ring[(j+1)%hr_res], ring[j]))
        prev_hr_ring = ring

    bm.to_mesh(mesh)
    bm.free()

    # Assign Materials to parts (approximation by geometry location/size if needed, but here we apply simply)
    obj.data.materials.append(mat_wood)
    obj.data.materials.append(mat_gold)
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    build_staircase()
