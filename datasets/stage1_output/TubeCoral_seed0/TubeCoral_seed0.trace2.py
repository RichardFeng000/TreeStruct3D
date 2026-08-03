import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Clears default objects from the scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_coral_material():
    """Creates a material with the specified organic coral colors."""
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
    
    # Noise for color variation across the surface
    noise.inputs['Scale'].default_value = 5.0
    noise.inputs['Detail'].default_value = 15.0
    
    # Sandy Beige, Olive Green, Pink Blush
    elements = color_ramp.color_ramp.elements
    elements[0].position = 0.0
    elements[0].color = (0.85, 0.75, 0.6, 1) # Sandy Beige
    
    if len(elements) < 3:
        el1 = elements.new(0.45)
        el1.color = (0.3, 0.35, 0.2, 1) # Muted Olive Green
    else:
        elements[1].position = 0.45
        elements[1].color = (0.3, 0.35, 0.2, 1)

    elements[2].position = 0.85
    elements[2].color = (0.9, 0.7, 0.75, 1) # Subtle Pink Blush
    
    links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    bsdf.inputs['Roughness'].default_value = 0.9
    return mat

def apply_granular_texture(bm, strength=0.12):
    """Adds high-frequency granular bumps to the mesh."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        # Use a combination of sine waves and random for 'polyp' look
        # This creates small peaks rather than smooth noise
        seed = (v.co.x * 12.0) + (v.co.y * 15.0) + (v.co.z * 18.0)
        bump = math.sin(seed) * 0.5 + 0.5 # Normalized to [0, 1]
        # Only push out if the bump value is high (simulating distinct polyps)
        if bump > 0.6:
            magnitude = (bump - 0.6) * strength * 2.0
            v.co += v.normal * magnitude

def generate_tube(start_pos, end_pos, radius):
    """Generates a single finger-like tube with high geometric detail."""
    bm = bmesh.new()
    
    # Higher resolution for the base cylinder to allow granular bumps
    segments = 32
    rings = 48
    depth = (end_pos - start_pos).length
    
    # Create a tapered cylinder
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=radius, radius2=radius*0.7, depth=depth, segments=segments)
    
    # Align the tube to the start and end positions
    direction = (end_pos - start_pos).normalized()
    up = Vector((0, 0, 1))
    rot_quat = up.rotation_difference(direction)
    rot_matrix = rot_quat.to_matrix().to_4x4()
    
    for v in bm.verts:
        # Move base to origin locally (cone is centered at Z=0 by default)
        v.co.z += depth * 0.5
        # Rotate and translate
        v.co = rot_matrix @ v.co + start_pos

    # Subdivide heavily for organic detail
    for _ in range(2):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1)
    
    # Calculate normals and apply bumps
    bm.normal_update()
    apply_granular_texture(bm, strength=0.15)
    
    mesh = bpy.data.meshes.new("TubeMesh")
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def generate_coral():
    clear_scene()
    
    coral_mat = create_coral_material()
    
    # Parameters for the coral structure
    num_tubes = 9
    base_radius = 1.3
    min_height = 4.0
    max_height = 7.0
    tube_radius = 0.45

    # --- Create Organic Base ---
    bm_base = bmesh.new()
    bmesh.ops.create_uvsphere(bm_base, u_segments=32, v_segments=16, radius=base_radius)
    for v in bm_base.verts:
        # Flatten the sphere into a blobby base
        v.co.z *= 0.4
        # Add random jitter to make it look biological
        v.co += Vector((random.uniform(-0.2, 0.2), 
                        random.uniform(-0.2, 0.2), 
                        random.uniform(-0.1, 0.1)))
    
    bm_base.normal_update()
    apply_granular_texture(bm_base, strength=0.1)
    
    mesh_base = bpy.data.meshes.new("CoralBase")
    bm_base.to_mesh(mesh_base)
    bm_base.free()
    
    obj_base = bpy.data.objects.new("CoralBase", mesh_base)
    bpy.context.collection.objects.link(obj_base)
    obj_base.data.materials.append(coral_mat)

    # --- Create the Tube Assembly ---
    for i in range(num_tubes):
        # Circular arrangement around center, fanning outward
        angle = (2 * math.pi / num_tubes) * i
        start_dist = random.uniform(0.3, 0.7)
        start_x = math.cos(angle) * start_dist
        start_y = math.sin(angle) * start_dist
        start_pos = Vector((start_x, start_y, 0))
        
        # Tubes lean outward to create a splayed silhouette
        lean_factor = random.uniform(1.8, 3.2)
        height = random.uniform(min_height, max_height)
        end_pos = Vector((start_x * lean_factor, start_y * lean_factor, height))
        
        # Slight variation in thickness
        radius_var = tube_radius * random.uniform(0.85, 1.15)
        
        tube_mesh = generate_tube(start_pos, end_pos, radius_var)
        obj_tube = bpy.data.objects.new(f"Tube_{i}", tube_mesh)
        bpy.context.collection.objects.link(obj_tube)
        obj_tube.data.materials.append(coral_mat)

    # Final polishing: Smooth shading for all objects
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for poly in obj.data.polygons:
                poly.use_smooth = True

if __name__ == "__main__":
    generate_coral()
