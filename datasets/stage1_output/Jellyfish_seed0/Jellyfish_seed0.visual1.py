import bpy
import bmesh
import math
import random
from mathutils import Vector, Color

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, alpha=1.0, transmission=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Alpha'].default_value = alpha
    if 'Transmission Weight' in node_principled.inputs:
        node_principled.inputs['Transmission Weight'].default_value = transmission
    elif 'Transmission' in node_principled.inputs:
        node_principled.inputs['Transmission'].default_value = transmission
        
    node_principled.inputs['Roughness'].default_value = 0.1
    links = mat.node_tree.links
    links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    mat.blend_method = 'BLEND' 
    return mat

def create_jellyfish_bell():
    # Lower resolution to help with "faceted" look
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=1.0)
    bell = bpy.context.active_object
    bell.name = "JellyfishBell"

    # Flatten for dome shape
    bell.scale = (1.3, 1.3, 0.7)
    bpy.ops.object.transform_apply(scale=True)

    bm = bmesh.new()
    bm.from_mesh(bell.data)
    
    # Open the bell
    verts_to_delete = [v for v in bm.verts if v.co.z < -0.1]
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')

    # Pronounced lobed rim and facets
    num_lobes = 8
    lobe_amplitude = 0.25 # Increased amplitude
    for v in bm.verts:
        angle = math.atan2(v.co.y, v.co.x)
        dist = (math.sin(angle * num_lobes) * lobe_amplitude)
        weight = 1.0 - (v.co.z + 0.1) / 0.8 if (v.co.z + 0.1) < 0.8 else 0
        v.co.x += math.cos(angle) * dist * weight
        v.co.y += math.sin(angle) * dist * weight
        
        # Add faceted jitter
        jitter = 0.025
        v.co.x += random.uniform(-jitter, jitter)
        v.co.y += random.uniform(-jitter, jitter)
        v.co.z += random.uniform(-jitter, jitter)

    bm.to_mesh(bell.data)
    bm.free()

    # Ensure it looks faceted by disabling smooth shading and not using Subdiv
    bpy.ops.object.shade_flat() 

    mat_bell = create_material("BellMat", (0.9, 0.75, 0.85, 1.0), alpha=0.6, transmission=0.8)
    bell.data.materials.append(mat_bell)
    return bell

def create_tentacles():
    num_tentacles = 80
    segments_per_tentacle = 20
    mat_tentacle = create_material("TentacleMat", (1.0, 0.6, 0.7, 1.0), alpha=0.3)

    for i in range(num_tentacles):
        angle = random.uniform(0, 2 * math.pi)
        r = random.uniform(0.9, 1.2)
        start_pos = Vector((math.cos(angle) * r, math.sin(angle) * r, -0.1))

        curve_data = bpy.data.curves.new(name=f"TentacleCurve_{i}", type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.fill_mode = 'FULL'
        curve_data.bevel_depth = 0.005 
        curve_data.bevel_resolution = 2

        spline = curve_data.splines.new('BEZIER')
        spline.bezier_points.add(segments_per_tentacle - 1)

        curr_pos = start_pos.copy()
        for j in range(segments_per_tentacle):
            p = spline.bezier_points[j]
            noise_offset = Vector((random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.6), -random.uniform(0.4, 1.0)))
            curr_pos += noise_offset
            p.co = curr_pos
            p.handle_left = p.co - (noise_offset * 0.3)
            p.handle_right = p.co + (noise_offset * 0.3)

        obj = bpy.data.objects.new(f"Tentacle_{i}", curve_data)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(mat_tentacle)

def create_oral_arm():
    # Create a ribbon-like mesh instead of a tube
    mat_arm = create_material("OralArmMat", (1.0, 0.5, 0.6, 1.0), alpha=0.7, transmission=0.3)
    
    mesh = bpy.data.meshes.new("OralArmMesh")
    obj = bpy.data.objects.new("OralArm", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    segments = 40
    ribbon_width = 0.15
    
    verts_left = []
    verts_right = []
    
    for i in range(segments):
        t = (i / segments) * 7.0
        radius = 0.4 * math.exp(-t * 0.2)
        cx = radius * math.cos(t * 2.5)
        cy = radius * math.sin(t * 2.5)
        cz = - (t * 1.0)
        center = Vector((cx, cy, cz))
        
        # Calculate tangent for width orientation
        next_t = ((i + 1) / segments) * 7.0
        next_radius = 0.4 * math.exp(-next_t * 0.2)
        next_center = Vector((next_radius * math.cos(next_t * 2.5), next_radius * math.sin(next_t * 2.5), -(next_t * 1.0)))
        tangent = (next_center - center).normalized()
        
        # Width vector perpendicular to tangent and roughly vertical/radial
        perp = tangent.cross(Vector((0, 0, 1))).normalized()
        
        width_scale = ribbon_width * (1.0 - (i / segments) * 0.7)
        v_l = bm.verts.new(center + perp * width_scale * 0.5)
        v_r = bm.verts.new(center - perp * width_scale * 0.5)
        verts_left.append(v_l)
        verts_right.append(v_r)

    for i in range(segments - 1):
        bm.faces.new((verts_left[i], verts_left[i+1], verts_right[i+1], verts_right[i]))

    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(mat_arm)

def main():
    clear_scene()
    create_jellyfish_bell()
    create_tentacles()
    create_oral_arm()

if __name__ == "__main__":
    main()
