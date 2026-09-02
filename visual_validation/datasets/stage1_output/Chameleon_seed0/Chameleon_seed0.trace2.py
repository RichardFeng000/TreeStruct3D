import bpy
import bmesh
import math
import random
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
    return mat

def create_chameleon():
    clear_scene()

    # Materials
    olive_green = create_material("OliveGreen", (0.15, 0.25, 0.05, 1.0))
    yellow_green = create_material("YellowGreen", (0.4, 0.6, 0.1, 1.0))
    dark_speckle = create_material("DarkSpeckle", (0.05, 0.1, 0.02, 1.0))

    # --- BODY & TAIL ASSEMBLY ---
    bm = bmesh.new()

    # Body: flattened elongated ellipsoid
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0)
    for v in bm.verts:
        v.co.x *= 0.6
        v.co.y *= 1.8
        v.co.z *= 0.4

    # Head: smaller sphere at the front
    head_center = Vector((0, 2.2, 0))
    head_res = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=16, radius=0.5)
    # Move head vertices to the center
    for v in head_res['verts']:
        v.co += head_center
        # Slightly flatten head relative to its new center
        local_co = v.co - head_center
        # We modify a copy of local coordinates to avoid drift during loop if needed, 
        # but simple additive offset then scaling works if we scale before translating or use temp vectors
    
    # Recalculate head flattening properly
    for v in head_res['verts']:
        v.co.x = head_center.x + (v.co.x - head_center.x) * 0.9
        v.co.z = head_center.z + (v.co.z - head_center.z) * 0.8

    # Tail: tapered cylinder extending from the back
    segments = 40
    rings = 12
    radius_start = 0.25
    radius_end = 0.03
    tail_length = 4.5
    start_y = -1.8

    all_tail_rings = []
    for i in range(segments + 1):
        t = i / segments
        r = radius_start * (1 - t) + radius_end * t
        y_pos = start_y - (t * tail_length)
        
        ring = []
        for j in range(rings):
            angle = (2 * math.pi / rings) * j
            vx = math.cos(angle) * r
            vz = math.sin(angle) * r
            v = bm.verts.new((vx, y_pos, vz))
            ring.append(v)
        all_tail_rings.append(ring)

    for i in range(segments):
        for j in range(rings):
            v1 = all_tail_rings[i][j]
            v2 = all_tail_rings[i+1][j]
            v3 = all_tail_rings[i+1][(j + 1) % rings]
            v4 = all_tail_rings[i][(j + 1) % rings]
            try:
                bm.faces.new((v1, v2, v3, v4))
            except ValueError:
                pass

    last_ring = all_tail_rings[-1]
    try:
        bm.faces.new(last_ring)
    except ValueError:
        pass

    # Spine Ridge: small bumps along the top of the body (Y axis from -1.8 to 2.2)
    for i in range(-15, 16):
        pos_y = (i / 15.0) * 2.0 # scaled a bit
        pos_z = 0.4 + random.uniform(-0.05, 0.05)
        # Create small bump using translate since location is not allowed in create_uvsphere
        bump_res = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=8, radius=0.08)
        for v in bump_res['verts']:
            v.co += Vector((0, pos_y, pos_z))

    # Create the main creature object
    main_mesh = bpy.data.meshes.new("ChameleonMesh")
    bm.to_mesh(main_mesh)
    bm.free()
    creature_obj = bpy.data.objects.new("Chameleon", main_mesh)
    bpy.context.collection.objects.link(creature_obj)
    creature_obj.data.materials.append(olive_green)

    # --- EYES ---
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(0.3 * side, 2.3, 0.2))
        eye = bpy.context.active_object
        eye.name = f"Eye_{'L' if side == -1 else 'R'}"
        eye.scale = (1, 1, 1.2)
        eye.data.materials.append(yellow_green)
        eye.parent = creature_obj

    # --- LIMBS & FEET ---
    def create_limb(pos, rot_z, flip_x=1):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.8, location=pos)
        limb = bpy.context.active_object
        limb.rotation_euler[1] = math.radians(45 * flip_x)
        limb.rotation_euler[2] = rot_z
        limb.data.materials.append(olive_green)
        limb.parent = creature_obj
        
        # Zygodactylous feet
        toe_offsets = [
            (0.05, 0.08, -0.1), (-0.05, 0.08, -0.1), # Group A
            (0.06, -0.07, -0.1), (-0.06, -0.07, -0.1), (0, -0.12, -0.1) # Group B
        ]
        for off in toe_offsets:
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(
                pos[0] + off[0]*flip_x, pos[1] + off[1], pos[2] + off[2] - 0.4
            ))
            toe = bpy.context.active_object
            toe.data.materials.append(olive_green)
            toe.parent = limb

    create_limb((0.6, 1.0, 0), math.radians(-30), flip_x=1)   # Front Right
    create_limb((-0.6, 1.0, 0), math.radians(30), flip_x=-1)  # Front Left
    create_limb((0.6, -1.0, 0), math.radians(-15), flip_x=1)  # Back Right
    create_limb((-0.6, -1.0, 0), math.radians(15), flip_x=-1) # Back Left

    # --- FINAL TOUCHES: TEXTURE AND SPECKLES ---
    tex = bpy.data.textures.new("SkinNoise", type='NOISE')
    tex.noise_scale = 0.1
    
    disp_mod = creature_obj.modifiers.new(name="LeatherySkin", type='DISPLACE')
    disp_mod.texture = tex
    disp_mod.strength = 0.05

    speckle_objs = []
    for _ in range(100):
        rx = random.uniform(-0.7, 0.7)
        ry = random.uniform(-6.3, 2.5)
        rz = random.uniform(-0.4, 0.6)
        if (abs(rx) < 0.6 and ry > -1.8) or (abs(rx) < 0.3 and ry <= -1.8):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03, location=(rx, ry, rz))
            s = bpy.context.active_object
            s.data.materials.append(dark_speckle)
            speckle_objs.append(s)

    bpy.ops.object.select_all(action='DESELECT')
    creature_obj.select_set(True)
    for s in speckle_objs:
        s.select_set(True)
    bpy.context.view_layer.objects.active = creature_obj
    bpy.ops.object.join()

if __name__ == "__main__":
    create_chameleon()
