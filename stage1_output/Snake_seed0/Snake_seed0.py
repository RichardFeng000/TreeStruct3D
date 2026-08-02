import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears default scene objects."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a matte olive-green material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = color
    # Deep matte surface: high roughness, low specular
    bsdf.inputs['Roughness'].default_value = 0.8
    
    output = nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def get_snake_path(t):
    """
    S-curve pose: 
    Head elevated at upper left (-x, +z)
    Body sweeping downward to bottom right (+x, -z/0)
    Using t from 0 (head) to 1 (tail).
    """
    # Clamp t to avoid domain errors with powers
    t = max(0.0, min(1.0, t))
    # X: Left to Right
    x = -5.0 + 10.0 * t
    # Y: Sinuous curve (S-shape)
    y = 3.0 * math.sin(math.pi * 2.0 * t)
    # Z: Elevated head, descending body. Using quadratic to avoid complex numbers.
    z = 4.0 * (1.0 - t)**2
    return Vector((x, y, z))

def get_snake_tangent(t):
    """Approximate tangent vector at point t."""
    delta = 0.001
    # Use a small offset but keep within bounds for the path function
    p1 = get_snake_path(t)
    p2 = get_snake_path(t + delta if t < 1.0 else t - delta)
    return (p2 - p1).normalized()

def generate_snake():
    clear_scene()
    
    # Parameters
    segments = 150
    vertices_per_ring = 20
    head_radius = 0.6
    tail_radius = 0.05
    flattening_factor = 0.7  # Width is smaller than height for bilateral flattening
    
    mesh = bpy.data.meshes.new("Snake")
    obj = bpy.data.objects.new("Snake", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    prev_ring = []
    all_rings = [] 
    
    for i in range(segments + 1):
        t = i / segments
        pos = get_snake_path(t)
        tangent = get_snake_tangent(t)
        
        # Calculate a coordinate frame (Frenet-Serret approximation)
        up_ref = Vector((0, 0, 1))
        if abs(tangent.dot(up_ref)) > 0.9:
            up_ref = Vector((0, 1, 0))
            
        bitangent = tangent.cross(up_ref).normalized()
        normal = bitangent.cross(tangent).normalized()
        
        # Taper from head to tail
        # Use a smooth curve for tapering: thicker at head, thinning out
        radius = head_radius * (1.0 - 0.95 * (t**0.8))
        if t > 0.9: # Extra sharp taper at the very end
            radius *= (1.0 - (t-0.9)*10) if t < 1.0 else 0.02

        # Bilateral flattening: Ellipse dimensions
        width_rad = radius * flattening_factor
        height_rad = radius
        
        current_ring = []
        for v_idx in range(vertices_per_ring):
            angle = (2 * math.pi / vertices_per_ring) * v_idx
            # Elliptical cross section: width on bitangent, height on normal
            offset = (bitangent * math.cos(angle) * width_rad + 
                      normal * math.sin(angle) * height_rad)
            
            vert = bm.verts.new(pos + offset)
            current_ring.append(vert)
        
        # Connect rings
        if prev_ring:
            for v_idx in range(vertices_per_ring):
                v1 = prev_ring[v_idx]
                v2 = prev_ring[(v_idx + 1) % vertices_per_ring]
                v3 = current_ring[(v_idx + 1) % vertices_per_ring]
                v4 = current_ring[v_idx]
                bm.faces.new((v1, v2, v3, v4))
        
        prev_ring = current_ring
        all_rings.append(current_ring)

    # Close tail with a single vertex (taper to point)
    tail_pos = get_snake_path(1.0)
    tail_tip = bm.verts.new(tail_pos)
    last_ring = all_rings[-1]
    for v_idx in range(vertices_per_ring):
        v1 = last_ring[v_idx]
        v2 = last_ring[(v_idx + 1) % vertices_per_ring]
        bm.faces.new((v1, v2, tail_tip))

    # Head Construction: Blunt rounded snout
    head_base = all_rings[0]
    
    # Offset for the nose tip (moving opposite to the tangent at t=0)
    t_nose = -0.05 
    pos_nose = get_snake_path(t_nose)
    tangent_nose = get_snake_tangent(t_nose)
    up_ref_n = Vector((0, 0, 1))
    if abs(tangent_nose.dot(up_ref_n)) > 0.9:
        up_ref_n = Vector((0, 1, 0))
    bitangent_n = tangent_nose.cross(up_ref_n).normalized()
    normal_n = bitangent_n.cross(tangent_nose).normalized()

    # Create the nose tip ring (slightly more blunt/flattened than body)
    nose_ring = []
    for v_idx in range(vertices_per_ring):
        angle = (2 * math.pi / vertices_per_ring) * v_idx
        offset = (bitangent_n * math.cos(angle) * head_radius * 0.9 + 
                  normal_n * math.sin(angle) * head_radius * 0.7)
        nose_ring.append(bm.verts.new(pos_nose + offset))

    # Bridge base of head to snout ring
    for v_idx in range(vertices_per_ring):
        v1 = head_base[v_idx]
        v2 = head_base[(v_idx + 1) % vertices_per_ring]
        v3 = nose_ring[(v_idx + 1) % vertices_per_ring]
        v4 = nose_ring[v_idx]
        bm.faces.new((v1, v2, v3, v4))

    # Cap the snout with a center vertex for a rounded blunt look
    snout_center = bm.verts.new(pos_nose)
    for v_idx in range(vertices_per_ring):
        v1 = nose_ring[v_idx]
        v2 = nose_ring[(v_idx + 1) % vertices_per_ring]
        bm.faces.new((v1, v2, snout_center))

    # Finalize mesh
    bm.to_mesh(mesh)
    bm.free()

    # Smoothing and Modifiers
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    for poly in mesh.polygons:
        poly.use_smooth = True

    # Material: Deep Olive Green (Dark, muted green)
    olive_green_color = (0.12, 0.22, 0.06, 1.0)
    mat = create_material("OliveGreen", olive_green_color)
    obj.data.materials.append(mat)

if __name__ == "__main__":
    generate_snake()
