import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_sage_green_material():
    """Creates a muted sage green material."""
    mat = bpy.data.materials.new(name="LichenMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    # Muted sage green: low saturation, medium-light value
    # RGB approx (0.45, 0.52, 0.38)
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.45, 0.52, 0.38, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.8 # Matte finish for organic growth
    return mat

def create_lichen_lobe(bm, center, angle_start, angle_end, radius, segments=15, rings=12):
    """
    Generates a single ruffled lobe of lichen geometry.
    """
    vertices = []
    for r_idx in range(rings):
        # Progress from 0 to 1
        t = r_idx / float(rings - 1)
        r_val = t * radius
        ring_verts = []
        
        # Organic jitter increases toward the edge
        jitter_scale = t * 0.25
        
        for s_idx in range(segments + 1):
            theta = angle_start + (s_idx / float(segments)) * (angle_end - angle_start)
            
            # Radial distortion for "leaf-like" edges
            curr_r = r_val + random.uniform(-jitter_scale, jitter_scale) * radius
            if curr_r < 0: curr_r = 0
            
            x = center.x + curr_r * math.cos(theta)
            y = center.y + curr_r * math.sin(theta)
            
            # Z height for organic ruffles/curls
            z = 0
            if r_idx > 0:
                # Base curvature (slightly cupped)
                curve = t**2 * 0.15
                # High-frequency ruffle effect combined with slow wave
                ruffle = math.sin(theta * 6 + t * 3) * t * 0.25
                curl = math.cos(theta * 3) * t * 0.1
                noise = random.uniform(-0.04, 0.04) * t
                z = curve + ruffle + curl + noise

            v = bm.verts.new(Vector((x, y, z)))
            ring_verts.append(v)
        vertices.append(ring_verts)

    for r_idx in range(rings - 1):
        for s_idx in range(segments):
            v1 = vertices[r_idx][s_idx]
            v2 = vertices[r_idx][s_idx + 1]
            v3 = vertices[r_idx + 1][s_idx + 1]
            v4 = vertices[r_idx + 1][s_idx]
            bm.faces.new((v1, v2, v3, v4))

def generate_lichen():
    # Initialize BMesh
    bm = bmesh.new()

    num_lobes = 30 # Increased density for a more "clustered" look
    base_radius = 0.6
    lobe_width_deg = 50
    
    for i in range(num_lobes):
        start_angle = math.radians(i * (360 / num_lobes))
        end_angle = start_angle + math.radians(lobe_width_deg)
        radius = base_radius * random.uniform(0.6, 1.5)
        center = Vector((0, 0, 0))
        
        create_lichen_lobe(
            bm, center, start_angle, end_angle, radius, 
            segments=random.randint(12, 18), 
            rings=random.randint(10, 15)
        )

    # Mesh conversion
    mesh = bpy.data.meshes.new("LichenMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("LichenGrowth", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Material assignment
    mat = create_sage_green_material()
    obj.data.materials.append(mat)
    
    # Modifiers for organic refinement
    # 1. Solidify: very thin to match leaf-like lobes
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.008
    solid.offset = 0
    
    # 2. Subdivision Surface for smoothness
    subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    # 3. Displace for microscopic organic texture
    tex = bpy.data.textures.new("LichenNoise", type='CLOUDS')
    tex.noise_scale = 0.05
    disp = obj.modifiers.new(name="Displace", type='DISPLACE')
    disp.texture = tex
    disp.strength = 0.02

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

def main():
    clear_scene()
    generate_lichen()

if __name__ == "__main__":
    main()
