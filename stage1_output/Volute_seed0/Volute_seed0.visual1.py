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
        bsdf.inputs['Roughness'].default_value = 0.25
    return mat

def generate_volute_shell():
    clear_scene()

    # Materials
    mat_cream = create_material("Cream", (0.9, 0.85, 0.7, 1.0))
    mat_brown = create_material("Brown", (0.3, 0.2, 0.1, 1.0))

    # Spiral parameters for a globular volute
    a = 0.1       # Initial scale
    b = 0.15      # Growth rate of the spiral center
    h_step = 0.03 # Low spire Z growth per radian
    theta_max = 18.0 # Approx 2.8 turns for a denser coil
    segments = 400 
    ring_res = 36

    bm = bmesh.new()
    prev_ring = []

    for i in range(segments + 1):
        theta = (i / segments) * theta_max
        
        # Spiral path center
        r_path = a * math.exp(b * theta)
        cx = r_path * math.cos(theta)
        cy = r_path * math.sin(theta)
        cz = h_step * theta
        center = Vector((cx, cy, cz))

        # Tangent for the frame
        dr = a * b * math.exp(b * theta)
        tx = dr * math.cos(theta) - r_path * math.sin(theta)
        ty = dr * math.sin(theta) + r_path * math.cos(theta)
        tz = h_step
        tangent = Vector((tx, ty, tz)).normalized()

        # Coordinate frame (Frenet-like)
        up_fixed = Vector((0, 1, 0)) if abs(tangent.dot(Vector((0,0,1)))) > 0.9 else Vector((0, 0, 1))
        right = tangent.cross(up_fixed).normalized()
        actual_up = right.cross(tangent).normalized()

        # Shell radius: Grows exponentially then inflates for the body whorl
        # Starts small at spire, expands rapidly towards end
        base_radius = 0.1 * math.exp(0.12 * theta)
        if theta > theta_max * 0.7:
            inflation = 1.0 + (theta - theta_max * 0.7) * 0.4
            base_radius *= inflation

        current_ring = []
        for j in range(ring_res):
            phi = (j / ring_res) * 2 * math.pi
            
            # Make it slightly oval/globular
            scale_x = 1.0 + 0.15 * math.sin(phi)
            scale_y = 1.0 - 0.1 * math.cos(phi)
            
            offset = (right * math.cos(phi) * base_radius * scale_x) + \
                     (actual_up * math.sin(phi) * base_radius * scale_y)
            
            v = bm.verts.new(center + offset)
            current_ring.append(v)

        if prev_ring:
            for j in range(ring_res):
                v1 = prev_ring[j]
                v2 = prev_ring[(j + 1) % ring_res]
                v3 = current_ring[(j + 1) % ring_res]
                v4 = current_ring[j]
                face = bm.faces.new((v1, v2, v3, v4))

                # Radiating wavy stripes: based on theta (i) and phi (j)
                # Pattern is primarily transverse to the path but with a wave
                wave_offset = 0.8 * math.sin(phi * 3.0 + theta)
                stripe_val = (theta * 2.5 + wave_offset)
                if int(stripe_val) % 2 == 0:
                    face.material_index = 1 # Brown
                else:
                    face.material_index = 0 # Cream

        prev_ring = current_ring

    # Cap the start (spire tip)
    try:
        start_verts = [v for v in bm.verts if any(f.verts[0] == v for f in bm.faces)] # simplistic attempt to find first ring
        # Better: since we know order, just use indices 0 to ring_res-1
        bm.faces.new([bm.verts[k] for k in range(ring_res)])
    except:
        pass

    # Cap the end (aperture)
    try:
        bm.faces.new(prev_ring)
    except:
        pass

    mesh = bpy.data.meshes.new("VoluteShell")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("VoluteShell", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat_cream)
    obj.data.materials.append(mat_brown)

    # Smoothing for organic look
    subsurf = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf.levels = 2
    
    # Perspective setup
    obj.rotation_euler = (math.radians(60), 0, math.radians(45))
    obj.location = (0, 0, 0)

if __name__ == "__main__":
    generate_volute_shell()
