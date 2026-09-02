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
    plume_max_radius = 0.25
    spikelet_count = 1500  # Increased for a denser plume
    spikelet_length_min = 0.1
    spikelet_length_max = 0.22
    
    # --- 1. Create the Main Stem ---
    # We use a mesh cylinder for the stem to ensure stability
    bm_stem = bmesh.new()
    bmesh.ops.create_cone(
        bm_stem, 
        cap_ends=True, 
        segments=16, 
        radius1=stem_radius * 1.1, 
        radius2=stem_radius * 0.9, 
        depth=stem_height
    )
    # Translate stem to start at origin
    bmesh.ops.translate(bm_stem, vec=Vector((0, 0, stem_height / 2)), verts=bm_stem.verts)
    
    stem_mesh = bpy.data.meshes.new("ReedStem")
    bm_stem.to_mesh(stem_mesh)
    bm_stem.free()
    stem_obj = bpy.data.objects.new("ReedStem", stem_mesh)
    bpy.context.collection.objects.link(stem_obj)

    # --- 2. Create the Plume (Inflorescence) using Curves ---
    # Using a single Curve object with many splines is more efficient than thousands of objects
    curve_data = bpy.data.curves.new("PlumeCurve", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 0.003 # Very thin for a feathery look
    curve_data.bevel_resolution = 2

    for _ in range(spikelet_count):
        # Distribution along the Z axis of the plume
        t = random.random()
        z_pos = plume_start_z + t * (plume_end_z - plume_start_z)
        
        # Conical tapering: radius decreases as z increases
        current_max_r = plume_max_radius * (1.0 - t * 0.8)
        
        angle = random.uniform(0, 2 * math.pi)
        dist_from_center = random.uniform(0, stem_radius * 1.5)
        start_x = math.cos(angle) * dist_from_center
        start_y = math.sin(angle) * dist_from_center
        
        # Direction: outward and upward
        dir_x = math.cos(angle) * random.uniform(0.7, 1.3)
        dir_y = math.sin(angle) * random.uniform(0.7, 1.3)
        dir_z = random.uniform(0.3, 0.8)
        direction = Vector((dir_x, dir_y, dir_z)).normalized()
        
        length = random.uniform(spikelet_length_min, spikelet_length_max)
        
        # Create a Bezier spline for each spikelet (3 points for organic curve)
        spline = curve_data.splines.new('BEZIER')
        spline.bezier_handle_left_type = 'AUTO'
        spline.bezier_handle_right_type = 'AUTO'
        
        # Set the number of points to 3 for a simple arc
        spline.points.add(2)
        
        p0 = spline.points[0]
        p1 = spline.points[1]
        p2 = spline.points[2]
        
        # Start point: on the stem/core
        p0.co = (start_x, start_y, z_pos)
        
        # Midpoint: half way along direction with some jitter
        mid_offset = direction * (length * 0.5)
        jitter = Vector((random.uniform(-0.03, 0.03), random.uniform(-0.03, 0.03), random.uniform(-0.03, 0.03)))
        p1.co = (start_x, start_y, z_pos) + mid_offset + jitter
        
        # End point: full length along direction
        end_offset = direction * length
        p2.co = (start_x, start_y, z_pos) + end_offset + jitter * 0.5

    plume_obj = bpy.data.objects.new("Plume", curve_data)
    bpy.context.collection.objects.link(plume_obj)

    # --- 3. Material and Coloring ---
    # Muted green: desaturated sage/olive tone
    muted_green = (0.32, 0.4, 0.25, 1.0) 
    mat = create_material("MutedGreen", muted_green)
    
    stem_obj.data.materials.append(mat)
    plume_obj.data.materials.append(mat)

if __name__ == "__main__":
    clear_scene()
    create_reed_inflorescence()
