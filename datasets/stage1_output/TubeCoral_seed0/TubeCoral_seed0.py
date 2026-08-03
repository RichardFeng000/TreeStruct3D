import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears default objects from the scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_coral_material():
    """Creates a material with sandy beige, olive green, pink blush and high-frequency granular bumps."""
    mat = bpy.data.materials.new(name="CoralMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    for n in nodes:
        nodes.remove(n)
        
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    
    # Color Noise and Ramp
    color_noise = nodes.new('ShaderNodeTexNoise')
    color_ramp = nodes.new('ShaderNodeValToRGB')
    color_noise.inputs['Scale'].default_value = 8.0
    color_noise.inputs['Detail'].default_value = 15.0
    
    elements = color_ramp.color_ramp.elements
    elements[0].position = 0.0
    elements[0].color = (0.9, 0.8, 0.6, 1) # Warm Sandy Beige
    
    if len(elements) < 3:
        el1 = elements.new(0.45)
        el1.color = (0.4, 0.42, 0.2, 1) # Muted Olive Green
    else:
        elements[1].position = 0.45
        elements[1].color = (0.4, 0.42, 0.2, 1)

    elements[2].position = 0.8
    elements[2].color = (1.0, 0.65, 0.75, 1) # Subtle Pink Blush
    
    # High-frequency granular bumps using a Bump node
    bump_noise = nodes.new('ShaderNodeTexNoise')
    bump_noise.inputs['Scale'].default_value = 80.0  # Very high for "granular" look
    bump_noise.inputs['Detail'].default_value = 15.0
    
    bump_node = nodes.new('ShaderNodeBump')
    bump_node.inputs['Strength'].default_value = 0.4
    
    links.new(color_noise.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    
    links.new(bump_noise.outputs['Fac'], bump_node.inputs['Height'])
    links.new(bump_node.outputs['Normal'], bsdf.inputs['Normal'])
    
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    bsdf.inputs['Roughness'].default_value = 0.9
    return mat

def apply_organic_jitter(bm, strength=0.05):
    """Adds slight organic irregularity to avoid perfect cylinders."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        v.co += Vector((random.uniform(-strength, strength), 
                       random.uniform(-strength, strength), 
                       random.uniform(-strength, strength)))

def generate_tube(start_pos, end_pos, radius):
    """Generates a thick organic tube."""
    bm = bmesh.new()
    
    # Increase resolution to avoid faceting in the render
    segments = 64
    rings = 80
    depth = (end_pos - start_pos).length
    
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=radius, radius2=radius*0.75, depth=depth, segments=segments)
    
    # Align tube to positions
    direction = (end_pos - start_pos).normalized()
    up = Vector((0, 0, 1))
    rot_quat = up.rotation_difference(direction)
    rot_matrix = rot_quat.to_matrix().to_4x4()
    
    # We shift the cone to be centered on the Z axis before rotating and translating
    for v in bm.verts:
        v.co.z += depth * 0.5
        # Add a slight organic curve
        dist = v.co.z / depth
        curve = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 0)) * (dist**2)
        v.co += curve
        v.co = rot_matrix @ v.co + start_pos

    apply_organic_jitter(bm, strength=0.06)
    bm.normal_update()
    
    mesh = bpy.data.meshes.new("TubeMesh")
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def generate_coral():
    clear_scene()
    coral_mat = create_coral_material()
    
    num_tubes = 12
    base_radius = 1.6
    min_height = 5.0
    max_height = 8.0
    tube_radius = 0.6

    # --- Organic Base ---
    bm_base = bmesh.new()
    bmesh.ops.create_uvsphere(bm_base, u_segments=64, v_segments=32, radius=base_radius)
    for v in bm_base.verts:
        v.co.z *= 0.3
        # Distort base to look like a growth cluster
        v.co += Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), random.uniform(-0.1, 0.1)))
    
    apply_organic_jitter(bm_base, strength=0.1)
    bm_base.normal_update()
    
    mesh_base = bpy.data.meshes.new("CoralBase")
    bm_base.to_mesh(mesh_base)
    bm_base.free()
    
    obj_base = bpy.data.objects.new("CoralBase", mesh_base)
    bpy.context.collection.objects.link(obj_base)
    obj_base.data.materials.append(coral_mat)

    # --- Tube Assembly ---
    for i in range(num_tubes):
        angle = (2 * math.pi / num_tubes) * i + random.uniform(-0.1, 0.1)
        start_dist = random.uniform(0.3, 0.8)
        start_x = math.cos(angle) * start_dist
        start_y = math.sin(angle) * start_dist
        start_pos = Vector((start_x, start_y, -0.2)) # slightly embed in base
        
        # Splayed silhouette: Tubes lean outward significantly
        lean_factor = random.uniform(2.5, 4.0)
        height = random.uniform(min_height, max_height)
        end_pos = Vector((start_x * lean_factor, start_y * lean_factor, height))
        
        radius_var = tube_radius * random.uniform(0.85, 1.15)
        tube_mesh = generate_tube(start_pos, end_pos, radius_var)
        obj_tube = bpy.data.objects.new(f"Tube_{i}", tube_mesh)
        bpy.context.collection.objects.link(obj_tube)
        obj_tube.data.materials.append(coral_mat)

    # Smooth shading for organic look
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for poly in obj.data.polygons:
                poly.use_smooth = True

if __name__ == "__main__":
    generate_coral()
