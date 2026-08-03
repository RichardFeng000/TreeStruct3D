import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, is_fruit=False):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    if is_fruit:
        # Add a noise texture for the golden-yellow with green tints effect
        node_noise = nodes.new(type='ShaderNodeTexNoise')
        node_noise.inputs['Scale'].default_value = 10.0
        
        node_ramp = nodes.new(type='ShaderNodeValToRGB')
        # Golden Yellow to subtle Greenish-Yellow
        node_ramp.color_ramp.elements[0].color = (0.3, 0.5, 0.1, 1.0) # Green tint
        node_ramp.color_ramp.elements[1].color = color # Golden Yellow
        
        mat.node_tree.links.new(node_noise.outputs['Fac'], node_ramp.inputs['Fac'])
        mat.node_tree.links.new(node_ramp.outputs['Color'], node_principled.inputs['Base Color'])
    else:
        node_principled.inputs['Base Color'].default_value = color
        
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_pineapple():
    # Parameters
    body_radius = 1.0
    body_height_scale = 1.6
    num_scales = 500
    golden_angle = math.pi * (3 - math.sqrt(5))
    
    # Materials
    mat_fruit = create_material("FruitMat", (1.0, 0.75, 0.1, 1.0), is_fruit=True) # Golden Yellow + Noise
    mat_leaf = create_material("LeafMat", (0.25, 0.38, 0.3, 1.0))   # Blue-Gray Green
    mat_spine = create_material("SpineMat", (0.05, 0.05, 0.05, 1.0)) # Dark/Black
    
    # --- Fruit Body ---
    body_mesh = bpy.data.meshes.new("PineappleBody")
    body_obj = bpy.data.objects.new("Pineapple", body_mesh)
    bpy.context.collection.objects.link(body_obj)
    
    bm = bmesh.new()
    
    for i in range(num_scales):
        # Fibonacci Spiral on spheroid
        phi = golden_angle * i
        cos_theta = 1 - (i / float(num_scales - 1)) * 2 
        sin_theta = math.sqrt(max(0, 1 - cos_theta**2))
        
        px, py, pz = sin_theta * math.cos(phi), sin_theta * math.sin(phi), cos_theta
        pos = Vector((px * body_radius, py * body_radius, pz * body_height_scale))
        normal = Vector((px, py, pz * (1.0/body_height_scale))).normalized()
        
        # Scale geometry - slightly more rounded "fruitlet" look
        s_size = 0.22
        s_height = 0.15
        
        up = normal
        right = Vector((0, 0, 1)).cross(up).normalized() if abs(up.z) < 0.9 else Vector((1, 0, 0)).cross(up).normalized()
        forward = up.cross(right).normalized()
        
        # Diamond base vertices
        v0 = bm.verts.new(pos + (right + forward) * s_size)
        v1 = bm.verts.new(pos + (-right + forward) * s_size)
        v2 = bm.verts.new(pos + (-right - forward) * s_size)
        v3 = bm.verts.new(pos + (right - forward) * s_size)
        tip = bm.verts.new(pos + up * s_height)
        
        bm.faces.new((v0, v1, tip))
        bm.faces.new((v1, v2, tip))
        bm.faces.new((v2, v3, tip))
        bm.faces.new((v3, v0, tip))
        
        # Small dark spine tips at the bottom (pz < -0.6)
        if pz < -0.7:
            spine_len = 0.1
            s_tip = bm.verts.new(pos + up * (-spine_len))
            bm.faces.new((v0, v1, s_tip)) # Simplified spines as small wedges
            bm.faces.new((v2, v3, s_tip))

    bm.to_mesh(body_mesh)
    bm.free()
    body_obj.data.materials.append(mat_fruit)

    # --- Crown Leaves ---
    crown_mesh = bpy.data.meshes.new("Crown")
    crown_obj = bpy.data.objects.new("Crown", crown_mesh)
    bpy.context.collection.objects.link(crown_obj)
    
    bm_l = bmesh.new()
    
    # More organic leaf distribution
    leaf_rings = 5
    leaves_per_ring = [4, 6, 8, 10, 12]
    leaf_heights = [0.7, 1.3, 1.9, 2.5, 3.1]
    leaf_widths = [0.1, 0.15, 0.18, 0.2, 0.22]
    
    for ring in range(leaf_rings):
        count = leaves_per_ring[ring]
        h_max = leaf_heights[ring]
        w_base = leaf_widths[ring]
        angle_step = (2 * math.pi) / count
        
        for i in range(count):
            rot_z = angle_step * i + (ring * 0.4) # Offset rings for rosette look
            lean = 0.3 + (ring * 0.15)
            
            segments = 12
            prev_pair = None
            
            for s in range(segments + 1):
                t = s / segments
                # Taper width from base to tip
                w = w_base * (1.0 - t**0.7)
                # Curve the leaf outward and slightly upward
                z = t * h_max
                curve_x = math.sin(t * math.pi * 0.5) * lean * (1.0 + t*0.5)
                
                # Local coords
                p1_loc = Vector((curve_x, w/2, z))
                p2_loc = Vector((curve_x, -w/2, z))
                
                rot_mat = Matrix.Rotation(rot_z, 4, 'Z')
                v1 = bm_l.verts.new(rot_mat @ p1_loc)
                v2 = bm_l.verts.new(rot_mat @ p2_loc)
                
                if prev_pair:
                    bm_l.faces.new((prev_pair[0], v1, v2, prev_pair[1]))
                prev_pair = (v1, v2)

    bm_l.to_mesh(crown_mesh)
    bm_l.free()
    
    # Position crown on top of body
    crown_obj.location.z = body_height_scale * 0.75
    crown_obj.data.materials.append(mat_leaf)

if __name__ == "__main__":
    clear_scene()
    create_pineapple()
