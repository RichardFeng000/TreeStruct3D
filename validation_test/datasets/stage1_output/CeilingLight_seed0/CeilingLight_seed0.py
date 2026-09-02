import bpy
import bmesh
import math

def clear_scene():
    """Removes all objects from the current scene."""
    if bpy.context.active_object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, emission=0.0, roughness=0.5, metallic=0.0):
    """Creates a Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Create Principled BSDF node
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_bsdf.inputs['Base Color'].default_value = color
    node_bsdf.inputs['Roughness'].default_value = roughness
    node_bsdf.inputs['Metallic'].default_value = metallic
    
    if emission > 0:
        # In Blender 4.0+, Emission is a separate input in Principled BSDF
        # Strength and Color are often linked or separate
        node_bsdf.inputs['Emission Strength'].default_value = emission
        node_bsdf.inputs['Emission Color'].default_value = color

    # Create Output node
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Link them
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    
    return mat

def create_ceiling_light():
    # Parameters for a flush-mount light
    radius = 0.45
    height = 0.08
    resolution = 64
    bevel_width = 0.005
    
    # Create the mesh and object
    mesh = bpy.data.meshes.new("FlushMountLightMesh")
    obj = bpy.data.objects.new("FlushMountLight", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Create a cylinder
    bmesh.ops.create_cone(
        bm, 
        cap_ends=True, 
        segments=resolution, 
        radius1=radius, 
        radius2=radius, 
        depth=height
    )
    
    # Materials
    # Top: Diffuser (White, Matte)
    mat_diffuser = create_material("Mat_Diffuser", (1, 1, 1, 1), emission=0.0, roughness=0.6)
    # Bottom: Light Source (White, High Emission)
    mat_glow = create_material("Mat_Glow", (1, 1, 1, 1), emission=20.0, roughness=0.1)
    # Rim: Side profile (Light Grey, subtle metallic)
    mat_rim = create_material("Mat_Rim", (0.9, 0.9, 0.9, 1), emission=0.0, roughness=0.3, metallic=0.4)

    obj.data.materials.append(mat_diffuser) # Index 0
    obj.data.materials.append(mat_glow)     # Index 1
    obj.data.materials.append(mat_rim)      # Index 2

    # Assign materials based on normal direction
    for face in bm.faces:
        norm = face.normal
        if norm.z > 0.9:
            face.material_index = 0 # Top - Diffuser
        elif norm.z < -0.9:
            face.material_index = 1 # Bottom - Glow
        else:
            face.material_index = 2 # Sides - Rim

    bm.to_mesh(mesh)
    bm.free()

    # Set object active for operators
    bpy.context.view_layer.objects.active = obj
    
    # Apply modifiers
    # Bevel to avoid perfectly sharp edges on the rim
    bevel_mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel_mod.width = bevel_width
    bevel_mod.segments = 3
    bevel_mod.limit_method = 'ANGLE'
    bevel_mod.angle_limit = math.radians(30)

    # Subdivision surface for overall smoothness
    subsurf_mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf_mod.levels = 2
    subsurf_mod.render_levels = 2

    # Smooth shading
    bpy.ops.object.shade_smooth()
    
    # Weighted Normal modifier helps keep the flat faces actually flat after smoothing/beveling
    wn_mod = obj.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
    wn_mod.keep_sharp = True

def setup_scene():
    clear_scene()
    create_ceiling_light()

if __name__ == "__main__":
    setup_scene()
