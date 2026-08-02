import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clear default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Create a basic material with a specific base color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        # Lower roughness for a slightly more organic, natural look
        bsdf.inputs['Roughness'].default_value = 0.8
    return mat

def create_reed_inflorescence():
    # Parameters for the reed structure
    stem_radius = 0.012
    stem_height = 2.5
    plume_start_z = 1.5
    plume_end_z = 2.6
    # Max length of spikelets at the base of the plume to define width
    max_spikelet_len = 0.35
    min_spikelet_len = 0.08
    spikelet_count = 4000 # Increased density for "dense plume"
    spikelet_thickness = 0.0015

    # --- 1. Create the Main Stem ---
    bm_stem = bmesh.new()
    bmesh.ops.create_cone(
        bm_stem, 
        cap_ends=True, 
        segments=12, 
        radius1=stem_radius * 1.1, 
        radius2=stem_radius * 0.8, 
        depth=stem_height
    )
    bmesh.ops.translate(bm_stem, vec=Vector((0, 0, stem_height / 2)), verts=bm_stem.verts)
    
    stem_mesh = bpy.data.meshes.new("ReedStem")
    bm_stem.to_mesh(stem_mesh)
    bm_stem.free()
    stem_obj = bpy.data.objects.new("ReedStem", stem_mesh)
    bpy.context.collection.objects.link(stem_obj)

    # --- 2. Create the Plume (Inflorescence) ---
    bm_plume = bmesh.new()
    
    for _ in range(spikelet_count):
        # Distribution along Z: denser at bottom/middle
        t = random.random()
        z_pos = plume_start_z + t * (plume_end_z - plume_start_z)
        
        # Linear taper for the "conical" shape: length decreases as z increases
        current_max_len = max_spikelet_len * (1.0 - t * 0.8) + min_spikelet_len * (t * 0.8)
        length = random.uniform(current_max_len * 0.6, current_max_len * 1.1)
        
        angle = random.uniform(0, 2 * math.pi)
        # Start points tightly packed around the stem
        dist_from_center = random.uniform(0, stem_radius * 1.5)
        start_x = math.cos(angle) * dist_from_center
        start_y = math.sin(angle) * dist_from_center
        
        # Direction: radiate outwards with a strong upward bias
        # The "featheriness" comes from the random variation in direction and length
        dir_x = math.cos(angle) * random.uniform(0.4, 1.2)
        dir_y = math.sin(angle) * random.uniform(0.4, 1.2)
        # Upward bias increases slightly towards the top to keep it "compact"
        dir_z = random.uniform(0.3, 0.9) + (t * 0.2) 
        direction = Vector((dir_x, dir_y, dir_z)).normalized()
        
        # Create a very thin cone for each spikelet
        base_verts = []
        segments = 3 # Triangle base is enough for such thin elements
        for i in range(segments):
            seg_angle = (2 * math.pi / segments) * i
            up = Vector((0, 0, 1)) if abs(direction.z) < 0.9 else Vector((0, 1, 0))
            right = direction.cross(up).normalized()
            forward = direction.cross(right).normalized()
            
            offset = (right * math.cos(seg_angle) + forward * math.sin(seg_angle)) * spikelet_thickness
            v = bm_plume.verts.new(Vector((start_x, start_y, z_pos)) + offset)
            base_verts.append(v)
        
        tip_pos = Vector((start_x, start_y, z_pos)) + direction * length
        tip_v = bm_plume.verts.new(tip_pos)
        
        for i in range(segments):
            v1 = base_verts[i]
            v2 = base_verts[(i + 1) % segments]
            bm_plume.faces.new((v1, v2, tip_v))

    plume_mesh = bpy.data.meshes.new("PlumeMesh")
    bm_plume.to_mesh(plume_mesh)
    bm_plume.free()
    plume_obj = bpy.data.objects.new("Plume", plume_mesh)
    bpy.context.collection.objects.link(plume_obj)

    # --- 3. Material and Coloring ---
    # Muted, soft green (desaturated olive/sage)
    muted_green = (0.35, 0.42, 0.28, 1.0) 
    mat = create_material("MutedGreen", muted_green)
    
    stem_obj.data.materials.append(mat)
    plume_obj.data.materials.append(mat)

if __name__ == "__main__":
    clear_scene()
    create_reed_inflorescence()
