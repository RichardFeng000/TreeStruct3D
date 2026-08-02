import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene of all objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_tapered_leg(name, position, height=0.3, top_rad=0.04, bot_rad=0.02):
    """Creates a wooden tapered leg."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Create cylinder with taper
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=bot_rad, radius2=top_rad, depth=height)
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = position
    return obj

def create_box(name, size, position, material=None):
    """Creates a basic box object."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = Vector(size)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    return obj

def create_rounded_box(name, size, position, material=None, subdivs=2):
    """Creates a box with a subdivision surface modifier for rounded corners."""
    obj = create_box(name, size, position, material)
    mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    mod.levels = subdivs
    mod.render_levels = subdivs
    bpy.ops.object.shade_smooth()
    return obj

def create_slats(name, count, start_pos, end_pos, thickness, material):
    """Creates a series of decorative vertical slats."""
    container = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(container)
    
    step = (end_pos[0] - start_pos[0]) / (count + 1)
    for i in range(1, count + 1):
        x = start_pos[0] + i * step
        # Vary height slightly for decorative feel or keep constant
        h = 0.8
        leg = create_box(f"{name}_slat_{i}", (thickness, h, thickness), (x, 0, h/2), material)
        leg.parent = None # Will be parented to frame later

def build_bed():
    clear_scene()
    
    # Materials
    mat_wood = create_material("Wood", (0.2, 0.1, 0.05, 1.0))
    mat_mattress = create_material("MattressGreen", (0.1, 0.3, 0.1, 1.0))
    mat_blanket = create_material("BlanketPink", (1.0, 0.75, 0.8, 1.0))
    mat_comforter = create_material("ComforterOffWhite", (0.95, 0.92, 0.88, 1.0))
    mat_pillow = create_material("PillowWhite", (0.9, 0.9, 0.9, 1.0))

    # Dimensions
    length = 2.1
    width = 1.6
    height_headboard = 1.3
    height_footboard = 0.7
    leg_height = 0.3
    mattress_thick = 0.25
    frame_thickness = 0.1

    # Frame Legs (Tapered)
    leg_pos = [
        (length/2, width/2, leg_height/2),
        (length/2, -width/2, leg_height/2),
        (-length/2, width/2, leg_height/2),
        (-length/2, -width/2, leg_height/2)
    ]
    legs = []
    for i, pos in enumerate(leg_pos):
        l = create_tapered_leg(f"Leg_{i}", pos)
        l.data.materials.append(mat_wood)
        legs.append(l)

    # Side Rails
    rail_l = create_box("Rail_L", (length, frame_thickness, frame_thickness), (0, width/2, leg_height), mat_wood)
    rail_r = create_box("Rail_R", (length, frame_thickness, frame_thickness), (0, -width/2, leg_height), mat_wood)

    # Headboard
    hb_posts_x = length/2
    hp1 = create_box("HB_Post_L", (frame_thickness, frame_thickness, height_headboard), (hb_posts_x, width/2, height_headboard/2), mat_wood)
    hp2 = create_box("HB_Post_R", (frame_thickness, frame_thickness, height_headboard), (hb_posts_x, -width/2, height_headboard/2), mat_wood)
    hb_top = create_box("HB_Top", (frame_thickness, width, frame_thickness), (hb_posts_x, 0, height_headboard), mat_wood)
    
    # Decorative slats for headboard
    slat_count = 5
    for i in range(1, slat_count):
        y_pos = -width/2 + (width / (slat_count + 1)) * (i+1) if i < slat_count else width/2
        # Fixed calculation for spacing slats on the Y axis across the headboard width
        y_val = (width * (i / (slat_count - 1))) - width/2
        s = create_box(f"HB_Slat_{i}", (frame_thickness, frame_thickness, height_headboard - 0.2), (hb_posts_x, y_val, (height_headboard-0.2)/2), mat_wood)

    # Footboard
    fb_posts_x = -length/2
    fp1 = create_box("FB_Post_L", (frame_thickness, frame_thickness, height_footboard), (fb_posts_x, width/2, height_footboard/2), mat_wood)
    fp2 = create_box("FB_Post_R", (frame_thickness, frame_thickness, height_footboard), (fb_posts_x, -width/2, height_footboard/2), mat_wood)
    fb_top = create_box("FB_Top", (frame_thickness, width, frame_thickness), (fb_posts_x, 0, height_footboard), mat_wood)

    # Mattress
    mattress_z = leg_height + mattress_thick/2
    mattress = create_rounded_box("Mattress", (length - 0.1, width - 0.1, mattress_thick), (0, 0, mattress_z), mat_mattress)

    # Pillows
    pillow_size = (0.5, 0.3, 0.15)
    p1 = create_rounded_box("Pillow_1", pillow_size, (length/2 - 0.4, width/4, mattress_z + mattress_thick/2 + 0.05), mat_pillow)
    p2 = create_rounded_box("Pillow_2", pillow_size, (length/2 - 0.4, -width/4, mattress_z + mattress_thick/2 + 0.05), mat_pillow)

    # Blanket (Pink Layer)
    blanket_z = mattress_z + mattress_thick/2 + 0.01
    # The blanket covers from head to about 2/3 down the bed
    blanket = create_box("Blanket", (length * 0.7, width - 0.05, 0.02), (length/2 - length*0.35, 0, blanket_z), mat_blanket)
    
    # Comforter (Folded at the foot)
    # Folded comforter is usually a thicker block at the bottom
    comf_width = width - 0.1
    comf_len = length * 0.3
    comf_thick = 0.12
    comf_z = mattress_z + mattress_thick/2 + comf_thick/2
    comforter = create_rounded_box("Comforter", (comf_len, comf_width, comf_thick), (-length/2 + comf_len/2, 0, comf_z), mat_comforter)

    # Final adjustments: subtle tilt to blanket for realism
    blanket.rotation_euler[1] = math.radians(-2) # slight pitch

build_bed()
