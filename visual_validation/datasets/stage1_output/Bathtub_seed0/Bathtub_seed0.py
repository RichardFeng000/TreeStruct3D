import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color=(1, 1, 1, 1), roughness=0.5):
    """Creates a simple Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Roughness'].default_value = roughness
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    links = mat.node_tree.links
    links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_bathtub():
    # Dimensions
    length = 2.0
    width = 1.0
    height = 0.7
    rim_width = 0.15
    bowl_depth = 0.5
    
    # Create the base shape (Tub Body)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1, depth=height, location=(0, 0, height/2))
    tub = bpy.context.active_object
    tub.name = "SoakingBathtub"
    
    # Scale to oval form
    tub.scale[0] = length / 2
    tub.scale[1] = width / 2
    bpy.ops.object.transform_apply(scale=True)
    
    # Apply Subdivision Surface for organic curve
    subsurf = tub.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf.levels = 3
    subsurf.render_levels = 3
    bpy.ops.object.modifier_apply(modifier="Subsurf")
    
    # Use BMesh to create the interior bowl and rim
    bm = bmesh.new()
    bm.from_mesh(tub.data)
    
    # Find top face (highest Z)
    top_face = None
    max_z = -float('inf')
    for f in bm.faces:
        center_z = sum(v.co.z for v in f.verts) / len(f.verts)
        if center_z > max_z:
            max_z = center_z
            top_face = f
            
    # Inset the top face to create the rim
    res = bmesh.ops.inset_individual(bm, faces=[top_face], thickness=rim_width)
    inner_face = res['faces'][0]
    
    # Extrude inner face downwards to create bowl
    extrusion_vec = Vector((0, 0, -bowl_depth))
    res = bmesh.ops.extrude_face_region(bm, geom=[inner_face])
    verts_to_move = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in verts_to_move:
        v.co += extrusion_vec
        
    # Smooth the bottom of the bowl by scaling it slightly and rounding
    bottom_face = None
    min_z = float('inf')
    for f in bm.faces:
        center_z = sum(v.co.z for v in f.verts) / len(f.verts)
        if center_z < min_z:
            min_z = center_z
            bottom_face = f
            
    if bottom_face:
        # Move bottom face slightly up and scale it to round the bowl
        for v in bottom_face.verts:
            v.co.z += 0.1 
            v.co.x *= 0.8
            v.co.y *= 0.8

    # Hammered Surface Logic: Jitter vertices on outer shell
    for v in bm.verts:
        dist_from_center = math.sqrt(v.co.x**2 + v.co.y**2)
        # Outer shell verts are those further from center and not too high (excluding the rim top)
        if dist_from_center > (width / 3) and v.co.z < (height - 0.1):
            norm = v.normal.copy()
            jitter_amount = random.uniform(-0.015, 0.015)
            v.co += norm * jitter_amount

    bm.to_mesh(tub.data)
    bm.free()
    
    # Smooth shading
    bpy.ops.object.shade_smooth()
    
    # Create the Platform Base (Oval disk)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1, depth=0.05, location=(0, 0, 0.025))
    base = bpy.context.active_object
    base.name = "TubBase"
    base.scale[0] = (length / 2) * 1.08
    base.scale[1] = (width / 2) * 1.08
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.shade_smooth()

    # Materials
    mat_glossy = create_material("WhiteGlossy", color=(1, 1, 1, 1), roughness=0.05)
    mat_hammered = create_material("WhiteHammered", color=(1, 1, 1, 1), roughness=0.6)
    
    # Assign materials to tub (Slot 0: Outer/Rim, Slot 1: Inner Bowl)
    tub.data.materials.append(mat_hammered) 
    tub.data.materials.append(mat_glossy)   
    base.data.materials.append(mat_hammered)

    # Precisely assign the inner bowl to the glossy material using BMesh again
    bm = bmesh.new()
    bm.from_mesh(tub.data)
    for f in bm.faces:
        # Use normal and position to distinguish interior from exterior
        # Inner faces usually point slightly upward or are located inside the tub volume
        center = f.calc_center_median()
        if (f.normal.z > 0.2) or (center.z < height * 0.7 and abs(center.x) < length/3 and abs(center.y) < width/3):
            f.material_index = 1
        else:
            f.material_index = 0
    bm.to_mesh(tub.data)
    bm.free()

if __name__ == "__main__":
    clear_scene()
    create_bathtub()
