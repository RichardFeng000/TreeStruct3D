import bpy
import bmesh
import math
import random
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
        bsdf.inputs['Roughness'].default_value = 0.95
    return mat

def create_leather_coral():
    # Parameters
    radius = 2.8
    lobes_count = 8
    base_thickness = 0.5
    spire_height = 1.6
    
    mesh = bpy.data.meshes.new("LeatherCoral")
    obj = bpy.data.objects.new("LeatherCoral", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # 1. Generate the Base Shape (Broad fleshy lobes)
    # Using high resolution to allow for granular texture via vertex manipulation
    radial_res = 120 
    ring_res = 60
    verts_map = []
    
    for r_idx in range(ring_res + 1):
        r_factor = r_idx / ring_res
        current_ring = []
        for s_idx in range(radial_res):
            theta = (s_idx / radial_res) * 2 * math.pi
            
            # Lobe shape: mix of sine waves for irregular organic feel
            lobe_variation = (
                math.sin(lobes_count * theta) * 0.35 + 
                math.sin(lobes_count * 2.1 * theta) * 0.15 + 
                math.cos(3 * theta) * 0.1
            )
            # Lobe effect is stronger at the edges
            current_radius = radius * r_factor * (1 + lobe_variation * (r_factor**1.2))
            
            x = math.cos(theta) * current_radius
            y = math.sin(theta) * current_radius
            z = 0
            
            v = bm.verts.new(Vector((x, y, z)))
            current_ring.append(v)
        verts_map.append(current_ring)

    # Create faces for the top surface
    for r in range(ring_res):
        for s in range(radial_res):
            s_next = (s + 1) % radial_res
            bm.faces.new((verts_map[r][s], verts_map[r][s_next], verts_map[r+1][s_next], verts_map[r+1][s]))

    # Extrude for thickness (Fleshy volume)
    bm.faces.ensure_lookup_table()
    all_faces = bm.faces[:]
    res = bmesh.ops.extrude_face_region(bm, geom=all_faces)
    extruded_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    
    # Adjust bottom vertices to create thickness and organic base
    for v in extruded_verts:
        dist = math.sqrt(v.co.x**2 + v.co.y**2)
        # Thicker center, thinner edges
        thickness = base_thickness * (1 - (dist / radius) * 0.6)
        v.co.z -= max(0.15, thickness)

    # Apply macro-curvature and micro-granular "polyps"
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        dist = math.sqrt(v.co.x**2 + v.co.y**2)
        is_top = v.co.z >= -0.1 # Approximate top surface
        
        if is_top:
            # Fleshy dome shape
            dome = (1 - (dist/radius)**2) * 0.6 if dist <= radius else 0
            
            # High-frequency granular noise for polyps
            grain = (
                math.sin(v.co.x * 35) * math.cos(v.co.y * 35) * 0.05 +
                math.sin(v.co.x * 80) * math.sin(v.co.y * 80) * 0.02
            )
            # Add some randomness to break the pattern
            grain += (random.random() - 0.5) * 0.03
            
            v.co.z += dome + grain
        else:
            # Bottom surface roughness
            grain_bottom = math.sin(v.co.x * 20) * math.cos(v.co.y * 20) * 0.04
            v.co.z += grain_bottom

    # 2. Central Spire
    spire_segments = 32
    spire_rings_count = 25
    spire_radius_base = 0.4
    spire_radius_top = 0.15
    
    spire_verts = []
    for h_idx in range(spire_rings_count):
        h_factor = h_idx / (spire_rings_count - 1)
        z = h_factor * spire_height
        r = spire_radius_base + (spire_radius_top - spire_radius_base) * h_factor
        # Organic lean and sway
        off_x = math.sin(h_factor * 2.0) * 0.2
        off_y = math.cos(h_factor * 1.8) * 0.2
        
        ring = []
        for s_idx in range(spire_segments):
            theta = (s_idx / spire_segments) * 2 * math.pi
            v = bm.verts.new(Vector((math.cos(theta)*r + off_x, math.sin(theta)*r + off_y, z)))
            ring.append(v)
        spire_verts.append(ring)

    # Create spire faces
    for h in range(spire_rings_count - 1):
        for s in range(spire_segments):
            s_next = (s + 1) % spire_segments
            bm.faces.new((spire_verts[h][s], spire_verts[h][s_next], spire_verts[h+1][s_next], spire_verts[h+1][s]))

    # Close top of spire
    top_center = bm.verts.new(Vector((
        math.sin(1 * 2.0) * 0.2, 
        math.cos(1 * 1.8) * 0.2, 
        spire_height)))
    last_ring = spire_verts[-1]
    for s in range(spire_segments):
        s_next = (s + 1) % spire_segments
        bm.faces.new((last_ring[s], last_ring[s_next], top_center))

    # Texture the spire with granular polyps
    for v in bm.verts:
        if v.co.z > 0.2: # Target only the vertical structure
            v.co += Vector((
                random.uniform(-0.03, 0.03), 
                random.uniform(-0.03, 0.03), 
                random.uniform(-0.03, 0.03)))

    bm.to_mesh(mesh)
    bm.free()

    # Modifiers for organic polish
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1
    subsurf.render_levels = 2
    
    # Material: Sandy brown with olive-green tones
    # Warm sandy brown base (R=0.6, G=0.5, B=0.3)
    coral_mat = create_material("CoralMat", (0.65, 0.52, 0.3, 1.0))
    obj.data.materials.append(coral_mat)

    return obj

def main():
    clear_scene()
    coral = create_leather_coral()
    coral.location = (0, 0, 0)
    bpy.context.view_layer.objects.active = coral
    bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    main()
