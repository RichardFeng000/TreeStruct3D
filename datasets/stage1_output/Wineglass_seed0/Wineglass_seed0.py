import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clear default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_glass_material():
    """Create a brownish-gray semi-transparent glass material."""
    mat = bpy.data.materials.new(name="WineGlassMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()

    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Brownish-gray color
    node_bsdf.inputs['Base Color'].default_value = (0.3, 0.25, 0.2, 1.0)
    node_bsdf.inputs['Transmission Weight'].default_value = 0.9
    node_bsdf.inputs['Roughness'].default_value = 0.05
    node_bsdf.inputs['IOR'].default_value = 1.5
    
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_bowl():
    """Create a wide rounded wine glass bowl."""
    # Profile: (radius, height)
    profile = [
        (0.0, 0.0),      # Bottom center
        (0.2, 0.1),      # Transition to stem
        (0.8, 0.7),      # Lower belly
        (1.1, 1.5),      # Widest point
        (0.9, 2.8),      # Tapering up
        (0.85, 3.0),     # Rim edge
    ]
    
    segments = 64
    bm = bmesh.new()
    
    all_slices = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        current_slice = []
        for r, h in profile:
            current_slice.append(bm.verts.new((r * cos_a, r * sin_a, h)))
        all_slices.append(current_slice)

    for i in range(segments):
        s1 = all_slices[i]
        s2 = all_slices[(i + 1) % segments]
        for j in range(len(profile) - 1):
            bm.faces.new((s1[j], s2[j], s2[j+1], s1[j+1]))

    return bm

def create_stem():
    """Create the thin vertical stem."""
    radius = 0.08
    height = 2.5
    segments = 32
    bm = bmesh.new()
    
    b_verts = [bm.verts.new((radius * math.cos(2*math.pi*i/segments), radius * math.sin(2*math.pi*i/segments), 0)) for i in range(segments)]
    t_verts = [bm.verts.new((radius * math.cos(2*math.pi*i/segments), radius * math.sin(2*math.pi*i/segments), height)) for i in range(segments)]

    for i in range(segments):
        bm.faces.new((b_verts[i], b_verts[(i + 1) % segments], t_verts[(i + 1) % segments], t_verts[i]))
    
    bm.faces.new(b_verts)
    bm.faces.new(t_verts)
    return bm

def create_stacked_base():
    """Create a clearly stacked disc base structure."""
    # Radius, height, z_offset
    discs = [
        (1.5, 0.15, 0.0),     # Bottom
        (1.2, 0.12, 0.15),    # Mid
        (0.9, 0.1, 0.27),     # Top
    ]
    
    bm = bmesh.new()
    segments = 64
    
    for r, h, offset in discs:
        b_verts = [bm.verts.new((r * math.cos(2*math.pi*i/segments), r * math.sin(2*math.pi*i/segments), offset)) for i in range(segments)]
        t_verts = [bm.verts.new((r * math.cos(2*math.pi*i/segments), r * math.sin(2*math.pi*i/segments), offset + h)) for i in range(segments)]
            
        for i in range(segments):
            bm.faces.new((b_verts[i], b_verts[(i+1)%segments], t_verts[(i+1)%segments], t_verts[i]))
        
        bm.faces.new(t_verts)
        if offset == 0:
            bm.faces.new(b_verts)
        
    return bm

def main():
    clear_scene()
    glass_mat = create_glass_material()
    
    # Base
    base_bm = create_stacked_base()
    base_mesh = bpy.data.meshes.new("BaseMesh")
    base_bm.to_mesh(base_mesh)
    base_bm.free()
    base_obj = bpy.data.objects.new("Base", base_mesh)
    bpy.context.collection.objects.link(base_obj)

    # Stem
    stem_z_start = 0.37
    stem_bm = create_stem()
    stem_mesh = bpy.data.meshes.new("StemMesh")
    stem_bm.to_mesh(stem_mesh)
    stem_bm.free()
    stem_obj = bpy.data.objects.new("Stem", stem_mesh)
    bpy.context.collection.objects.link(stem_obj)
    stem_obj.location.z = stem_z_start

    # Bowl
    bowl_bm = create_bowl()
    bowl_mesh = bpy.data.meshes.new("BowlMesh")
    bowl_bm.to_mesh(bowl_mesh)
    bowl_bm.free()
    bowl_obj = bpy.data.objects.new("Bowl", bowl_mesh)
    bpy.context.collection.objects.link(bowl_obj)
    bowl_obj.location.z = stem_z_start + 2.5

    # Solidify the bowl to give it thickness
    mod_solid = bowl_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    mod_solid.thickness = 0.03
    bpy.context.view_layer.objects.active = bowl_obj
    bpy.ops.object.modifier_apply(modifier="Solidify")

    # Join all
    bpy.ops.object.select_all(action='DESELECT')
    base_obj.select_set(True)
    stem_obj.select_set(True)
    bowl_obj.select_set(True)
    bpy.context.view_layer.objects.active = bowl_obj
    bpy.ops.object.join()
    
    final_obj = bpy.context.active_object
    final_obj.name = "WineGlass"
    final_obj.data.materials.append(glass_mat)
    bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    main()
