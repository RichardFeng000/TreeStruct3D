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
        # Color is sandy brown with olive-green tones
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.98 # Very matte
        bsdf.inputs['Specular IOR Level'].default_value = 0.1
    return mat

def create_leather_coral():
    # Parameters for a fleshier, broader look
    radius = 3.0
    lobes_count = 7
    base_thickness = 0.6
    spire_height = 1.8
    
    mesh = bpy.data.meshes.new("LeatherCoral")
    obj = bpy.data.objects.new("LeatherCoral", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # 1. Generate the Base Shape (Broad fleshy lobes)
    radial_res = 160 # Higher res for better texture resolution
    ring_res = 80
    verts_map = []
    
    for r_idx in range(ring_res + 1):
        r_factor = r_idx / ring_res
        current_ring = []
        for s_idx in range(radial_res):
            theta = (s_idx / radial_res) * 2 * math.pi
            
            # Lobe shape: wider and more fleshy than the previous version
            lobe_variation = (
                math.sin(lobes_count * theta) * 0.4 + 
                math.cos(lobes_count * 0.5 * theta) * 0.1
            )
            # Broaden the lobes: use a different growth curve for radius
            current_radius = radius * r_factor * (1 + lobe_variation * math.pow(r_factor, 0.7))
            
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

    # Extrude for thickness
    bm.faces.ensure_lookup_table()
    all_faces = bm.faces[:]
    res = bmesh.ops.extrude_face_region(bm, geom=all_faces)
    extruded_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    
    for v in extruded_verts:
        dist = math.sqrt(v.co.x**2 + v.co.y**2)
        thickness = base_thickness * (1 - (dist / radius) * 0.5)
        v.co.z -= max(0.2, thickness)

    # Apply macro-curvature and intense granular "polyps"
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        dist = math.sqrt(v.co.x**2 + v.co.y**2)
        is_top = v.co.z >= -0.1 
        
        if is_top:
            # Fleshy dome shape
            dome = (1 - (dist/radius)**2) * 0.8 if dist <= radius else 0
            
            # Intense high-frequency noise for granular polyps
            grain = (
                math.sin(v.co.x * 60) * math.cos(v.co.y * 60) * 0.12 +
                math.sin(v.co.x * 150) * math.sin(v.co.y * 150) * 0.06 +
                (random.uniform(-1, 1) * 0.08) # Random jitter for roughness
            )
            v.co.z += dome + grain
        else:
            # Bottom surface slightly rough but flatter
            v.co.z += random.uniform(-0.05, 0.05)

    # 2. Central Spire
    spire_segments = 48
    spire_rings_count = 30
    spire_radius_base = 0.6
    spire_radius_top = 0.2
    
    spire_verts = []
    for h_idx in range(spire_rings_count):
        h_factor = h_idx / (spire_rings_count - 1)
        z = h_factor * spire_height
        r = spire_radius_base + (spire_radius_top - spire_radius_base) * h_factor
        off_x = math.sin(h_factor * 2.0) * 0.3
        off_y = math.cos(h_factor * 1.8) * 0.3
        
        ring = []
        for s_idx in range(spire_segments):
            theta = (s_idx / spire_segments) * 2 * math.pi
            v = bm.verts.new(Vector((math.cos(theta)*r + off_x, math.sin(theta)*r + off_y, z)))
            ring.append(v)
        spire_verts.append(ring)

    for h in range(spire_rings_count - 1):
        for s in range(spire_segments):
            s_next = (s + 1) % spire_segments
            bm.faces.new((spire_verts[h][s], spire_verts[h][s_next], spire_verts[h+1][s_next], spire_verts[h+1][s]))

    top_center = bm.verts.new(Vector((
        math.sin(2.0) * 0.3, 
        math.cos(1.8) * 0.3, 
        spire_height)))
    last_ring = spire_verts[-1]
    for s in range(spire_segments):
        s_next = (s + 1) % spire_segments
        bm.faces.new((last_ring[s], last_ring[s_next], top_center))

    # Texture the spire with granular polyps
    for v in bm.verts:
        if v.co.z > 0.2: 
            v.co += Vector((random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)))

    bm.to_mesh(mesh)
    bm.free()

    # No Subdiv modifier to avoid smoothing out the granular detail we just added manually
    
    # Material: Sandy brown with olive-green tones (R=0.45, G=0.42, B=0.2)
    coral_mat = create_material("CoralMat", (0.48, 0.43, 0.22, 1.0))
    obj.data.materials.append(coral_mat)

    return obj

def main():
    clear_scene()
    coral = create_leather_coral()
    coral.location = (0, 0, 0)
    bpy.context.view_layer.objects.active = coral
    # Use shade smooth but the geometry is now noisy enough that it will still look rough
    bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    main()
