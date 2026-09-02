import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Clears the default Blender scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_coral_material():
    """Creates a material with the requested beige, olive and pink tones."""
    mat = bpy.data.materials.new(name="CoralMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    for n in nodes:
        nodes.remove(n)
        
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    noise = nodes.new('ShaderNodeTexNoise')
    color_ramp = nodes.new('ShaderNodeValToRGB')
    
    noise.inputs['Scale'].default_value = 12.0
    noise.inputs['Detail'].default_value = 8.0
    
    # Sandy Beige, Olive Green, Pink Blush
    elements = color_ramp.color_ramp.elements
    elements[0].position = 0.0
    elements[0].color = (0.83, 0.71, 0.55, 1) # Sandy Beige
    
    el1 = elements.new(0.45)
    el1.color = (0.35, 0.42, 0.2, 1) # Olive Green
    
    elements[2].position = 0.85
    elements[2].color = (0.95, 0.75, 0.8, 1) # Pink Blush
    
    links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    bsdf.inputs['Roughness'].default_value = 0.85
    return mat

def generate_tube(start_pos, end_pos, radius):
    """Generates a single finger-like tube with granular detail."""
    bm = bmesh.new()
    
    # Create the cylinder along Z axis initially
    segments = 24
    rings = 32
    # Using create_cone to allow taper
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=radius, radius2=radius*0.7, depth=1.0, segments=segments)
    
    # Align tube from start_pos to end_pos
    direction = end_pos - start_pos
    length = direction.length
    
    # Calculate rotation matrix to align Z axis (0,0,1) with the direction vector
    up = Vector((0, 0, 1))
    rot_quat = up.rotation_difference(direction.normalized())
    rot_matrix = rot_quat.to_matrix().to_4x4()
    
    # Scale to length and rotate/translate vertices
    # We translate it so the bottom is at start_pos, then scale and rotate
    for v in bm.verts:
        # Current local coordinates are centered on Z=0 (range -0.5 to 0.5)
        # Shift so base is at origin locally
        v.co.z += 0.5 
        # Scale length
        v.co.z *= length
        # Rotate
        v.co = rot_matrix @ v.co
        # Translate
        v.co += start_pos

    # Heavy subdivision for organic noise/bumps
    for _ in range(2):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1)

    # Granular polyp bumps: push vertices along their normals
    # We calculate pseudo-normals manually by looking at the tube axis
    axis = direction.normalized()
    for v in bm.verts:
        # Vector from point to axis line (approximation of surface normal for cylinder)
        proj = (v.co - start_pos).dot(axis) * axis
        normal = (v.co - (start_pos + proj)).normalized()
        
        # Add a random "bump" factor based on coordinates
        seed = sum(v.co) * 123.456
        noise = math.sin(seed) * 0.05 + random.uniform(-0.03, 0.03)
        v.co += normal * noise

    # Create distinct "polyp" clusters (blobs)
    num_bumps = 80
    for _ in range(num_bumps):
        target_v = random.choice(bm.verts)
        bump_rad = 0.25
        strength = random.uniform(0.04, 0.12)
        
        # Find vertices close to the target and push them out
        for v in bm.verts:
            dist = (v.co - target_v.co).length
            if dist < bump_rad:
                proj = (v.co - start_pos).dot(axis) * axis
                normal = (v.co - (start_pos + proj)).normalized()
                v.co += normal * strength * (1.0 - dist/bump_rad)

    mesh = bpy.data.meshes.new("TubeMesh")
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def generate_coral():
    clear_scene()
    
    coral_mat = create_coral_material()
    
    # Base Parameters
    num_tubes = 8
    base_radius = 1.2
    min_height = 3.5
    max_height = 6.0
    tube_radius = 0.4

    # Create the shared organic base
    bm_base = bmesh.new()
    bmesh.ops.create_uvsphere(bm_base, u_segments=32, v_segments=16, radius=base_radius)
    for v in bm_base.verts:
        v.co.z *= 0.4 # Flatten the base
        v.co.x += random.uniform(-0.15, 0.15)
        v.co.y += random.uniform(-0.15, 0.15)
    
    mesh_base = bpy.data.meshes.new("CoralBase")
    bm_base.to_mesh(mesh_base)
    bm_base.free()
    
    obj_base = bpy.data.objects.new("CoralBase", mesh_base)
    bpy.context.collection.objects.link(obj_base)
    obj_base.data.materials.append(coral_mat)
    
    # Add subdivision to base for softness
    subdiv = obj_base.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 2

    # Create the tubes (fingers)
    for i in range(num_tubes):
        angle = (2 * math.pi / num_tubes) * i
        start_x = math.cos(angle) * random.uniform(0.4, 0.8)
        start_y = math.sin(angle) * random.uniform(0.4, 0.8)
        start_pos = Vector((start_x, start_y, 0))
        
        # Splayed outward from center
        lean_factor = random.uniform(1.5, 2.5)
        height = random.uniform(min_height, max_height)
        end_pos = Vector((start_x * lean_factor, start_y * lean_factor, height))
        
        radius_var = tube_radius * random.uniform(0.8, 1.2)
        
        tube_mesh = generate_tube(start_pos, end_pos, radius_var)
        obj_tube = bpy.data.objects.new(f"Tube_{i}", tube_mesh)
        bpy.context.collection.objects.link(obj_tube)
        obj_tube.data.materials.append(coral_mat)

if __name__ == "__main__":
    generate_coral()
