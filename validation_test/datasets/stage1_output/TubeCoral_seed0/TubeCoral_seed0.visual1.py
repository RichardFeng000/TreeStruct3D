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
    """Creates a material with sandy beige, olive green, and pink blush."""
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
    
    # High scale for more granular color variation
    noise.inputs['Scale'].default_value = 15.0
    noise.inputs['Detail'].default_value = 15.0
    
    # Color palette: Sandy Beige, Olive Green, Pink Blush
    elements = color_ramp.color_ramp.elements
    elements[0].position = 0.0
    elements[0].color = (0.88, 0.78, 0.65, 1) # Warm Sandy Beige
    
    if len(elements) < 3:
        el1 = elements.new(0.4)
        el1.color = (0.35, 0.38, 0.25, 1) # Muted Olive Green
    else:
        elements[1].position = 0.4
        elements[1].color = (0.35, 0.38, 0.25, 1)

    elements[2].position = 0.75
    elements[2].color = (0.95, 0.6, 0.7, 1) # Subtle Pink Blush
    
    links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    bsdf.inputs['Roughness'].default_value = 0.85
    return mat

def apply_granular_bumps(bm, strength=0.1):
    """Creates high-frequency organic polyp bumps."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        # Use purely random values to avoid the ridged/banded look of sine waves
        # Only apply to a percentage of vertices to create 'bumps' rather than uniform noise
        if random.random() > 0.6:
            bump_amount = random.uniform(0, strength) * 1.5
            v.co += v.normal * bump_amount

def generate_tube(start_pos, end_pos, radius):
    """Generates a thick organic tube with granular detail."""
    bm = bmesh.new()
    
    # High resolution is essential to avoid the 'columnar' look and allow for bumps
    segments = 48
    rings = 60
    depth = (end_pos - start_pos).length
    
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=radius, radius2=radius*0.7, depth=depth, segments=segments)
    
    # Align tube to positions
    direction = (end_pos - start_pos).normalized()
    up = Vector((0, 0, 1))
    rot_quat = up.rotation_difference(direction)
    rot_matrix = rot_quat.to_matrix().to_4x4()
    
    for v in bm.verts:
        v.co.z += depth * 0.5
        # Add a slight organic curve/bend to the tube's spine
        dist_from_base = v.co.z / depth
        bend = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 0)) * (dist_from_base**2)
        v.co += bend
        v.co = rot_matrix @ v.co + start_pos

    # Further subdivide to ensure granularity
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1)
    
    bm.normal_update()
    apply_granular_bumps(bm, strength=0.12)
    
    mesh = bpy.data.meshes.new("TubeMesh")
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def generate_coral():
    clear_scene()
    coral_mat = create_coral_material()
    
    num_tubes = 10
    base_radius = 1.4
    min_height = 4.5
    max_height = 7.5
    tube_radius = 0.5

    # --- Organic Base ---
    bm_base = bmesh.new()
    bmesh.ops.create_uvsphere(bm_base, u_segments=32, v_segments=16, radius=base_radius)
    for v in bm_base.verts:
        v.co.z *= 0.35
        # More chaotic jitter for the base
        v.co += Vector((random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), random.uniform(-0.1, 0.1)))
    
    bm_base.normal_update()
    apply_granular_bumps(bm_base, strength=0.15)
    
    mesh_base = bpy.data.meshes.new("CoralBase")
    bm_base.to_mesh(mesh_base)
    bm_base.free()
    
    obj_base = bpy.data.objects.new("CoralBase", mesh_base)
    bpy.context.collection.objects.link(obj_base)
    obj_base.data.materials.append(coral_mat)

    # --- Tube Assembly ---
    for i in range(num_tubes):
        angle = (2 * math.pi / num_tubes) * i
        start_dist = random.uniform(0.4, 0.8)
        start_x = math.cos(angle) * start_dist
        start_y = math.sin(angle) * start_dist
        start_pos = Vector((start_x, start_y, 0))
        
        # Splayed silhouette: Tubes lean outward
        lean_factor = random.uniform(2.0, 3.5)
        height = random.uniform(min_height, max_height)
        end_pos = Vector((start_x * lean_factor, start_y * lean_factor, height))
        
        radius_var = tube_radius * random.uniform(0.8, 1.2)
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
