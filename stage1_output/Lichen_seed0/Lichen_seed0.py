import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene objects."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_sage_green_material():
    """Creates a muted, distinct sage green material."""
    mat = bpy.data.materials.new(name="LichenMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Muted Sage Green: (R, G, B, A)
        bsdf.inputs['Base Color'].default_value = (0.38, 0.45, 0.32, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.85
        bsdf.inputs['Specular IOR Level'].default_value = 0.2
    return mat

def create_organic_lobe(bm, center_v, angle, length, width_factor):
    """
    Generates a single organic lobe radiating from the center vertex.
    """
    segments = 8
    rings = 6
    
    # Store vertices for this lobe to build faces
    verts = []
    
    for r in range(rings):
        t = r / (rings - 1) # Normalized distance along the lobe [0, 1]
        ring_verts = []
        
        dist = t * length
        # Lobe width increases then slightly tapers or stays wide at edges
        current_width = t * 0.25 * width_factor
        
        for s in range(segments + 1):
            # Offset from the main radial line of the lobe
            offset_perc = (s / segments) - 0.5
            theta = angle + offset_perc * current_width
            
            # Organic noise and ruffles
            # Use sine waves for undulating edges
            ruffle = math.sin(t * 4.0 + theta * 3.0) * 0.1 * t
            jitter_x = random.uniform(-0.02, 0.02) * t
            jitter_y = random.uniform(-0.02, 0.02) * t
            
            x = (dist + ruffle) * math.cos(theta) + jitter_x
            y = (dist + ruffle) * math.sin(theta) + jitter_y
            
            # Z height: Low rosette shape. Base is flat, edges curl up/down
            # The 't' factor ensures it stays attached to the center
            z = (t**2 * 0.15) + math.cos(theta * 5.0 + t * 3.0) * 0.1 * t
            
            v = bm.verts.new(Vector((x, y, z)))
            ring_verts.append(v)
        verts.append(ring_verts)

    # Create faces for the lobe
    for r in range(rings - 1):
        for s in range(segments):
            try:
                bm.faces.new((verts[r][s], verts[r][s+1], verts[r+1][s+1], verts[r+1][s]))
            except ValueError:
                # Face might already exist or have degenerate edges
                pass

def generate_lichen():
    # Initialize BMesh
    bm = bmesh.new()

    # Central base point
    center_v = bm.verts.new(Vector((0, 0, 0)))

    # Create a small central disk for stability and visual density
    base_res = 12
    base_ring = []
    for s in range(base_res):
        theta = (s / base_res) * 2 * math.pi
        v = bm.verts.new(Vector((0.1 * math.cos(theta), 0.1 * math.sin(theta), 0)))
        base_ring.append(v)
    
    for s in range(base_res):
        try:
            bm.faces.new((center_v, base_ring[(s+1)%base_res], base_ring[s]))
        except ValueError:
            pass

    # Radiating lobes to form a low rosette structure
    num_lobes = 50
    for i in range(num_lobes):
        angle = (i / num_lobes) * 2 * math.pi + random.uniform(-0.1, 0.1)
        length = random.uniform(0.7, 1.4)
        width = random.uniform(0.8, 1.6)
        create_organic_lobe(bm, center_v, angle, length, width)

    # Mesh conversion
    mesh = bpy.data.meshes.new("LichenMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("LichenGrowth", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Material assignment
    mat = create_sage_green_material()
    obj.data.materials.append(mat)
    
    # Modifiers for organic detail
    # 1. Solidify: gives the lobes leaf-like thickness
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.01
    
    # 2. Subdivision Surface: smooths the jagged procedural edges
    subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3
    
    # 3. Displace: adds micro-surface organic variation (lichen texture)
    tex = bpy.data.textures.new("LichenNoise", type='CLOUDS')
    tex.noise_scale = 0.12
    disp = obj.modifiers.new(name="Displace", type='DISPLACE')
    disp.texture = tex
    disp.strength = 0.03

    # Set as active and smooth shading
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

def main():
    clear_scene()
    generate_lichen()

if __name__ == "__main__":
    main()
