import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_coconut_material():
    """Creates a high-contrast procedural gradient material for the coconut husk."""
    mat = bpy.data.materials.new(name="CoconutHusk")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for node in nodes:
        nodes.remove(node)

    output = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.1  # Higher gloss for "drinking coconut" look
    
    tex_coord = nodes.new(type='ShaderNodeTexCoord')
    sep_xyz = nodes.new(type='ShaderNodeSeparateXYZ')
    color_ramp = nodes.new(type='ShaderNodeValToRGB')
    
    # Stronger gradient for visibility: Pale Yellow-Green -> Bright Green -> Dark Forest Green
    elements = color_ramp.color_ramp.elements
    elements[0].position = 0.0
    elements[0].color = (0.85, 1.0, 0.7, 1.0) # Light white-green base
    
    mid = elements.new(0.5)
    mid.color = (0.1, 0.6, 0.1, 1.0) # Fresh bright green mid
    
    elements[2].position = 1.0
    elements[2].color = (0.02, 0.3, 0.05, 1.0) # Darker green top

    links.new(tex_coord.outputs['Generated'], sep_xyz.inputs['Vector'])
    links.new(sep_xyz.outputs['Z'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat

def create_stalk_material():
    """Creates a pale green material for the stalk."""
    mat = bpy.data.materials.new(name="CoconutStalk")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = (0.7, 0.9, 0.6, 1.0) 
    bsdf.inputs['Roughness'].default_value = 0.3
    return mat

def create_coconut():
    # 1. Main Body
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=64, ring_count=32)
    obj = bpy.context.active_object
    obj.name = "CoconutBody"

    # Oval shape: Taller and wider at base
    obj.scale = (1.0, 1.0, 1.4)
    bpy.ops.object.transform_apply(scale=True)

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # Apply Taper: Narrower at top, wider at bottom
    for v in bm.verts:
        # Z goes from -1.4 to 1.4 (approx) after apply scale
        z_norm = (v.co.z + 1.4) / 2.8
        taper = 0.7 + (z_norm * 0.3) # More wide at bottom, narrower top? 
        # Wait, prompt says "wider at the base and tapering slightly toward the top"
        # So if z is high, scale should be smaller.
        taper_top = 1.0 - (v.co.z * 0.15) 
        if v.co.z > 0:
            v.co.x *= taper_top
            v.co.y *= taper_top

    # Crown Details: Raised Ring and Flower Scar
    # Identify crown vertices (Z near the top pole ~1.4)
    crown_threshold = 1.2
    ring_start = 1.1
    ring_end = 1.3

    for v in bm.verts:
        # Create Raised Ring
        if ring_start < v.co.z < ring_end:
            dir = Vector((v.co.x, v.co.y, 0)).normalized()
            v.co += dir * 0.06 # Push out to make it a visible lip

        # Create Three-Part Flower Scar (Indentations)
        if v.co.z > crown_threshold:
            # Calculate angle in XY plane
            angle = math.atan2(v.co.y, v.co.x)
            # Map angle to 3 zones of 120 degrees each
            normalized_angle = (angle + math.pi) / (2 * math.pi) # 0 to 1
            # Create three distinct dips using a sine wave on the angle
            dip = math.cos(normalized_angle * 3 * 2 * math.pi)
            if dip > 0.7: # Only indent at peaks of the cosine wave
                v.co.z -= 0.12 # Push inward deeply enough to be visible
                # Pull toward center slightly
                dir_to_center = Vector((-v.co.x, -v.co.y, 0)).normalized()
                v.co += dir_to_center * 0.05

    bm.to_mesh(obj.data)
    bm.free()

    bpy.ops.object.shade_smooth()
    subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 2

    # 2. The Stalk
    # Position it at the very top of the tapered oval
    stalk_z = 1.35 
    bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=0.25, location=(0, 0, stalk_z + 0.12))
    stalk = bpy.context.active_object
    stalk.name = "CoconutStalk"
    
    # Taper the top of the stalk
    sbm = bmesh.new()
    sbm.from_mesh(stalk.data)
    for v in sbm.verts:
        if v.co.z > 0: # Top part (local coords relative to cylinder center)
            v.co.x *= 0.6
            v.co.y *= 0.6
    sbm.to_mesh(stalk.data)
    sbm.free()
    
    bpy.ops.object.shade_smooth()

    # Materials
    husk_mat = create_coconut_material()
    stalk_mat = create_stalk_material()
    obj.data.materials.append(husk_mat)
    stalk.data.materials.append(stalk_mat)
    stalk.parent = obj

if __name__ == "__main__":
    clear_scene()
    create_coconut()
