import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default scene of all objects."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_boulder_material():
    """Creates a warm reddish-brown earth-toned material compatible with Blender 4.0+."""
    mat = bpy.data.materials.new(name="BoulderMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Reddish-brown color typical of weathered sandstone
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    # In Blender 4.0+, Principled BSDF inputs changed. 
    # We use the names 'Base Color' and 'Roughness'.
    node_principled.inputs['Base Color'].default_value = (0.45, 0.23, 0.12, 1.0) 
    node_principled.inputs['Roughness'].default_value = 0.9
    
    # To avoid KeyError with Specular/IOR across versions, we set IOR if it exists
    if 'IOR' in node_principled.inputs:
        node_principled.inputs['IOR'].default_value = 1.5

    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    links = mat.node_tree.links
    links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    
    return mat

def generate_boulder():
    # 1. Create a base mesh (IcoSphere)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=2.5)
    obj = bpy.context.active_object
    obj.name = "LargeBoulder"

    # 2. Shape the broad, flat-topped irregular silhouette using BMesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    for v in bm.verts:
        # Flatten overall profile (Low profile / Wide)
        v.co.z *= 0.35
        
        # Irregular wide footprint
        angle = math.atan2(v.co.y, v.co.x)
        dist_mod = 1.0 + 0.2 * math.sin(angle * 3) + 0.15 * math.cos(angle * 5)
        v.co.x *= dist_mod * random.uniform(0.9, 1.1)
        v.co.y *= (1.3 / dist_mod) * random.uniform(0.9, 1.1)

        # Explicit Flat-top logic: Push top vertices toward a plateau
        if v.co.z > 0.2:
            # Squash the crown to create that sedimentary rock appearance
            v.co.z = 0.2 + (v.co.z - 0.2) * 0.2

    bm.to_mesh(obj.data)
    bm.free()

    # 3. Use Subdivision Surface modifier first to prevent jagged/spiky displacement
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2

    # 4. Apply Displacement layers for granular and eroded textures
    # Layer A: Coarse Erosion (Large shapes)
    tex_coarse = bpy.data.textures.new("CoarseErosion", type='CLOUDS')
    tex_coarse.noise_scale = 1.8
    disp_coarse = obj.modifiers.new(name="Disp_Coarse", type='DISPLACE')
    disp_coarse.texture = tex_coarse
    disp_coarse.strength = 0.3

    # Layer B: Sedimentary Grain (Medium scale)
    tex_sediment = bpy.data.textures.new("SedimentDetail", type='CLOUDS')
    tex_sediment.noise_scale = 0.5
    disp_sediment = obj.modifiers.new(name="Disp_Sediment", type='DISPLACE')
    disp_sediment.texture = tex_sediment
    disp_sediment.strength = 0.12

    # Layer C: Fine Pitting (High frequency)
    tex_fine = bpy.data.textures.new("FinePitting", type='CLOUDS')
    tex_fine.noise_scale = 0.06
    disp_fine = obj.modifiers.new(name="Disp_Fine", type='DISPLACE')
    disp_fine.texture = tex_fine
    disp_fine.strength = 0.05

    # Apply all modifiers to lock the geometry into a mesh
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # We must apply them one by one in order
    modifier_names = ["Subdiv", "Disp_Coarse", "Disp_Sediment", "Disp_Fine"]
    for name in modifier_names:
        if name in obj.modifiers:
            bpy.ops.object.modifier_apply(modifier=name)

    # Final pass for micro-grit via BMesh (subtle high-frequency jitter)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for v in bm.verts:
        v.co += Vector((random.uniform(-0.02, 0.02), 
                        random.uniform(-0.02, 0.02), 
                        random.uniform(-0.02, 0.02)))
    bm.to_mesh(obj.data)
    bm.free()

    # Material assignment
    mat = create_boulder_material()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

if __name__ == "__main__":
    clear_scene()
    generate_boulder()
