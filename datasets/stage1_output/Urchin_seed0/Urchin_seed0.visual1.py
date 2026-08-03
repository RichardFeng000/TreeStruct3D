import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Removes all existing objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_core_material():
    """Creates a dark purple material for the core."""
    mat = bpy.data.materials.new(name="UrchinCore")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.05, 0.01, 0.1, 1.0) # Very dark purple
    return mat

def create_spine_material():
    """Creates a material with a distance-based gradient for the spines."""
    mat = bpy.data.materials.new(name="UrchinSpines")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    for node in nodes:
        nodes.remove(node)

    # Node setup for gradient based on distance from origin
    tex_coord = nodes.new('ShaderNodeTexCoord')
    vec_math = nodes.new('ShaderNodeVectorMath')
    vec_math.operation = 'LENGTH'
    
    color_ramp = nodes.new('ShaderNodeValToRGB')
    # Define colors: Dark purple at base -> Reddish-purple at tip
    elements = color_ramp.color_ramp.elements
    elements[0].position = 0.0
    elements[0].color = (0.1, 0.02, 0.15, 1.0) # Base
    elements[1].position = 0.6 # Transition point
    elements[1].color = (0.5, 0.05, 0.3, 1.0)  # Tip

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    
    links.new(tex_coord.outputs['Object'], vec_math.inputs[0])
    links.new(vec_math.outputs['Value'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])

    # Output node
    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    return mat

def create_sea_urchin():
    # Parameters
    body_radius = 1.0
    spine_count = 800 # Increased density
    min_spine_len = 2.2
    max_spine_len = 3.8
    spine_base_rad = 0.05
    spine_tip_rad = 0.008
    spine_segments = 10
    ring_pts = 8 # Smoother rings

    # Materials
    core_mat = create_core_material()
    spine_mat = create_spine_material()

    # --- Central Body ---
    bpy.ops.mesh.primitive_uv_sphere_add(radius=body_radius, segments=32, ring_count=16)
    body = bpy.context.active_object
    body.name = "UrchinBody"
    body.scale[2] = 0.8 # Slightly oblate
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    body.data.materials.append(core_mat)

    # --- Spines (Unified Mesh) ---
    spine_mesh = bpy.data.meshes.new("SpineMesh")
    spine_obj = bpy.data.objects.new("UrchinSpines", spine_mesh)
    bpy.context.collection.objects.link(spine_obj)
    spine_obj.data.materials.append(spine_mat)

    bm = bmesh.new()

    for i in range(spine_count):
        # Fibonacci Sphere distribution
        phi = math.acos(1 - 2 * (i + 0.5) / spine_count)
        theta = math.pi * (1 + 5**0.5) * (i + 0.5)

        # Position accounting for body scaling
        x = body_radius * math.sin(phi) * math.cos(theta)
        y = body_radius * math.sin(phi) * math.sin(theta)
        z = (body_radius * 0.8) * math.cos(phi)
        
        start_pos = Vector((x, y, z))
        direction = start_pos.normalized()
        
        length = random.uniform(min_spine_len, max_spine_len)
        base_rad = spine_base_rad * random.uniform(0.8, 1.2)
        
        # Create the cone for each spine
        spine_verts = []
        for seg in range(spine_segments + 1):
            t = seg / spine_segments
            current_rad = base_rad * (1.0 - t) + spine_tip_rad * t
            dist = t * length
            
            ring_verts = []
            # Construct orthonormal basis for the ring
            ref = Vector((0, 1, 0)) if abs(direction.x) < 0.9 else Vector((1, 0, 0))
            v_perp1 = direction.cross(ref).normalized()
            v_perp2 = direction.cross(v_perp1).normalized()
            
            for r in range(ring_pts):
                angle = (2 * math.pi / ring_pts) * r
                offset = (v_perp1 * math.cos(angle) + v_perp2 * math.sin(angle)) * current_rad
                p = start_pos + (direction * dist) + offset
                ring_verts.append(bm.verts.new(p))
            spine_verts.append(ring_verts)

        # Connect faces between rings
        for seg in range(spine_segments):
            curr_ring = spine_verts[seg]
            next_ring = spine_verts[seg+1]
            for r in range(ring_pts):
                v1, v2 = curr_ring[r], curr_ring[(r + 1) % ring_pts]
                v3, v4 = next_ring[(r + 1) % ring_pts], next_ring[r]
                bm.faces.new((v1, v2, v3, v4))

        # Cap the base (though mostly hidden by body)
        bm.faces.new(spine_verts[0])

    bm.to_mesh(spine_mesh)
    bm.free()

if __name__ == "__main__":
    clear_scene()
    create_sea_urchin()
