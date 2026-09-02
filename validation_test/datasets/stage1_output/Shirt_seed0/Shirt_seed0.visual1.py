import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.8
    return mat

def create_shirt():
    # Materials
    pink_mat = create_material("FabricPink", (1.0, 0.75, 0.8, 1.0)) # Blush Pink
    trim_mat = create_material("TrimDark", (0.15, 0.15, 0.15, 1.0))  # Dark Grey/Black

    # Dimensions
    bw, bh = 0.6, 0.8     # Body width, height
    sw, sh = 0.4, 0.25    # Sleeve length, width
    thick = 0.01          # Fabric thickness
    trim_w = 0.03         # Trim strip width

    bm = bmesh.new()

    # --- Torso Geometry ---
    # Corners of the body (rectangular)
    v_bl = bm.verts.new(Vector((-bw/2, -bh/2, 0)))
    v_br = bm.verts.new(Vector((bw/2, -bh/2, 0)))
    v_tr = bm.verts.new(Vector((bw/2, bh/2, 0)))
    v_tl = bm.verts.new(Vector((-bw/2, bh/2, 0)))

    # Create a grid for the body to avoid "fan" artifacts and allow clean holes
    # Simple approach: define perimeter and bridge to neck
    neck_res = 32
    n_rad_x, n_rad_y = 0.1, 0.08
    n_center = Vector((0, bh/2 * 0.7, 0))
    n_verts = []
    for i in range(neck_res):
        a = (2 * math.pi * i) / neck_res
        v = bm.verts.new(Vector((n_center.x + math.cos(a)*n_rad_x, n_center.y + math.sin(a)*n_rad_y, 0)))
        n_verts.append(v)

    # Create outer ring vertices for the body
    outer_res = 64
    out_verts = []
    for i in range(outer_res):
        t = i / outer_res
        if t < 0.25: p = v_bl.co.lerp(v_br.co, t * 4)
        elif t < 0.5: p = v_br.co.lerp(v_tr.co, (t-0.25)*4)
        elif t < 0.75: p = v_tr.co.lerp(v_tl.co, (t-0.5)*4)
        else: p = v_tl.co.lerp(v_bl.co, (t-0.75)*4)
        out_verts.append(bm.verts.new(p))

    # Bridge inner and outer to create the main torso fabric
    for i in range(outer_res):
        iv1 = n_verts[i % neck_res]
        iv2 = n_verts[(i+1) % neck_res]
        ov1 = out_verts[i]
        ov2 = out_verts[(i+1) % outer_res]
        bm.faces.new((iv1, iv2, ov2, ov1))

    # --- Sleeve Geometry (Slightly Raised) ---
    sleeve_z = 0.03 # Elevation for "raised" look
    
    # Right sleeve vertices
    rs_inner_top = bm.verts.new(Vector((bw/2, bh/2, sleeve_z)))
    rs_inner_bot = bm.verts.new(Vector((bw/2, bh/2 - sh, sleeve_z)))
    rs_outer_bot = bm.verts.new(Vector((bw/2 + sw, bh/2 - sh, sleeve_z)) )
    rs_outer_top = bm.verts.new(Vector((bw/2 + sw, bh/2, sleeve_z)))
    bm.faces.new((rs_inner_bot, rs_inner_top, rs_outer_top, rs_outer_bot))

    # Left sleeve vertices
    ls_inner_top = bm.verts.new(Vector((-bw/2, bh/2, sleeve_z)))
    ls_inner_bot = bm.verts.new(Vector((-bw/2, bh/2 - sh, sleeve_z)))
    ls_outer_bot = bm.verts.new(Vector((-bw/2 - sw, bh/2 - sh, sleeve_z)))
    ls_outer_top = bm.verts.new(Vector((-bw/2 - sw, bh/2, sleeve_z)))
    bm.faces.new((ls_inner_bot, ls_inner_top, ls_outer_top, ls_outer_bot))

    # Convert to mesh
    mesh_data = bpy.data.meshes.new("ShirtMesh")
    bm.to_mesh(mesh_data)
    bm.free()
    shirt_obj = bpy.data.objects.new("Shirt", mesh_data)
    bpy.context.collection.objects.link(shirt_obj)
    shirt_obj.data.materials.append(pink_mat)

    # Add thickness to fabric
    solidify = shirt_obj.modifiers.new(name="Thickness", type='SOLIDIFY')
    solidify.thickness = thick
    solidify.offset = 1.0

    # --- Trim Geometry (Dark borders) ---
    trim_bm = bmesh.new()
    
    def add_strip(p1, p2, z=0):
        vec = (p2 - p1).normalized()
        perp = Vector((-vec.y, vec.x, 0)) * trim_w
        v1a = trim_bm.verts.new(p1 + perp + Vector((0,0,z)))
        v1b = trim_bm.verts.new(p1 - perp + Vector((0,0,z)))
        v2a = trim_bm.verts.new(p2 + perp + Vector((0,0,z)))
        v2b = trim_bm.verts.new(p2 - perp + Vector((0,0,z)))
        trim_bm.faces.new((v1a, v2a, v2b, v1b))

    # Body bottom and sides
    add_strip(Vector((-bw/2, -bh/2, 0)), Vector((bw/2, -bh/2, 0))) # Bottom
    add_strip(Vector((bw/2, -bh/2, 0)), Vector((bw/2, bh/2-sh, 0))) # Right side torso
    add_strip(Vector((-bw/2, -bh/2, 0)), Vector((-bw/2, bh/2-sh, 0))) # Left side torso

    # Sleeves (elevated)
    z = sleeve_z + 0.01
    # Right sleeve edges
    add_strip(Vector((bw/2, bh/2-sh, z)), Vector((bw/2+sw, bh/2-sh, z)))
    add_strip(Vector((bw/2+sw, bh/2-sh, z)), Vector((bw/2+sw, bh/2, z)))
    add_strip(Vector((bw/2+sw, bh/2, z)), Vector((bw/2, bh/2, z)))
    # Left sleeve edges
    add_strip(Vector((-bw/2, bh/2-sh, z)), Vector((-bw/2-sw, bh/2-sh, z)))
    add_strip(Vector((-bw/2-sw, bh/2-sh, z)), Vector((-bw/2-sw, bh/2, z)))
    add_strip(Vector((-bw/2-sw, bh/2, z)), Vector((-bw/2, bh/2, z)))

    # Top shoulders and neck trim
    add_strip(Vector((bw/2, bh/2, 0)), Vector((n_center.x + n_rad_x, n_center.y, 0))) # Right shoulder to neck
    add_strip(Vector((-bw/2, bh/2, 0)), Vector((n_center.x - n_rad_x, n_center.y, 0))) # Left shoulder to neck

    # Neck circle trim
    n_res = 64
    v_ins, v_outs = [], []
    for i in range(n_res):
        a = (2 * math.pi * i) / n_res
        vx, vy = math.cos(a), math.sin(a)
        v_ins.append(trim_bm.verts.new(Vector((n_center.x + vx*n_rad_x, n_center.y + vy*n_rad_y, 0.01))))
        v_outs.append(trim_bm.verts.new(Vector((n_center.x + vx*(n_rad_x+trim_w), n_center.y + vy*(n_rad_y+trim_w), 0.01))))
    for i in range(n_res):
        trim_bm.faces.new((v_ins[i], v_ins[(i+1)%n_res], v_outs[(i+1)%n_res], v_outs[i]))

    trim_mesh = bpy.data.meshes.new("TrimMesh")
    trim_bm.to_mesh(trim_mesh)
    trim_bm.free()
    trim_obj = bpy.data.objects.new("Trim", trim_mesh)
    bpy.context.collection.objects.link(trim_obj)
    trim_obj.data.materials.append(trim_mat)

    t_solidify = trim_obj.modifiers.new(name="TrimThickness", type='SOLIDIFY')
    t_solidify.thickness = thick * 1.5
    t_solidify.offset = 1.0

clear_scene()
create_shirt()
