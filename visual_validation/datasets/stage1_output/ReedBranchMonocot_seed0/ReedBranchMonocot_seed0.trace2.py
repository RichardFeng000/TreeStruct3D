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
    return mat

def create_reed_inflorescence():
    # Parameters for the reed structure
    stem_radius = 0.015
    stem_height = 2.5
    plume_start_z = 1.4
    plume_end_z = 2.6
    plume_max_radius = 0.3
    spikelet_count = 2500 # Dense plume
    spikelet_length_min = 0.12
    spikelet_length_max = 0.28
    spikelet_thickness = 0.002

    # --- 1. Create the Main Stem ---
    bm_stem = bmesh.new()
    bmesh.ops.create_cone(
        bm_stem, 
        cap_ends=True, 
        segments=16, 
        radius1=stem_radius * 1.1, 
        radius2=stem_radius * 0.9, 
        depth=stem_height
    )
    # Translate stem to start at origin (bottom)
    bmesh.ops.translate(bm_stem, vec=Vector((0, 0, stem_height / 2)), verts=bm_stem.verts)
    
    stem_mesh = bpy.data.meshes.new("ReedStem")
    bm_stem.to_mesh(stem_mesh)
    bm_stem.free()
    stem_obj = bpy.data.objects.new("ReedStem", stem_mesh)
    bpy.context.collection.objects.link(stem_obj)

    # --- 2. Create the Plume (Inflorescence) ---
    # To ensure stability and high density, we use one BMesh for all spikelets.
    # Each spikelet is modeled as a very thin elongated cone/cylinder.
    bm_plume = bmesh.new()
    
    for _ in range(spikelet_count):
        # Distribution along the Z axis of the plume (conical)
        t = random.random()
        z_pos = plume_start_z + t * (plume_end_z - plume_start_z)
        
        # Conical tapering: radius decreases as z increases
        current_max_r = plume_max_radius * (1.0 - t * 0.7)
        
        angle = random.uniform(0, 2 * math.pi)
        # Distribute start points near the stem core
        dist_from_center = random.uniform(0, stem_radius * 2)
        start_x = math.cos(angle) * dist_from_center
        start_y = math.sin(angle) * dist_from_center
        
        # Direction: outward and upward (conical spray)
        dir_x = math.cos(angle) * random.uniform(0.5, 1.5)
        dir_y = math.sin(angle) * random.uniform(0.5, 1.5)
        dir_z = random.uniform(0.4, 1.0)
        direction = Vector((dir_x, dir_y, dir_z)).normalized()
        
        length = random.uniform(spikelet_length_min, spikelet_length_max)
        
        # Create a thin cone for each spikelet to give it "real geometry" volume
        # Instead of bmesh.ops which is slow in loops, we manually create the vertices
        
        # Base circle (bottom of spikelet)
        base_verts = []
        segments = 4 # Low segments per spikelet because they are extremely thin
        for i in range(segments):
            seg_angle = (2 * math.pi / segments) * i
            # Perpendicular to direction vector for the base circle
            # Create a simple coordinate frame
            up = Vector((0, 0, 1)) if abs(direction.z) < 0.9 else Vector((0, 1, 0))
            right = direction.cross(up).normalized()
            forward = direction.cross(right).normalized()
            
            offset = (right * math.cos(seg_angle) + forward * math.sin(seg_angle)) * spikelet_thickness
            v = bm_plume.verts.new(Vector((start_x, start_y, z_pos)) + offset)
            base_verts.append(v)
        
        # Tip vertex
        tip_pos = Vector((start_x, start_y, z_pos)) + direction * length
        tip_v = bm_plume.verts.new(tip_pos)
        
        # Create faces for the cone sides
        for i in range(segments):
            v1 = base_verts[i]
            v2 = base_verts[(i + 1) % segments]
            bm_plume.faces.new((v1, v2, tip_v))

    # Finalize Plume Mesh
    plume_mesh = bpy.data.meshes.new("PlumeMesh")
    bm_plume.to_mesh(plume_mesh)
    bm_plume.free()
    plume_obj = bpy.data.objects.new("Plume", plume_mesh)
    bpy.context.collection.objects.link(plume_obj)

    # --- 3. Material and Coloring ---
    # Muted green: desaturated sage/olive tone
    muted_green = (0.3, 0.4, 0.25, 1.0) 
    mat = create_material("MutedGreen", muted_green)
    
    stem_obj.data.materials.append(mat)
    plume_obj.data.materials.append(mat)

if __name__ == "__main__":
    clear_scene()
    create_reed_inflorescence()
