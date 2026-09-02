import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clear all existing objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, alpha=1.0, transmission=0.0):
    """Create a Principled BSDF material with transparency and color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Create shader node
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Blender 4.0+ uses 'Base Color' and 'Transmission Weight' instead of 'Transmission'
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Alpha'].default_value = alpha
    if 'Transmission Weight' in node_principled.inputs:
        node_principled.inputs['Transmission Weight'].default_value = transmission
    elif 'Transmission' in node_principled.inputs:
        node_principled.inputs['Transmission'].default_value = transmission
        
    node_principled.inputs['Roughness'].default_value = 0.1
    
    # Connect nodes
    links = mat.node_tree.links
    links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    
    # Set blend mode for transparency in EEVEE
    mat.blend_method = 'BLEND' 
    return mat

def create_jellyfish_bell():
    """Create the lobed, translucent bell of the jellyfish."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0)
    bell = bpy.context.active_object
    bell.name = "JellyfishBell"

    # Flatten it to be more dome-like
    bell.scale = (1.2, 1.2, 0.8)
    bpy.ops.object.transform_apply(scale=True)

    bm = bmesh.new()
    bm.from_mesh(bell.data)
    
    # Remove vertices below a certain Z threshold to make it an open bell
    verts_to_delete = [v for v in bm.verts if v.co.z < -0.2]
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')

    # Create the lobed rim and subtle facets
    num_lobes = 8
    lobe_amplitude = 0.15
    frequency = num_lobes
    
    for v in bm.verts:
        angle = math.atan2(v.co.y, v.co.x)
        dist = (math.sin(angle * frequency) * lobe_amplitude)
        
        # Weight based on Z height: stronger at bottom rim
        weight = 1.0 - (v.co.z + 0.2) / 1.0
        if weight < 0: weight = 0
        
        v.co.x += math.cos(angle) * dist * weight
        v.co.y += math.sin(angle) * dist * weight
        
        # Add subtle faceted jitter to the surface
        jitter = 0.015
        v.co.x += random.uniform(-jitter, jitter)
        v.co.y += random.uniform(-jitter, jitter)
        v.co.z += random.uniform(-jitter, jitter)

    bm.to_mesh(bell.data)
    bm.free()

    # Subdiv for a mix of smooth and faceted look
    subsurf = bell.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1

    # Material: Pale pink-lavender, translucent
    mat_bell = create_material("BellMat", (0.9, 0.75, 0.85, 1.0), alpha=0.6, transmission=0.8)
    bell.data.materials.append(mat_bell)

    return bell

def create_tentacles():
    """Create numerous thin, wispy tentacles."""
    num_tentacles = 70
    segments_per_tentacle = 15
    
    # Material: Translucent pink thread
    mat_tentacle = create_material("TentacleMat", (1.0, 0.6, 0.7, 1.0), alpha=0.4)

    for i in range(num_tentacles):
        angle = random.uniform(0, 2 * math.pi)
        r = random.uniform(0.8, 1.1)
        start_pos = Vector((math.cos(angle) * r, math.sin(angle) * r, -0.2))

        curve_data = bpy.data.curves.new(name=f"TentacleCurve_{i}", type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.fill_mode = 'FULL'
        curve_data.bevel_depth = 0.006 
        curve_data.bevel_resolution = 3

        spline = curve_data.splines.new('BEZIER')
        spline.bezier_points.add(segments_per_tentacle - 1)

        curr_pos = start_pos.copy()
        for j in range(segments_per_tentacle):
            p = spline.bezier_points[j]
            # Tangle movement
            noise_offset = Vector((
                random.uniform(-0.5, 0.5),
                random.uniform(-0.5, 0.5),
                -random.uniform(0.3, 0.7)
            ))
            curr_pos += noise_offset
            p.co = curr_pos
            p.handle_left = p.co - (noise_offset * 0.5)
            p.handle_right = p.co + (noise_offset * 0.5)

        obj = bpy.data.objects.new(f"Tentacle_{i}", curve_data)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(mat_tentacle)

def create_oral_arm():
    """Create a single thicker, ribbon-like central oral arm."""
    # Material: Slightly more opaque pink
    mat_arm = create_material("OralArmMat", (1.0, 0.5, 0.6, 1.0), alpha=0.7)

    curve_data = bpy.data.curves.new(name="OralArmCurve", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 0.1  # Base thickness
    curve_data.bevel_resolution = 4

    spline = curve_data.splines.new('BEZIER')
    segments = 25
    spline.bezier_points.add(segments - 1)

    t_max = 6.0
    for i in range(segments):
        t = (i / segments) * t_max
        radius_spiral = 0.4 * math.exp(-t * 0.15)
        x = radius_spiral * math.cos(t * 2.0)
        y = radius_spiral * math.sin(t * 2.0)
        z = - (t * 0.8)
        
        p = spline.bezier_points[i]
        p.co = Vector((x, y, z))
        
        # Tapering thickness: point radius multiplies bevel_depth
        p.radius = 1.0 * (1.0 - (i / segments) * 0.8)
        
        p.handle_left = p.co - Vector((0.3, 0, 0.3))
        p.handle_right = p.co + Vector((0.3, 0, 0.3))

    obj = bpy.data.objects.new("OralArm", curve_data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat_arm)

def main():
    clear_scene()
    create_jellyfish_bell()
    create_tentacles()
    create_oral_arm()

if __name__ == "__main__":
    main()
