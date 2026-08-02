import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears all objects from the current scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple material with a base color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_shirt():
    # Materials
    pink_mat = create_material("FabricPink", (1.0, 0.78, 0.82, 1.0))  # Blush pink
    trim_mat = create_material("TrimDark", (0.1, 0.1, 0.1, 1.0))      # Dark grey/black

    # Dimensions
    body_w = 0.6
    body_h = 0.8
    sleeve_l = 0.45
    sleeve_w = 0.25
    thickness = 0.01
    trim_width = 0.02

    # --- Main Shirt Geometry ---
    bm = bmesh.new()
    
    # Torso coordinates
    # We define the outer perimeter of the shirt body (excluding sleeves)
    v_bl = bm.verts.new(Vector((-body_w/2, -body_h/2, 0)))
    v_br = bm.verts.new(Vector((body_w/2, -body_h/2, 0)))
    v_tr = bm.verts.new(Vector((body_w/2, body_h/2, 0)))
    v_tl = bm.verts.new(Vector((-body_w/2, body_h/2, 0)))

    # Neck hole coordinates (elliptical)
    neck_res = 32
    n_rad_x, n_rad_y = 0.12, 0.08
    n_center = Vector((0, body_h/2 * 0.65, 0))
    n_verts = []
    for i in range(neck_res):
        a = (2 * math.pi * i) / neck_res
        v = bm.verts.new(Vector((n_center.x + math.cos(a)*n_rad_x, n_center.y + math.sin(a)*n_rad_y, 0)))
        n_verts.append(v)

    # To create the body with a hole, we subdivide the area into quads
    # Create outer ring vertices for better topology bridging
    outer_res = 32
    out_verts = []
    for i in range(outer_res):
        # Interpolate between the 4 corners of the rectangle
        t = i / outer_res
        if t < 0.25: # Bottom
            frac = t * 4
            p = v_bl.co.lerp(v_br.co, frac)
        elif t < 0.5: # Right
            frac = (t - 0.25) * 4
            p = v_br.co.lerp(v_tr.co, frac)
        elif t < 0.75: # Top
            frac = (t - 0.5) * 4
            p = v_tr.co.lerp(v_tl.co, frac)
        else: # Left
            frac = (t - 0.75) * 4
            p = v_tl.co.lerp(v_bl.co, frac)
        out_verts.append(bm.verts.new(p))

    # Bridge inner neck ring to outer perimeter ring
    for i in range(outer_res):
        iv1 = n_verts[i % neck_res]
        iv2 = n_verts[(i+1) % neck_res]
        ov1 = out_verts[i]
        ov2 = out_verts[(i+1) % outer_res]
        bm.faces.new((iv1, iv2, ov2, ov1))

    # Sleeves - slightly raised from surface
    sleeve_z_start = 0.01
    sleeve_z_end = 0.06

    # Right Sleeve
    # Start at right edge of torso (v_br to v_tr)
    vs_r_outer_top = bm.verts.new(Vector((body_w/2 + sleeve_l, body_h/2 * 0.8, sleeve_z_end)))
    vs_r_outer_bot = bm.verts.new(Vector((body_w/2 + sleeve_l, body_h/2 * 0.3, sleeve_z_start)))
    # The sleeve attaches to the torso right edge
    # We'll just create a simple quad for now and solidify later
    bm.faces.new((v_br, vs_r_outer_bot, vs_r_outer_top, v_tr))

    # Left Sleeve
    vs_l_outer_top = bm.verts.new(Vector((-body_w/2 - sleeve_l, body_h/2 * 0.8, sleeve_z_end)))
    vs_l_outer_bot = bm.verts.new(Vector((-body_w/2 - sleeve_l, body_h/2 * 0.3, sleeve_z_start)))
    bm.faces.new((v_bl, v_tl, vs_l_outer_top, vs_l_outer_bot))

    # Convert to mesh and apply solidify
    mesh_data = bpy.data.meshes.new("ShirtMesh")
    bm.to_mesh(mesh_data)
    bm.free()
    shirt_obj = bpy.data.objects.new("Shirt", mesh_data)
    bpy.context.collection.objects.link(shirt_obj)
    shirt_obj.data.materials.append(pink_mat)

    solidify = shirt_obj.modifiers.new(name="Thickness", type='SOLIDIFY')
    solidify.thickness = thickness
    solidify.offset = 1.0

    # --- Trim Geometry ---
    trim_bm = bmesh.new()
    
    def add_trim_strip(p1, p2, z=0):
        dir_vec = (p2 - p1).normalized()
        perp = Vector((-dir_vec.y, dir_vec.x, 0)) * trim_width
        v1a = trim_bm.verts.new(p1 + perp + Vector((0,0,z)))
        v1b = trim_bm.verts.new(p1 - perp + Vector((0,0,z)))
        v2a = trim_bm.verts.new(p2 + perp + Vector((0,0,z)))
        v2b = trim_bm.verts.new(p2 - perp + Vector((0,0,z)))
        trim_bm.faces.new((v1a, v2a, v2b, v1b))

    # Bottom Hem
    add_trim_strip(Vector((-body_w/2, -body_h/2, 0)), Vector((body_w/2, -body_h/2, 0)))
    
    # Right Side (Torso)
    add_trim_strip(Vector((body_w/2, -body_h/2, 0)), Vector((body_w/2, body_h/2 * 0.3, 0)))
    # Right Sleeve Outer and Inner
    add_trim_strip(Vector((body_w/2, body_h/2 * 0.3, 0)), Vector((body_w/2 + sleeve_l, body_h/2 * 0.3, sleeve_z_start)))
    add_trim_strip(Vector((body_w/2 + sleeve_l, body_h/2 * 0.3, sleeve_z_start)), Vector((body_w/2 + sleeve_l, body_h/2 * 0.8, sleeve_z_end)))
    add_trim_strip(Vector((body_w/2 + sleeve_l, body_h/2 * 0.8, sleeve_z_end)), Vector((body_w/2, body_h/2, 0)))
    
    # Top Shoulder Right to Left
    add_trim_strip(Vector((body_w/2, body_h/2, 0)), Vector((-body_w/2, body_h/2, 0)))

    # Left Sleeve Outer and Inner
    add_trim_strip(Vector((-body_w/2, body_h/2, 0)), Vector((-body_w/2 - sleeve_l, body_h/2 * 0.8, sleeve_z_end)))
    add_trim_strip(Vector((-body_w/2 - sleeve_l, body_h/2 * 0.8, sleeve_z_end)), Vector((-body_w/2 - sleeve_l, body_h/2 * 0.3, sleeve_z_start)))
    add_trim_strip(Vector((-body_w/2 - sleeve_l, body_h/2 * 0.3, sleeve_z_start)), Vector((-body_w/2, body_h/2 * 0.3, 0)))
    # Left Side (Torso)
    add_trim_strip(Vector((-body_w/2, body_h/2 * 0.3, 0)), Vector((-body_w/2, -body_h/2, 0)))

    # Neck Trim (Circle)
    n_res = 64
    v_ins = []
    v_outs = []
    for i in range(n_res):
        a = (2 * math.pi * i) / n_res
        vx, vy = math.cos(a), math.sin(a)
        v_ins.append(trim_bm.verts.new(Vector((n_center.x + vx*n_rad_x, n_center.y + vy*n_rad_y, 0.01))))
        v_outs.append(trim_bm.verts.new(Vector((n_center.x + vx*(n_rad_x + trim_width), n_center.y + vy*(n_rad_y + trim_width), 0.01))))

    for i in range(n_res):
        trim_bm.faces.new((v_ins[i], v_ins[(i+1)%n_res], v_outs[(i+1)%n_res], v_outs[i]))

    # Finalize Trim Mesh
    trim_mesh_data = bpy.data.meshes.new("TrimMesh")
    trim_bm.to_mesh(trim_mesh_data)
    trim_bm.free()
    trim_obj = bpy.data.objects.new("Trim", trim_mesh_data)
    bpy.context.collection.objects.link(trim_obj)
    trim_obj.data.materials.append(trim_mat)

    # Solidify Trim for a bit of depth
    t_solid = trim_obj.modifiers.new(name="TrimThickness", type='SOLIDIFY')
    t_solid.thickness = thickness * 1.5
    t_solid.offset = 1.0
    
    # Shift trim slightly along Z to prevent z-fighting with the main fabric
    trim_obj.location.z = 0.002

clear_scene()
create_shirt()
