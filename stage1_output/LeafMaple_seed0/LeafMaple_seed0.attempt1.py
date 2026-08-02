import bpy
import bmesh
import math
from mathutils import Vector

# Clear scene
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for mesh in list(bpy.data.meshes):
    bpy.data.meshes.remove(mesh)
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat)

# Parameters
leaf_scale = 3.0
petiole_length = 2.2
petiole_radius_base = 0.06
petiole_radius_tip = 0.03

lobe_defs = [
    (0,   1.00, 13, 1.5),
    (42,  0.80, 12, 1.3),
    (88,  0.62, 13, 1.2),
    (-88, 0.62, 13, 1.2),
    (-42, 0.80, 12, 1.3),
]

def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

def lobe_radius(theta_deg):
    r = 0.08
    for angle, length, width, sharpness in lobe_defs:
        delta = theta_deg - angle
        while delta > 180:
            delta -= 360
        while delta < -180:
            delta += 360
        delta = abs(delta)
        if delta < width * 3.0:
            t = delta / (width * 3.0)
            lobe_r = length * (1 - smoothstep(t)) ** (1.0 / sharpness)
            r = max(r, lobe_r + 0.04)
    return r

def serration_value(theta_deg, base_r):
    if base_r < 0.20:
        return 0.0
    amp = 0.06 * min(1.0, (base_r - 0.12) / 0.5)
    freq = 48
    phase = theta_deg * freq / 360.0
    t = phase % 1.0
    if t < 0.5:
        tooth = 4 * t - 1
    else:
        tooth = 3 - 4 * t
    irregularity = 0.12 * math.sin(theta_deg * 7.3) + 0.08 * math.sin(theta_deg * 13.1)
    tooth *= (1 + irregularity)
    return amp * tooth

def generate_outline(num_points=540, serrated=True):
    points = []
    for i in range(num_points):
        theta = -180 + 360 * i / num_points
        r = lobe_radius(theta)
        if serrated:
            r += serration_value(theta, r)
        theta_rad = math.radians(theta)
        x = r * math.sin(theta_rad) * leaf_scale
        y = r * math.cos(theta_rad) * leaf_scale
        points.append((x, y))
    return points

def compute_undulation(x, y, t):
    dist = math.sqrt(x * x + y * y)
    angle = math.atan2(x, y)
    z = 0.0
    z += 0.1 * math.sin(angle * 3 + 0.5) * t
    z += 0.05 * math.sin(dist * 3.5) * t
    z += 0.04 * math.cos(angle * 5 - dist * 2) * t
    z += 0.08 * t * t
    return z

def compute_vein_displacement(x, y, t):
    z = 0.0
    point = Vector((x, y))

    for lobe_angle, lobe_length, _, _ in lobe_defs:
        la = math.radians(lobe_angle)
        vein_dir = Vector((math.sin(la), math.cos(la)))
        proj = point.dot(vein_dir)
        perp = point - vein_dir * proj
        perp_dist = perp.length

        max_proj = lobe_length * leaf_scale * t * 1.05
        if 0.01 < proj < max_proj:
            vein_progress = proj / max_proj
            vein_width = 0.06 * (1 - vein_progress * 0.6)
            vein_falloff = math.exp(-(perp_dist / vein_width) ** 2)
            vein_height = 0.06 * (1 - vein_progress * 0.3)
            z += vein_height * vein_falloff * t

            num_secondary = 5
            for s in range(num_secondary):
                s_t = (s + 1) / (num_secondary + 1)
                branch_point = vein_dir * (max_proj * s_t)
                branch_offset = point - branch_point

                for side in [-1, 1]:
                    branch_angle = la + side * math.radians(38)
                    bdir = Vector((math.sin(branch_angle), math.cos(branch_angle)))
                    bproj = branch_offset.dot(bdir)
                    bperp = branch_offset - bdir * bproj
                    bperp_dist = bperp.length

                    branch_len = max_proj * 0.30 * (1 - s_t * 0.3)
                    if bproj > 0 and bproj < branch_len:
                        bprogress = bproj / branch_len
                        bwidth = 0.02 * (1 - bprogress * 0.7)
                        bfalloff = math.exp(-(bperp_dist / bwidth) ** 2)
                        bheight = 0.03 * (1 - bprogress * 0.5)
                        z += bheight * bfalloff * t * (1 - s_t * 0.2)

    z += 0.008 * math.sin(x * 22) * math.cos(y * 22) * t
    return z

def create_leaf_blade():
    bm = bmesh.new()
    smooth_outline = generate_outline(540, serrated=False)
    serrated_outline = generate_outline(540, serrated=True)
    num_outline = len(smooth_outline)

    num_rings = 12
    ring_verts = []

    for ring_idx in range(num_rings + 1):
        t = ring_idx / num_rings
        scale = t ** 0.65
        serration_blend = smoothstep((t - 0.75) / 0.25)

        verts = []
        for i in range(num_outline):
            sx, sy = smooth_outline[i]
            ex, ey = serrated_outline[i]
            ox = sx * (1 - serration_blend) + ex * serration_blend
            oy = sy * (1 - serration_blend) + ey * serration_blend

            x = ox * scale
            y = oy * scale

            z = compute_undulation(x, y, t)
            z += compute_vein_displacement(x, y, t)

            verts.append(bm.verts.new((x, y, z)))

        ring_verts.append(verts)

    bm.verts.ensure_lookup_table()

    for ring_idx in range(num_rings):
        r1 = ring_verts[ring_idx]
        r2 = ring_verts[ring_idx + 1]
        for i in range(num_outline):
            j = (i + 1) % num_outline
            try:
                bm.faces.new([r1[i], r1[j], r2[j], r2[i]])
            except ValueError:
                pass

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True

    return bm

def create_petiole():
    bm = bmesh.new()
    segments = 32
    radial_segments = 16

    start = Vector((0, -0.05 * leaf_scale, 0))
    end = Vector((0, -0.05 * leaf_scale - petiole_length, 0))

    verts_grid = []
    for i in range(segments + 1):
        t = i / segments
        pos = start.lerp(end, t)
        pos.x += 0.035 * math.sin(t * math.pi * 0.8)
        pos.z += 0.02 * math.sin(t * math.pi)

        radius = petiole_radius_base * (1 - t * 0.35) + petiole_radius_tip * t * 0.35
        if t < 0.1:
            radius *= 1 + (0.1 - t) * 4

        ring = []
        for j in range(radial_segments):
            angle = 2 * math.pi * j / radial_segments
            x = pos.x + radius * math.cos(angle)
            y = pos.y
            z = pos.z + radius * math.sin(angle)
            ring.append(bm.verts.new((x, y, z)))
        verts_grid.append(ring)

    for i in range(segments):
        for j in range(radial_segments):
            j2 = (j + 1) % radial_segments
            v1 = verts_grid[i][j]
            v2 = verts_grid[i][j2]
            v3 = verts_grid[i + 1][j2]
            v4 = verts_grid[i + 1][j]
            bm.faces.new([v1, v2, v3, v4])

    end_verts = verts_grid[-1]
    end_center = bm.verts.new((end.x, end.y, end.z))
    for j in range(radial_segments):
        j2 = (j + 1) % radial_segments
        bm.faces.new([end_verts[j], end_verts[j2], end_center])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True

    return bm

# Build geometry
blade_bm = create_leaf_blade()
blade_mesh = bpy.data.meshes.new("LeafBladeMesh")
blade_bm.to_mesh(blade_mesh)
blade_bm.free()

petiole_bm = create_petiole()
petiole_mesh = bpy.data.meshes.new("PetioleMesh")
petiole_bm.to_mesh(petiole_mesh)
petiole_bm.free()

combined_mesh = bpy.data.meshes.new("MapleLeafMesh")
combined_bm = bmesh.new()
combined_bm.from_mesh(blade_mesh)
combined_bm.from_mesh(petiole_mesh)
bmesh.ops.remove_doubles(combined_bm, verts=combined_bm.verts, dist=0.01)
bmesh.ops.recalc_face_normals(combined_bm, faces=combined_bm.faces)
for f in combined_bm.faces:
    f.smooth = True
combined_bm.to_mesh(combined_mesh)
combined_bm.free()

bpy.data.meshes.remove(blade_mesh)
bpy.data.meshes.remove(petiole_mesh)

leaf = bpy.data.objects.new("MapleLeaf", combined_mesh)
bpy.context.collection.objects.link(leaf)

# Modifiers
solidify = leaf.modifiers.new(name="Solidify", type='SOLIDIFY')
solidify.thickness = 0.02
solidify.offset = 0
solidify.use_even_offset = True

subsurf = leaf.modifiers.new(name="Subdivision", type='SUBSURF')
subsurf.levels = 2
subsurf.render_levels = 3
try:
    subsurf.boundary_smooth = 'PRESERVE_CORNERS'
except AttributeError:
    pass

# Orient for three-quarter view
leaf.rotation_euler = (math.radians(15), math.radians(-10), math.radians(5))