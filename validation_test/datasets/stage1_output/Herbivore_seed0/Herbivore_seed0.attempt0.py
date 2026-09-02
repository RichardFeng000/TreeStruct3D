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

def add_sphere(bm, center, radius, u_segments=24, v_segments=16, scale=(1, 1, 1)):
    n = len(bm.verts)
    bmesh.ops.create_uvsphere(bm, u_segments=u_segments, v_segments=v_segments, radius=radius)
    for i in range(n, len(bm.verts)):
        v = bm.verts[i]
        v.co.x = center[0] + v.co.x * scale[0]
        v.co.y = center[1] + v.co.y * scale[1]
        v.co.z = center[2] + v.co.z * scale[2]

mesh = bpy.data.meshes.new("CreatureMesh")
obj = bpy.data.objects.new("FurryCreature", mesh)
bpy.context.collection.objects.link(obj)

bm = bmesh.new()

# Body - stocky, rounded, bear-like
add_sphere(bm, (0, 0, 1.0), 1.4, 36, 24, scale=(2.0, 1.35, 1.2))
for v in list(bm.verts):
    if v.co.z < 0.6:
        v.co.z *= 0.88

# Back hump for bear-like silhouette
add_sphere(bm, (-0.3, 0, 1.7), 0.7, 24, 16, scale=(1.2, 0.9, 0.5))

# Head - small
add_sphere(bm, (2.3, 0, 1.0), 0.55, 28, 20, scale=(1.1, 0.95, 0.95))

# Muzzle
add_sphere(bm, (2.9, 0, 0.75), 0.32, 20, 14, scale=(1.5, 0.85, 0.65))

# Ears - small rounded
add_sphere(bm, (2.2, 0.35, 1.5), 0.15, 12, 10, scale=(0.7, 0.5, 1.1))
add_sphere(bm, (2.2, -0.35, 1.5), 0.15, 12, 10, scale=(0.7, 0.5, 1.1))

# Neck - short and thick
add_sphere(bm, (1.7, 0, 0.9), 0.5, 20, 14, scale=(1.0, 1.0, 0.8))

# Tail - small stubby
add_sphere(bm, (-2.6, 0, 0.9), 0.22, 12, 10, scale=(0.8, 0.8, 0.6))

# Legs - four thick legs with large rounded paws
for pos in [(1.4, 0.75, 0.0), (1.4, -0.75, 0.0), (-1.4, 0.75, 0.0), (-1.4, -0.75, 0.0)]:
    add_sphere(bm, (pos[0], pos[1], pos[2] - 0.1), 0.45, 18, 14, scale=(0.85, 0.85, 1.4))
    add_sphere(bm, (pos[0], pos[1], pos[2] - 0.85), 0.48, 18, 14, scale=(1.2, 1.2, 0.5))

# Merge overlapping vertices and recalculate normals
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.06)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh)
bm.free()

# Smooth shading
for poly in mesh.polygons:
    poly.use_smooth = True

# Subdivision surface modifier
subsurf = obj.modifiers.new(name="Subsurf", type='SUBSURF')
subsurf.levels = 2
subsurf.render_levels = 3

# Vertex color painting for fur coloring
vcol = mesh.color_attributes.new(name="FurColor", type='FLOAT_COLOR', domain='POINT')

base = (0.80, 0.68, 0.58, 1.0)
stripe = (0.30, 0.23, 0.18, 1.0)
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

    # Stripes on flanks - darker brownish-gray vertical bands
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

    # Dorsal darker marking along the back
    if co.z > 1.5 and abs(co.y) < 0.5:
        db = (co.z - 1.5) / 0.5 * 0.3 * (1 - abs(co.y) / 0.5)
        r = r * (1 - db) + stripe[0] * db
        g = g * (1 - db) + stripe[1] * db
        b = b * (1 - db) + stripe[2] * db

    # Muzzle darker
    if co.x > 2.7 and co.z < 1.0:
        mb = 0.25
        r = r * (1 - mb) + stripe[0] * mb
        g = g * (1 - mb) + stripe[1] * mb
        b = b * (1 - mb) + stripe[2] * mb

    # Ears darker
    if co.z > 1.4 and 1.8 < co.x < 2.6 and abs(co.y) > 0.2:
        eb = 0.3
        r = r * (1 - eb) + stripe[0] * eb
        g = g * (1 - eb) + stripe[1] * eb
        b = b * (1 - eb) + stripe[2] * eb

    # Subtle noise variation
    n = math.sin(co.x * 15) * math.cos(co.y * 13) * math.sin(co.z * 11) * 0.04
    r = max(0, min(1, r + n))
    g = max(0, min(1, g + n))
    b = max(0, min(1, b + n))
    vcol.data[i].color = (r, g, b, a)

# Material with vertex color for fur base coloring
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

# Particle hair system for dense fluffy fur
psys_mod = obj.modifiers.new(name="FurParticles", type='PARTICLE_SYSTEM')
fs = psys_mod.particle_system.settings
fs.type = 'HAIR'
fs.count = 40000
fs.hair_length = 0.5
fs.hair_step = 7
fs.use_advanced_hair = True
fs.child_type = 'INTERPOLATED'
fs.child_nbr = 10
fs.rendered_child_count = 30
fs.child_length = 0.9
fs.child_length_threshold = 0.0
fs.clump_factor = 0.35
fs.clump_shape = 0.5
fs.roughness_1 = 0.3
fs.roughness_1_size = 1.0
fs.roughness_2 = 0.15
fs.roughness_2_threshold = 0.0
fs.roughness_endpoint = 0.25
fs.roughness_end_shape = 0.5
fs.use_modifier_stack = True