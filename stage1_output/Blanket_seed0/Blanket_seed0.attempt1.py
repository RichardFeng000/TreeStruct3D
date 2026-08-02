import bpy
import bmesh
import math
import random
from mathutils import Vector, noise

# === Clear scene ===
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for block in list(bpy.data.meshes):
    bpy.data.meshes.remove(block)
for block in list(bpy.data.materials):
    bpy.data.materials.remove(block)
for block in list(bpy.data.cameras):
    bpy.data.cameras.remove(block)
for block in list(bpy.data.lights):
    bpy.data.lights.remove(block)

# === Parameters ===
BLANKET_SIZE = 4.0
SUBDIVISIONS = 130
THICKNESS = 0.018
HALF_SIZE = BLANKET_SIZE / 2

# === Create blanket mesh ===
mesh = bpy.data.meshes.new("BlanketMesh")
blanket = bpy.data.objects.new("Blanket", mesh)
bpy.context.collection.objects.link(blanket)
bpy.context.view_layer.objects.active = blanket
blanket.select_set(True)

# Create grid using bmesh
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=SUBDIVISIONS, y_segments=SUBDIVISIONS, size=HALF_SIZE)
bm.to_mesh(mesh)
bm.free()

# === Apply stronger rumpling displacement ===
for v in mesh.vertices:
    x, y = v.co.x, v.co.y

    # Multi-octave noise for natural rumpling — amplified
    z = 0.0
    z += noise.noise(Vector((x * 0.30, y * 0.30, 0.5))) * 0.050
    z += noise.noise(Vector((x * 0.75, y * 0.75, 0.5))) * 0.025
    z += noise.noise(Vector((x * 1.8, y * 1.8, 0.5))) * 0.012
    z += noise.noise(Vector((x * 4.5, y * 4.5, 0.5))) * 0.005

    # Edge waviness and slight curl — stronger
    edge_dist_x = HALF_SIZE - abs(x)
    edge_dist_y = HALF_SIZE - abs(y)
    edge_dist = min(edge_dist_x, edge_dist_y)

    if edge_dist < 0.7:
        ef = (0.7 - edge_dist) / 0.7
        ef = ef * ef
        wave = noise.noise(Vector((x * 2.0, y * 2.0, 1.5)))
        z += ef * 0.040 * (0.35 + 0.65 * (wave * 0.5 + 0.5))

    # Corner lift — more pronounced
    if edge_dist < 0.35:
        cf = (0.35 - edge_dist) / 0.35
        cf = cf * cf
        corner_noise = noise.noise(Vector((x * 3.0, y * 3.0, 3.5)))
        z += cf * 0.030 * (0.5 + 0.5 * corner_noise)

    # Subtle fold-like ridges — more defined
    fold = noise.noise(Vector((x * 0.5 + 10.0, y * 1.2 + 5.0, 7.0)))
    z += fold * 0.012 * max(0, 1.0 - edge_dist / HALF_SIZE)

    v.co.z = z

# === Generate animal print pattern — with higher contrast ===
random.seed(42)

# Pastel color palette — slightly more saturated
colors = [
    (0.95, 0.65, 0.75, 1.0),  # pastel pink
    (0.72, 0.65, 0.92, 1.0),  # lavender
    (0.62, 0.80, 0.95, 1.0),  # pastel blue
    (0.98, 0.92, 0.78, 1.0),  # cream
]

patches = []

def make_patch(cx, cy, radius, color, ns_range, na_range):
    return {
        'cx': cx, 'cy': cy, 'radius': radius, 'color': color,
        'angle': random.uniform(0, 2 * math.pi),
        'aspect': random.uniform(0.50, 1.0),
        'noise_scale': random.uniform(*ns_range),
        'noise_amp': random.uniform(*na_range),
        'seed': random.uniform(0, 200),
    }

# Large patches
for _ in range(22):
    patches.append(make_patch(
        random.uniform(-HALF_SIZE * 0.85, HALF_SIZE * 0.85),
        random.uniform(-HALF_SIZE * 0.85, HALF_SIZE * 0.85),
        random.uniform(0.22, 0.45), random.choice(colors),
        (2.0, 5.0), (0.35, 0.55)))

# Medium patches
for _ in range(30):
    patches.append(make_patch(
        random.uniform(-HALF_SIZE * 0.90, HALF_SIZE * 0.90),
        random.uniform(-HALF_SIZE * 0.90, HALF_SIZE * 0.90),
        random.uniform(0.10, 0.19), random.choice(colors),
        (3.5, 7.5), (0.35, 0.58)))

# Small spots
for _ in range(45):
    patches.append(make_patch(
        random.uniform(-HALF_SIZE * 0.95, HALF_SIZE * 0.95),
        random.uniform(-HALF_SIZE * 0.95, HALF_SIZE * 0.95),
        random.uniform(0.030, 0.075), random.choice(colors),
        (5.5, 11.0), (0.28, 0.48)))

# === Create color attribute and paint — higher contrast base ===
vcol_layer = mesh.color_attributes.new(name="AnimalPrint", type='FLOAT_COLOR', domain='POINT')

for v_idx, v in enumerate(mesh.vertices):
    x, y = v.co.x, v.co.y

    # Base: off-white with subtle variation — less gray
    wn = noise.noise(Vector((x * 7.0, y * 7.0, 10.0))) * 0.018
    wn2 = noise.noise(Vector((x * 15.0, y * 15.0, 20.0))) * 0.008
    r = 0.992 + wn + wn2 * 0.5
    g = 0.988 + wn + wn2 * 0.5
    b = 0.980 + wn * 0.8 + wn2 * 0.4

    for patch in patches:
        dx = x - patch['cx']
        dy = y - patch['cy']

        # Rotate to patch local space
        ca = math.cos(patch['angle'])
        sa = math.sin(patch['angle'])
        lx = dx * ca + dy * sa
        ly = -dx * sa + dy * ca

        # Elliptical distance
        ed = math.sqrt((lx / patch['aspect'])**2 + (ly * patch['aspect'])**2)

        # Noise-perturbed boundary — more aggressive
        ns = patch['noise_scale']
        sd = patch['seed']
        n1 = noise.noise(Vector((x * ns + sd, y * ns + sd, sd)))
        n2 = noise.noise(Vector((x * ns * 2.1 + sd, y * ns * 2.1 + sd, sd * 1.7)))
        boundary_noise = n1 * 0.65 + n2 * 0.35

        eff_radius = patch['radius'] * (1.0 + boundary_noise * patch['noise_amp'])

        if ed < eff_radius:
            t = 1.0 - (ed / eff_radius)
            t = max(0.0, min(1.0, t * 4.0))  # Sharper falloff

            pc = patch['color']
            r = r * (1 - t) + pc[0] * t
            g = g * (1 - t) + pc[1] * t
            b = b * (1 - t) + pc[2] * t

    # Clamp
    r = max(0.0, min(1.0, r))
    g = max(0.0, min(1.0, g))
    b = max(0.0, min(1.0, b))

    vcol_layer.data[v_idx].color = (r, g, b, 1.0)

# === Add modifiers ===
solidify = blanket.modifiers.new(name="Solidify", type='SOLIDIFY')
solidify.thickness = THICKNESS
solidify.offset = 0
solidify.use_rim = True
solidify.use_rim_only = False

subsurf = blanket.modifiers.new(name="Subsurf", type='SUBSURF')
subsurf.levels = 1
subsurf.render_levels = 2

# === Create material — reduce roughness for better color pop ===
mat = bpy.data.materials.new(name="BlanketMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links

# Clear default nodes
for node in list(nodes):
    nodes.remove(node)

output = nodes.new('ShaderNodeOutputMaterial')
output.location = (400, 0)

vcol_node = nodes.new('ShaderNodeVertexColor')
vcol_node.layer_name = "AnimalPrint"
vcol_node.location = (-200, 0)

bsdf = nodes.new('ShaderNodeBsdfPrincipled')
bsdf.location = (100, 0)
bsdf.inputs['Roughness'].default_value = 0.75  # Less rough for color vibrancy

links.new(vcol_node.outputs['Color'], bsdf.inputs['Base Color'])
links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

mesh.materials.append(mat)

# === Smooth shading ===
for poly in mesh.polygons:
    poly.use_smooth = True

# === Add subtle edge bevel for fabric-like soft edges ===
bevel = blanket.modifiers.new(name="Bevel", type='BEVEL')
bevel.width = 0.006
bevel.segments = 3
bevel.limit_method = 'ANGLE'
bevel.angle_limit = math.radians(40)