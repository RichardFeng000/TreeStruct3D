import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material():
    mat = bpy.data.materials.new(name="CoralMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Sandy beige color: RGB ~ (0.85, 0.78, 0.65)
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_principled.inputs['Base Color'].default_value = (0.85, 0.78, 0.65, 1.0)
    node_principled.inputs['Roughness'].default_value = 0.9
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_palmate_branch(bm, start_pos, direction, length=3.0, width_base=0.2, thickness=0.1):
    """Creates a broad, flat blade-like branch that fans out."""
    segments = 15
    res_width = 8  # Resolution across the wide part
    seg_len = length / segments
    
    # Coordinate system for the "blade"
    up_global = Vector((0, 0, 1))
    if abs(direction.dot(up_global)) > 0.9:
        up_global = Vector((0, 1, 0))
    
    # Right axis is the width direction of the blade
    right_axis = direction.cross(up_global).normalized()
    # Local 'flat' axis (the thin part)
    thin_axis = right_axis.cross(direction).normalized()
    
    prev_ring = []
    curr_pos = start_pos.copy()
    curr_dir = direction.copy()

    for s in range(segments + 1):
        # Width grows significantly (palmate effect)
        growth = 1.0 + (s / segments)**1.5 * 4.0
        current_width = width_base * growth
        current_thick = thickness * (1.0 + (s/segments)*0.5)
        
        # Create a flattened elliptical ring for this segment
        ring = []
        for i in range(res_width):
            angle = (2 * math.pi * i) / res_width
            # Flattened ellipse: wide on right_axis, thin on thin_axis
            off = (right_axis * math.cos(angle) * current_width + 
                   thin_axis * math.sin(angle) * current_thick) * 0.5
            v = bm.verts.new(curr_pos + off)
            ring.append(v)
        
        # Connect previous ring to this one with faces
        if prev_ring:
            for i in range(res_width):
                v1 = prev_ring[i]
                v2 = prev_ring[(i + 1) % res_width]
                v3 = ring[(i + 1) % res_width]
                v4 = ring[i]
                bm.faces.new((v1, v2, v3, v4))
        
        # Add a cap face for the start (first segment)
        if s == 0:
            try:
                bm.faces.new(ring)
            except ValueError: pass

        prev_ring = ring
        
        # Organic curving of the branch path
        curr_pos += curr_dir * seg_len
        jitter = Vector((random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)))
        curr_dir = (curr_dir + jitter).normalized()

    # Cap the end
    try:
        bm.faces.new(prev_ring)
    except ValueError: pass

def build_elkhorn():
    clear_scene()
    
    mesh = bpy.data.meshes.new("ElkhornCoral")
    obj = bpy.data.objects.new("ElkhornCoral", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Base structure (central mound)
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=6, radius=0.5)
    for v in bm.verts:
        v.co.z *= 0.6 # Flatten the base sphere into a lump

    # Create several broad fan branches radiating from center
    num_branches = 7
    for i in range(num_branches):
        angle = (2 * math.pi * i / num_branches)
        pos = Vector((math.cos(angle)*0.3, math.sin(angle)*0.3, 0.1))
        # Direct branches outwards and upwards
        dir_vec = Vector((math.cos(angle), math.sin(angle), 0.7)).normalized()
        create_palmate_branch(bm, pos, dir_vec, length=random.uniform(2.5, 3.5), width_base=0.4)

    # Finalize mesh
    bm.to_mesh(mesh)
    bm.free()
    
    # Add material
    mat = create_material()
    obj.data.materials.append(mat)
    
    # Modifiers for organic look and granular texture
    subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 2
    
    displace = obj.modifiers.new(name="GranularTexture", type='DISPLACE')
    tex = bpy.data.textures.new("CoralNoise", type='CLOUDS')
    tex.noise_scale = 0.05
    displace.texture = tex
    displace.strength = 0.08
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    build_elkhorn()
