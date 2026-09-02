import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_ginkgo_leaf():
    # --- Parameters ---
    stem_length = 5.0
    stem_radius = 0.06
    fan_radius = 3.2
    fan_angle_width = math.radians(120) # Wider fan for a more characteristic look
    segments_r = 16
    segments_theta = 60
    wave_freq = 7
    wave_amp = 0.25
    notch_depth = 1.4  # Deeper notch to create two distinct lobes
    notch_width = 0.35 # Wider notch for visibility
    
    # Materials: Pale yellow-green
    leaf_color = (0.55, 0.8, 0.25, 1.0) 
    mat = create_material("GinkgoMaterial", leaf_color)

    # --- Create the Blade ---
    bm = bmesh.new()
    verts = []
    half_width = fan_angle_width / 2
    
    for i in range(segments_r + 1):
        row = []
        r_norm = i / segments_r # 0 to 1
        for j in range(segments_theta + 1):
            t_norm = j / segments_theta 
            theta = -half_width + t_norm * fan_angle_width
            
            # Outer edge calculation
            # Base radius + scalloped wave
            edge_r = fan_radius + math.sin(theta * wave_freq * 2.5) * wave_amp
            
            # Central notch: a deep Gaussian-like dip at theta=0
            notch_factor = math.exp(-(theta**2) / (2 * notch_width**2))
            edge_r -= notch_factor * notch_depth
            
            current_r = r_norm * edge_r
            
            # Plane coordinates
            x = current_r * math.sin(theta)
            y = current_r * math.cos(theta)
            
            # Organic surface curvature: a gentle saddle/twist bend
            # Bends slightly along the length and twists at the edges
            z = (current_r * 0.2) * math.sin(theta * 1.2) + (r_norm**2 * 0.4)
            
            v = bm.verts.new(Vector((x, y, z)))
            row.append(v)
        verts.append(row)

    # Create faces for the blade surface
    for i in range(segments_r):
        for j in range(segments_theta):
            bm.faces.new((
                verts[i][j], 
                verts[i+1][j], 
                verts[i+1][j+1], 
                verts[i][j+1]
            ))

    blade_mesh = bpy.data.meshes.new("GinkgoBlade")
    bm.to_mesh(blade_mesh)
    bm.free()
    
    blade_obj = bpy.data.objects.new("GinkgoBlade", blade_mesh)
    bpy.context.collection.objects.link(blade_obj)
    blade_obj.data.materials.append(mat)

    # --- Create the Petiole (Stem) ---
    bm_stem = bmesh.new()
    stem_segments = 12
    
    stem_verts_bottom = []
    stem_verts_top = []
    
    for i in range(stem_segments):
        angle = (2 * math.pi / stem_segments) * i
        # Tapered: base is slightly thinner than the attachment point
        bx = math.cos(angle) * (stem_radius * 0.5)
        by = math.sin(angle) * (stem_radius * 0.5)
        stem_verts_bottom.append(bm_stem.verts.new(Vector((bx, by, -stem_length))))
        
        tx = math.cos(angle) * stem_radius
        ty = math.sin(angle) * stem_radius
        stem_verts_top.append(bm_stem.verts.new(Vector((tx, ty, 0))))

    for i in range(stem_segments):
        next_i = (i + 1) % stem_segments
        bm_stem.faces.new((
            stem_verts_bottom[i], 
            stem_verts_bottom[next_i], 
            stem_verts_top[next_i], 
            stem_verts_top[i]
        ))

    bm_stem.faces.new(stem_verts_bottom)
    bm_stem.faces.new(stem_verts_top)

    stem_mesh = bpy.data.meshes.new("GinkgoStem")
    bm_stem.to_mesh(stem_mesh)
    bm_stem.free()
    
    stem_obj = bpy.data.objects.new("GinkgoStem", stem_mesh)
    bpy.context.collection.objects.link(stem_obj)
    stem_obj.data.materials.append(mat)

    # --- Assembly and Pose ---
    blade_obj.parent = stem_obj
    
    # Set a natural three-quarter perspective pose
    stem_obj.rotation_euler = (math.radians(-10), math.radians(25), math.radians(15))
    
    # Smooth the look with Subdiv and Shading
    subsurf_blade = blade_obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf_blade.levels = 2
    
    subsurf_stem = stem_obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf_stem.levels = 1

    bpy.context.view_layer.objects.active = blade_obj
    bpy.ops.object.shade_smooth()
    bpy.context.view_layer.objects.active = stem_obj
    bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    clear_scene()
    create_ginkgo_leaf()
