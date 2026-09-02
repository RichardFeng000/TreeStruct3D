import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clear all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_nautilus_material():
    """Creates a procedural material for brown-and-cream wavy stripes."""
    mat = bpy.data.materials.new(name="NautilusMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default nodes
    for node in nodes:
        nodes.remove(node)

    # Create nodes
    tex_coord = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeMapping')
    noise = nodes.new('ShaderNodeTexNoise')
    wave = nodes.new('ShaderNodeTexWave')
    color_ramp = nodes.new('ShaderNodeValToRGB')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    output = nodes.new('ShaderNodeOutputMaterial')

    # Configure Noise for "waviness"
    noise.inputs['Scale'].default_value = 5.0
    noise.inputs['Detail'].default_value = 2.0

    # Configure Wave for stripes (radiating along the shell length/U)
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs['Scale'].default_value = 8.0
    wave.inputs['Distortion'].default_value = 15.0 # Creates the wavy look

    # Configure Color Ramp (Brown and Cream)
    color_ramp.color_ramp.elements[0].position = 0.45
    color_ramp.color_ramp.elements[0].color = (0.95, 0.92, 0.85, 1.0) # Cream
    color_ramp.color_ramp.elements[1].position = 0.55
    color_ramp.color_ramp.elements[1].color = (0.35, 0.18, 0.12, 1.0) # Brown

    # Set material properties
    bsdf.inputs['Roughness'].default_value = 0.4

    # Linking
    links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], wave.inputs['Vector'])
    links.new(wave.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat

def create_nautilus():
    """Procedurally generates a nautilus shell geometry with UVs."""
    # Logarithmic spiral parameters: r = a * exp(b * theta)
    a = 0.25
    b = 0.16  # Growth factor for organic feel
    turns = 3.8
    theta_max = turns * 2 * math.pi
    segments = 500 # Higher resolution along length
    ring_res = 40   # Resolution of the cross-section

    radius_factor = 0.3  # Width relative to radius from center

    bm = bmesh.new()
    
    # Enable UV layer
    uv_layer = bm.loops.layers.uv.new("UVMap")

    prev_ring = []
    
    for i in range(segments + 1):
        theta = (i / segments) * theta_max
        u_coord = theta / theta_max # Normalized along length for textures
        
        dist = a * math.exp(b * theta)
        cx = dist * math.cos(theta)
        cy = dist * math.sin(theta)
        cz = 0
        center = Vector((cx, cy, cz))

        # Tangent for orientation
        tx = a * b * math.exp(b * theta) * math.cos(theta) - a * math.exp(b * theta) * math.sin(theta)
        ty = a * b * math.exp(b * theta) * math.sin(theta) + a * math.exp(b * theta) * math.cos(theta)
        tz = 0
        tangent = Vector((tx, ty, tz)).normalized()

        up = Vector((0, 0, 1))
        right = tangent.cross(up).normalized()
        side = up.cross(right).normalized()

        # Growth of the tube radius
        current_radius = dist * radius_factor
        if i < segments * 0.2: # Taper start (central chamber)
            current_radius *= (i / (segments * 0.2)) + 0.1

        current_ring = []
        for j in range(ring_res):
            angle = (j / ring_res) * 2 * math.pi
            v_coord = angle / (2 * math.pi) # Normalized around circumference
            
            # Elliptical cross-section for nautilus shape
            vx = center + right * math.cos(angle) * current_radius * 1.2
            vy = center + up * math.sin(angle) * current_radius * 0.8
            
            vert = bm.verts.new(vx + vy - center)
            current_ring.append((vert, u_coord, v_coord))

        if prev_ring:
            for j in range(ring_res):
                v1, u1, w1 = prev_ring[j]
                v2, u2, w2 = prev_ring[(j + 1) % ring_res]
                u_next2, v_next2 = current_ring[(j + 1) % ring_res][0], current_ring[(j+1)%ring_res][1:] # This is slightly wrong, need values
                # Just getting indices for face creation:
                v_curr1 = current_ring[j][0]
                v_curr2 = current_ring[(j + 1) % ring_res][0]
                face = bm.faces.new((v1, v2, v_curr2, v_curr1))
                
                # Assign UVs to the loop of the face
                for loop in face.loops:
                    # Identify which vertex this loop belongs to and assign stored coords
                    # This is complex in BMesh; we'll use a mapping dictionary
                    pass

        prev_ring = current_ring

    # Fixing UV assignment (BMesh loops)
    bm.verts.ensure_lookup_table()
    # We need to store the coordinates assigned during creation
    # Let's regenerate and assign UVs properly via loop access
    bm.free()
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    
    prev_ring_verts = []
    for i in range(segments + 1):
        theta = (i / segments) * theta_max
        u_coord = theta / theta_max
        dist = a * math.exp(b * theta)
        center = Vector((dist * math.cos(theta), dist * math.sin(theta), 0))
        tx = a * b * math.exp(b * theta) * math.cos(theta) - a * math.exp(b * theta) * math.sin(theta)
        ty = a * b * math.exp(b * theta) * math.sin(theta) + a * math.exp(b * theta) * math.cos(theta)
        tangent = Vector((tx, ty, 0)).normalized()
        right = tangent.cross(Vector((0, 0, 1))).normalized()
        up = Vector((0, 0, 1))

        current_radius = dist * radius_factor
        if i < segments * 0.2: current_radius *= (i / (segments * 0.2)) + 0.1

        curr_ring_verts = []
        for j in range(ring_res):
            angle = (j / ring_res) * 2 * math.pi
            v_coord = angle / (2 * math.pi)
            vx = center + right * math.cos(angle) * current_radius * 1.2
            vy = center + up * math.sin(angle) * current_radius * 0.8
            vert = bm.verts.new(vx + vy - center)
            curr_ring_verts.append((vert, u_coord, v_coord))

        if prev_ring_verts:
            for j in range(ring_res):
                v1, u1, w1 = prev_ring_verts[j]
                v2, u2, w2 = prev_ring_verts[(j+1)%ring_res]
                v3, u3, w3 = curr_ring_verts[(j+1)%ring_res]
                v4, u4, w4 = curr_ring_verts[j]
                face = bm.faces.new((v1, v2, v3, v4))
                # Assign UVs to face loops
                uvs = [(u1, w1), (u2, w2), (u3, w3), (u4, w4)]
                for loop in face.loops:
                    loop[uv_layer].uv = uvs[loop.vert_idx if hasattr(loop, 'vert_idx') else 0] # This is simplified
        prev_ring_verts = curr_ring_verts

    # Properly assign UVs by iterating through all loops
    # To be safe, we use a vertex-to-uv dictionary since the loop indices in bmesh can be tricky
    vert_to_uv = {}
    # Re-calculate values to avoid storage issues during BMesh face creation
    for i in range(segments + 1):
        theta = (i / segments) * theta_max
        u = theta / theta_max
        dist = a * math.exp(b * theta)
        center = Vector((dist * math.cos(theta), dist * math.sin(theta), 0))
        tx = a * b * math.exp(b * theta) * math.cos(theta) - a * math.exp(b * theta) * math.sin(theta)
        ty = a * b * math.exp(b * theta) * math.sin(theta) + a * math.exp(b * theta) * math.cos(theta)
        tangent = Vector((tx, ty, 0)).normalized()
        right = tangent.cross(Vector((0, 0, 1))).normalized()
        up = Vector((0, 0, 1))
        cr = dist * radius_factor
        if i < segments * 0.2: cr *= (i / (segments * 0.2)) + 0.1
        for j in range(ring_res):
            # we can't easily find the vert again, so let's just use the index from when they were created
            pass

    # Let's do a cleaner loop for UV assignment: 
    # Create verts first, store them, then create faces and assign loops.
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    all_verts = [] # stores (vert, u, v)
    for i in range(segments + 1):
        theta = (i / segments) * theta_max
        u = theta / theta_max
        dist = a * math.exp(b * theta)
        center = Vector((dist * math.cos(theta), dist * math.sin(theta), 0))
        tx = a * b * math.exp(b * theta) * math.cos(theta) - a * math.exp(b * theta) * math.sin(theta)
        ty = a * b * math.exp(b * theta) * math.sin(theta) + a * math.exp(b * theta) * math.cos(theta)
        tangent = Vector((tx, ty, 0)).normalized()
        right = tangent.cross(Vector((0, 0, 1))).normalized()
        up = Vector((0, 0, 1))
        cr = dist * radius_factor
        if i < segments * 0.2: cr *= (i / (segments * 0.2)) + 0.1
        ring = []
        for j in range(ring_res):
            angle = (j / ring_res) * 2 * math.pi
            v = angle / (2 * math.pi)
            vert = bm.verts.new(center + right * math.cos(angle)*cr*1.2 + up * math.sin(angle)*cr*0.8)
            ring.append((vert, u, v))
        all_verts.append(ring)

    for i in range(segments):
        for j in range(ring_res):
            v1 = all_verts[i][j][0]
            v2 = all_verts[i][(j+1)%ring_res][0]
            v3 = all_verts[i+1][(j+1)%ring_res][0]
            v4 = all_verts[i+1][j][0]
            face = bm.faces.new((v1, v2, v3, v4))
            # Assign UVs to the 4 loops of the face
            uvs = [all_verts[i][j][1:], all_verts[i][(j+1)%ring_res][1:], 
                   all_verts[i+1][(j+1)%ring_res][1:], all_verts[i+1][j][1:]]
            for loop in face.loops:
                # This is a hacky way to align loops to the verts we used to create the face
                # but since faces are created in order, it generally works.
                pass
    
    # More reliable UV assignment: iterate all loops and check which vertex they belong to
    # We need a map of vert -> uv
    vert_uv_map = {}
    for ring in all_verts:
        for v_data in ring:
            vert_uv_map[v_data[0]] = (v_data[1], v_data[2])

    for face in bm.faces:
        for loop in face.loops:
            loop[uv_layer].uv = vert_uv_map[loop.vert]

    # Cap ends
    first_ring = [v[0] for v in all_verts[0]]
    bm.faces.new(first_ring)
    last_ring = [v[0] for v in all_verts[-1]]
    bm.faces.new(last_ring)

    bm.normal_update()
    mesh = bpy.data.meshes.new("NautilusShell")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Nautilus", mesh)
    bpy.context.collection.objects.link(obj)
    
    subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subsurf.levels = 2
    for poly in mesh.polygons: poly.use_smooth = True
    
    return obj

if __name__ == "__main__":
    clear_scene()
    nautilus_obj = create_nautilus()
    
    # Apply Material
    mat = create_nautilus_material()
    nautilus_obj.data.materials.append(mat)
    
    bpy.context.view_layer.update()
    local_bbox_min = nautilus_obj.bound_box[0]
    local_bbox_max = nautilus_obj.bound_box[6]
    center_offset = (Vector((local_bbox_min)) + Vector((local_bbox_max))) / 2
    nautilus_obj.location -= center_offset
