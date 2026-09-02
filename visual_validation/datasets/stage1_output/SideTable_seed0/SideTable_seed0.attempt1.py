import bpy
import bmesh
import math

# Clear scene
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for block in list(bpy.data.meshes):
    bpy.data.meshes.remove(block)
for block in list(bpy.data.materials):
    bpy.data.materials.remove(block)

# Parameters (scaled up for visibility)
TOP_SIZE = 1.0
TOP_THICKNESS = 0.056
CORNER_RADIUS = 0.09
TOP_Z = 1.0
TOP_BEVEL = 0.007

LEG_RADIUS = 0.036
LEG_SPACING = 0.68
BASE_RADIUS = 0.116
BASE_HEIGHT = 0.056

FLOOR_Z = 0.0
LEG_TOP_Z = TOP_Z - TOP_THICKNESS

def create_top_bm():
    bm = bmesh.new()
    half = TOP_SIZE / 2
    r = CORNER_RADIUS
    seg = 24

    corners = [
        (half - r, -half + r, -math.pi / 2),
        (half - r,  half - r, 0.0),
        (-half + r, half - r, math.pi / 2),
        (-half + r, -half + r, math.pi),
    ]

    top_verts = []
    for cx, cy, start in corners:
        for i in range(seg):
            angle = start + (math.pi / 2) * (i / seg)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            v = bm.verts.new((x, y, TOP_Z))
            top_verts.append(v)

    bm.verts.ensure_lookup_table()
    top_face = bm.faces.new(top_verts)

    ret = bmesh.ops.extrude_face_region(bm, geom=[top_face])
    ext_verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, -TOP_THICKNESS), verts=ext_verts)

    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    horiz_edges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6]
    if horiz_edges:
        bmesh.ops.bevel(bm, geom=horiz_edges, offset=TOP_BEVEL, segments=5, profile=0.5, affect='EDGES')

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def create_leg_bm(x_pos, y_pos):
    bm = bmesh.new()
    seg = 48

    z_top = LEG_TOP_Z
    z_floor = FLOOR_Z
    leg_bottom_z = z_floor + BASE_HEIGHT

    rings = []
    rings.append((LEG_RADIUS, z_top))
    rings.append((LEG_RADIUS, leg_bottom_z))
    rings.append((LEG_RADIUS * 0.985, leg_bottom_z - 0.004))
    rings.append((LEG_RADIUS * 0.972, leg_bottom_z - 0.012))

    flare_steps = 16
    r_start = LEG_RADIUS * 0.972
    r_end = BASE_RADIUS
    for i in range(1, flare_steps + 1):
        t = i / flare_steps
        z = leg_bottom_z - BASE_HEIGHT * t
        smooth = 0.5 - 0.5 * math.cos(math.pi * t)
        r = r_start + (r_end - r_start) * smooth
        rings.append((r, z))

    rings.append((BASE_RADIUS * 0.97, z_floor + 0.001))
    rings.append((BASE_RADIUS * 0.90, z_floor))

    all_rings = []
    for r, z in rings:
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            v = bm.verts.new((x_pos + r * math.cos(a), y_pos + r * math.sin(a), z))
            ring.append(v)
        all_rings.append(ring)

    bm.verts.ensure_lookup_table()

    for k in range(len(all_rings) - 1):
        ra = all_rings[k]
        rb = all_rings[k + 1]
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new([ra[i], ra[j], rb[j], rb[i]])

    bm.faces.new(all_rings[0])
    bm.faces.new(list(reversed(all_rings[-1])))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

# Build all parts as bmesh
top_bm = create_top_bm()
leg1_bm = create_leg_bm(LEG_SPACING / 2, 0)
leg2_bm = create_leg_bm(-LEG_SPACING / 2, 0)

# Merge leg bmeshes into top bmesh
for leg_bm in [leg1_bm, leg2_bm]:
    verts_map = {}
    for v in leg_bm.verts:
        new_v = top_bm.verts.new(v.co)
        verts_map[v] = new_v
    for f in leg_bm.faces:
        new_verts = [verts_map[v] for v in f.verts]
        top_bm.faces.new(new_verts)
    leg_bm.free()

bmesh.ops.recalc_face_normals(top_bm, faces=top_bm.faces[:])

# Create final mesh and object
side_table_mesh = bpy.data.meshes.new("SideTableMesh")
top_bm.to_mesh(side_table_mesh)
top_bm.free()

side_table = bpy.data.objects.new("SideTable", side_table_mesh)
bpy.context.collection.objects.link(side_table)

for p in side_table.data.polygons:
    p.use_smooth = True