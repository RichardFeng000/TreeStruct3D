import bpy
import bmesh
import math
from mathutils import Vector, Matrix

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
    return mat

def add_feather(bm, start_pos, direction, length, width):
    """Adds a single feather quad to the bmesh."""
    v = direction.normalized()
    # Orthogonal vector for width (mostly horizontal)
    w = v.cross(Vector((0, 0, 1))).normalized()
    if w.length < 0.1:
        w = v.cross(Vector((0, 1, 0))).normalized()

    p1 = start_pos - w * (width / 2)
    p2 = start_pos + w * (width / 2)
    p3 = start_pos + v * length + w * (width / 2)
    p4 = start_pos + v * length - w * (width / 2)

    v1 = bm.verts.new(p1)
    v2 = bm.verts.new(p2)
    v3 = bm.verts.new(p3)
    v4 = bm.verts.new(p4)
    bm.faces.new((v1, v2, v3, v4))

def build_bird():
    # Materials
    mats = {
        "white": create_material("White", (0.95, 0.95, 0.95, 1.0)),
        "gray": create_material("GrayWhite", (0.75, 0.75, 0.75, 1.0)),
        "red_brown": create_material("ReddishBrown", (0.35, 0.15, 0.08, 1.0)),
        "dark_brown": create_material("DarkBrown", (0.15, 0.06, 0.03, 1.0)),
        "black": create_material("Black", (0.02, 0.02, 0.02, 1.0))
    }

    mesh = bpy.data.meshes.new("Bird")
    obj = bpy.data.objects.new("Bird", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # --- BODY ---
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=0.5)
    for v in bm.verts:
        v.co.x *= 0.6  # Slim width
        v.co.y *= 1.3  # Long body
        v.co.z *= 0.7  # Low profile

    # --- HEAD ---
    head_center = Vector((0, 1.4, 0.2))
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=12, radius=0.3)
    for v in bm.verts[-144:]: # Head vertices
        v.co += head_center

    # Beak
    beak_start = head_center + Vector((0, 0.25, 0))
    beak_end = head_center + Vector((0, 0.6, -0.1))
    b1 = bm.verts.new(beak_start + Vector((0.04, 0, 0)))
    b2 = bm.verts.new(beak_start + Vector((-0.04, 0, 0)))
    b3 = bm.verts.new(beak_end)
    bm.faces.new((b1, b2, b3))

    # --- WINGS (Cohesive surfaces) ---
    def create_wing(side):
        # Side: 1 for Right, -1 for Left
        span = 4.5
        chord = 1.2
        res_x = 10 # span resolution
        res_y = 4  # chord resolution
        
        verts = []
        for i in range(res_x):
            tx = i / (res_x - 1)
            # Wing curvature/shape
            wing_x = side * tx * span
            wing_y = -0.2 + (tx**2 * 0.5) # slight sweep back
            wing_z = 0.1 * math.sin(tx * math.pi)

            row = []
            for j in range(res_y):
                ty = j / (res_y - 1)
                # Offset across the chord
                offset_y = (ty - 0.5) * chord
                offset_z = 0.1 * math.sin(ty * math.pi) # airfoil bump
                row.append(bm.verts.new(Vector((wing_x, wing_y + offset_y, wing_z + offset_z))))
            verts.append(row)

        for i in range(res_x - 1):
            for j in range(res_y - 1):
                bm.faces.new((verts[i][j], verts[i+1][j], verts[i+1][j+1], verts[i][j+1]))

        # --- TRAILING EDGE FEATHERS ---
        num_feathers = 15
        for k in range(num_feathers):
            t = k / (num_feathers - 1)
            # Position at the trailing edge of the wing skin
            fx = side * t * span
            fy = -0.2 + (t**2 * 0.5) - (chord/2)
            fz = 0.1 * math.sin(t * math.pi)
            
            f_dir = Vector((side * 0.1, -0.8, -0.1))
            # Primaries are longer at the tips
            length = 0.4 + (t**2 * 0.7) if t > 0.6 else 0.3 + t*0.2
            width = 0.2 - t*0.1
            add_feather(bm, Vector((fx, fy, fz)), f_dir, length, width)

    create_wing(1)  # Right
    create_wing(-1) # Left

    # --- TAIL ---
    tail_span = 0.8
    for i in range(7):
        t = (i / 6.0) - 0.5
        start_pos = Vector((t * tail_span, -1.4, 0))
        direction = Vector((0, -0.7, -0.2 * abs(t)))
        add_feather(bm, start_pos, direction, 0.6, 0.25)

    # Finalize mesh and assign materials
    bm.to_mesh(mesh)
    bm.free()
    
    obj.data.materials.append(mats["white"])
    obj.data.materials.append(mats["gray"])
    obj.data.materials.append(mats["red_brown"])
    obj.data.materials.append(mats["dark_brown"])
    obj.data.materials.append(mats["black"])

    for poly in mesh.polygons:
        c = poly.center
        dist = abs(c.x)
        # Head
        if c.y > 1.2:
            poly.material_index = 0 # White
        # Body / Chest
        elif dist < 0.7 and c.y > -0.6:
            poly.material_index = 1 # GrayWhite
        # Tail
        elif c.y < -1.3:
            poly.material_index = 3 # DarkBrown
        # Wings gradient logic
        else:
            if dist > 3.8:
                poly.material_index = 4 # Black (Tips)
            elif dist > 2.0:
                poly.material_index = 3 # Dark Brown
            elif dist > 0.8:
                poly.material_index = 2 # Reddish Brown
            else:
                poly.material_index = 0 # White (Near body)

    # Smoothness
    subdiv = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subdiv.levels = 1
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))

if __name__ == "__main__":
    clear_scene()
    build_bird()
