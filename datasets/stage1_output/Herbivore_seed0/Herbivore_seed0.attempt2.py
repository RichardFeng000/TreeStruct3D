import bpy
import bmesh
import math

# Clear scene
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for m in list(bpy.data.meshes):
    if m.users == 0:
        bpy.data.meshes.remove(m)
for mat in list(bpy.data.materials):
    if mat.users == 0:
        bpy.data.materials.remove(mat)
for part in list(bpy.data.particles):
    if part.users == 0:
        bpy.data.particles.remove(part)

def safe_set(obj, attr, value):
    try:
        setattr(obj, attr, value)
    except Exception:
        pass

def add_sphere(bm, center, radius, u_segments=24, v_segments=16, scale=(1, 1, 1)):
    result = bmesh.ops.create_uvsphere(bm, u_segments=u_segments, v_segments=v_segments, radius=radius)
    for v in result["verts"]:
        v.co.x = center[0] + v.co.x * scale[0]
        v.co.y = center[1] + v.co.y * scale[1]
        v.co.z = center[2] + v.co.z * scale[2]
    return result["verts"]

mesh = bpy.data.meshes.new("CreatureMesh")
obj = bpy.data.objects.new("FurryCreature", mesh)
bpy.context.collection.objects.link(obj)

bm = bmesh.new()

# Body - stocky, rounded
body_verts = add_sphere(bm, (0, 0, 0.8), 1.4, 36, 24, scale=(2.0, 1.35, 1.2))
for v in body_verts:
    if v.co.z < 0.6:
        v.co.z *= 0.88

# Head
head_verts = add_sphere(bm, (2.3, 0, 0.8), 0.55, 28, 20, scale=(1.1, 0.95, 0.95))

# Neck
neck_verts = add_sphere(bm, (1.7, 0, 0.7), 0.5, 20, 14, scale=(1.0, 1.0, 0.8))

# Legs
leg_positions = [(1.4, 0.75, 0.0), (1.4, -0.75, 0.0), (-1.4, 0.75, 0.0), (-1.4, -0.75, 0.0)]
for pos in leg_positions:
    add_sphere(bm, (pos[0], pos[1], pos[2] - 0.1), 0.45, 18, 14, scale=(0.85, 0.85, 1.4))
    add_sphere(bm, (pos[0], pos[1], pos[2] - 0.85), 0.48, 18, 14, scale=(1.2, 1.2, 0.5))

# Tail
add_sphere(bm, (-2.6, 0, 0.7), 0.22, 12, 10, scale=(0.8, 0.8, 0.6))

# Merge and smooth
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.06)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(mesh)
bm.free()

# Smooth shading
for poly in mesh.polygons:
    poly.use_smooth = True

# Subdivision
subsurf = obj.modifiers.new(name="Subsurf", type='SUBSURF')
subsurf.levels = 2
subsurf.render_levels = 3

# Vertex colors for fur
vcol = mesh.color_attributes.new(name="FurColor", type='FLOAT_COLOR', domain='POINT')

base = (0.80, 0.68, 0.58, 1.0)  # sandy beige-pink
stripe = (0.30, 0.23, 0.18, 1.0)  # brownish-gray
leg_c = (0.60, 0.48, 0.38, 1.0)
belly = (0.88, 0.78, 0.68, 1.0)

for i, vert in enumerate(mesh.vertices):
    co = vert.co
    r, g, b, a = base
    d = math.sqrt(co.x ** 2 + co.y ** 2)

    # Legs darker
    if co.z < 0.2 and d > 0.6:
        r, g, b = leg_c[0], leg_c[1], leg_c[2]
    # Belly lighter
    elif co.z < 0.5 and d < 1.5:
        t = max(0, (0.5 - co.z) / 0.5) * 0.5
        r = r * (1 - t) + belly[0] * t
        g = g * (1 - t) + belly[1] * t
        b = b * (1 - t) + belly[2] * t

    # Stripes on flanks
    if 0.3 < co.z < 2.3 and -2.2 < co.x < 2.2:
        sf = min(1.0, abs(co.y) / 0.8)
        if sf > 0.15:
            sp = math.sin(co.x * 2.2) * 0.5 + 0.5
            sn1 = math.sin(co.x * 5.5 + co.z * 2) * 0.2
            sn2 = math.sin(co.x * 11 + co.y * 3) * 0.1
            sv = sp + sn1 + sn2
            if sv > 0.5:
                t = min(1.0, (sv - 0.5) / 0.4) * sf
                r = r * (1 - t) + stripe[0] * t
                g = g * (1 - t) + stripe[1] * t
                b = b * (1 - t) + stripe[2] * t

    # Dorsal marking
    if co.z > 1.5 and abs(co.y) < 0.5:
        db = (co.z - 1.5) / 0.5 * 0.3 * (1 - abs(co.y) / 0.5)
        r = r * (1 - db) + stripe[0] * db
        g = g * (1 - db) + stripe[1] * db
        b = b * (1 - db) + stripe[2] * db

    # Muzzle
    if co.x > 2.7 and co.z < 1.0:
        mb = 0.25
        r = r * (1 - mb) + stripe[0] * mb
        g = g * (1 - mb) + stripe[1] * mb
        b = b * (1 - mb) + stripe[2] * mb

    # Ears (approximated by head region)
    if co.z > 1.2 and 1.8 < co.x < 2.6 and abs(co.y) > 0.2:
        eb = 0.3
        r = r * (1 - eb) + stripe[0] * eb
        g = g * (1 - eb) + stripe[1] * eb
        b = b * (1 - eb) + stripe[2] * eb

    # Noise
    n = math.sin(co.x * 15) * math.cos(co.y * 13) * math.sin(co.z * 11) * 0.04
    r = max(0, min(1, r + n))
    g = max(0, min(1, g + n))
    b = max(0, min(1, b + n))
    vcol.data[i].color = (r, g, b, a)

# Material with vertex color
mat = bpy.data.materials.new("FurMat")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

out = nodes.new('ShaderNodeOutputMaterial')
vc = nodes.new('ShaderNodeVertexColor')
vc.layer_name = "FurColor"
bsdf = nodes.new('ShaderNodeBsdfPrincipled')
links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
bsdf.inputs['Roughness'].default_value = 0.95
obj.data.materials.append(mat)

# Particle hair system
try:
    psys_mod = obj.modifiers.new(name="FurParticles", type='PARTICLE_SYSTEM')
    fs = psys_mod.particle_system.settings

    safe_set(fs, 'type', 'HAIR')
    safe_set(fs, 'count', 15000)
    safe_set(fs, 'hair_length', 0.5)
    safe_set(fs, 'hair_step', 7)
    safe_set(fs, 'use_advanced_hair', True)
    safe_set(fs, 'child_type', 'INTERPOLATED')

    for attr in ['child_nbr', 'child_count', 'children_count']:
        if hasattr(fs, attr):
            setattr(fs, attr, 8)
            break

    for attr in ['rendered_child_count', 'render_child_count', 'child_render_count']:
        if hasattr(fs, attr):
            setattr(fs, attr, 25)
            break

    safe_set(fs, 'child_length', 0.9)
    safe_set(fs, 'child_length_threshold', 0.0)
    safe_set(fs, 'clump_factor', 0.35)
    safe_set(fs, 'clump_shape', 0.5)
    safe_set(fs, 'roughness_1', 0.3)
    safe_set(fs, 'roughness_1_size', 1.0)
    safe_set(fs, 'roughness_2', 0.15)
    safe_set(fs, 'roughness_2_threshold', 0.0)
    safe_set(fs, 'roughness_endpoint', 0.25)
    safe_set(fs, 'roughness_end_shape', 0.5)
    safe_set(fs, 'use_modifier_stack', True)

    # Set hair color to match vertex color via shader
    hair_mat = bpy.data.materials.new("HairMat")
    hair_mat.use_nodes = True
    hair_nodes = hair_mat.node_tree.nodes
    hair_links = hair_mat.node_tree.links
    hair_nodes.clear()

    hair_out = hair_nodes.new('ShaderNodeOutputMaterial')
    hair_vc = hair_nodes.new('ShaderNodeVertexColor')
    hair_vc.layer_name = "FurColor"
    hair_bsdf = hair_nodes.new('ShaderNodeBsdfPrincipled')
    hair_bsdf.inputs['Roughness'].default_value = 0.95
    hair_bsdf.inputs['Specular'].default_value = 0.0
    hair_bsdf.inputs['Transmission'].default_value = 0.0
    hair_bsdf.inputs['IOR'].default_value = 1.45
    hair_bsdf.inputs['Alpha'].default_value = 0.5
    hair_links.new(hair_vc.outputs['Color'], hair_bsdf.inputs['Base Color'])
    hair_links.new(hair_bsdf.outputs['BSDF'], hair_out.inputs['Surface'])
    fs.material = hair_mat
except Exception as e:
    print(f"Particle system setup warning: {e}")

# Ensure object is active and selected
bpy.context.view_layer.objects.active = obj
obj.select_set(True)