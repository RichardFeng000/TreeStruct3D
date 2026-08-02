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
        bsdf.inputs['Roughness'].default_value = 0.6
    return mat

def create_ginkgo_leaf():
    # --- Parameters ---
    stem_length = 5.0
    stem_radius = 0.08
    fan_radius = 3.5
    fan_angle_width = math.radians(130) # Wide fan shape
    segments_r = 20
    segments_theta = 80
    
    # Edge detail parameters
    wave_freq = 9
    wave_amp = 0.35        # Increased for more visible scalloping
    notch_depth = 1.8      # Increased to create distinct lobes
    notch_width = 0.4
    
    # Material: Pale yellow-green
    leaf_color = (0.6, 0.85, 0.3, 1.0) 
    mat = create_material("GinkgoMaterial", leaf_color)

    # --- Create the Blade ---
    bm = bmesh.new()
    verts = []
    half_width = fan_angle_width / 2
    
    for i in range(segments_r + 1):
        row = []
        r_norm = i / segments_r # 0 to 1 (stem end to outer edge)
        for j in range(segments_theta + 1):
            t_norm = j / segments_theta 
            theta = -half_width + t_norm * fan_angle_width
            
            # Outer edge: Scalloping + Central Notch
            scallop = math.sin(theta * wave_freq) * wave_amp
            notch = math.exp(-(theta**2) / (2 * notch_width**2)) * notch_depth
            edge_r = fan_radius + scallop - notch
            
            current_r = r_norm * edge_r
            
            # Plane coordinates
            x = current_r * math.sin(theta)
            y = current_r * math.cos(theta)
            
            # Organic curvature: gentle cup shape with some asymmetric twist
            # z increases as we move away from center, creating a concave/convex feel
            z_base = r_norm**2 * 0.6 
            z_fold = (r_norm * 0.3) * math.cos(theta * 0.5)
            z_variation = 0.1 * math.sin(theta * 3) * r_norm
            z = z_base + z_fold + z_variation
            
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
        # Tapered: thinner at the bottom
        bx = math.cos(angle) * (stem_radius * 0.6)
        by = math.sin(angle) * (stem_radius * 0.6)
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
    
    # Three-quarter perspective pose
    stem_obj.rotation_euler = (math.radians(-15), math.radians(30), math.radians(20))
    
    # Smoothing and refinement
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
