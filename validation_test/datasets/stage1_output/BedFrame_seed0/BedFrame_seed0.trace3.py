import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple material with a specific color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Base Color'].default_value = color
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def add_box(bm, size, location):
    """Adds a box to the bmesh at a specific location."""
    bmesh.ops.create_cube(bm, size=1.0)
    verts = bm.verts[-8:]
    loc_vec = Vector(location)
    for v in verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
        v.co += loc_vec

def add_tapered_leg(bm, top_rad, bot_rad, height, location):
    """Adds a tapered leg to the bmesh."""
    # create_cone is centered at origin along Z axis.
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=bot_rad, radius2=top_rad, depth=height)
    verts = bm.verts[-34:] # 16*2 + 2 caps (approximate based on standard cone ops)
    # Actually let's just grab all vertices created in the last operation
    # Better: since we know it's a cone, let's iterate through new verts.
    loc_vec = Vector(location)
    for v in verts:
        v.co.z -= height / 2 # Shift to grow downwards from location if needed, 
        # but usually, the center is at origin. Let's make it sit on ground.
        v.co += loc_vec

def add_cylinder(bm, radius, height, location):
    """Adds a cylinder (accent ring) to the bmesh."""
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=radius, radius2=radius, depth=height)
    verts = bm.verts[-34:]
    loc_vec = Vector(location)
    for v in verts:
        v.co += loc_vec

def add_carved_panel(bm, width, height, depth, location):
    """Adds a decorative carved panel (frame + recessed center)."""
    # Outer Frame
    add_box(bm, (width, depth, height), location)
    
    # Recessed part: we create another box that slightly overlaps the first 
    # and would be handled by boolean or just visually placed. 
    # To keep it procedural without booleans, we'll build a frame of sticks.
    frame_thickness = width * 0.1
    # Top rail
    add_box(bm, (width, depth*1.2, frame_thickness), 
            (location[0], location[1], location[2] + height/2 - frame_thickness/2))
    # Bottom rail
    add_box(bm, (width, depth*1.2, frame_thickness), 
            (location[0], location[1], location[2] - height/2 + frame_thickness/2))
    # Left rail
    add_box(bm, (frame_thickness, depth*1.2, height), 
            (location[0] - width/2 + frame_thickness/2, location[1], location[2]))
    # Right rail
    add_box(bm, (frame_thickness, depth*1.2, height), 
            (location[0] + width/2 - frame_thickness/2, location[1], location[2]))
    
    # Recessed Center Panel
    inner_w = width - 2 * frame_thickness
    inner_h = height - 2 * frame_thickness
    inner_d = depth * 0.6
    add_box(bm, (inner_w, inner_d, inner_h), location)

def main():
    clear_scene()
    
    # Dimensions
    bed_width = 1.6
    bed_length = 2.0
    hb_height = 1.4
    fb_height = 0.7
    leg_height = 0.35
    post_thick = 0.08
    rail_thick = 0.06
    
    # Materials
    wood_mat = create_material("Wood", (0.2, 0.1, 0.05, 1.0))
    metal_mat = create_material("Metal", (0.8, 0.8, 0.8, 1.0))

    # --- WOODEN STRUCTURE ---
    bm_wood = bmesh.new()
    
    # Headboard Posts
    add_box(bm_wood, (post_thick, post_thick, hb_height), (-bed_width/2, -bed_length/2, hb_height/2))
    add_box(bm_wood, (post_thick, post_thick, hb_height), (bed_width/2, -bed_length/2, hb_height/2))
    # Headboard Top Rail
    add_box(bm_wood, (bed_width, post_thick, post_thick), (0, -bed_length/2, hb_height))
    # Headboard Decorative Panel
    add_carved_panel(bm_wood, bed_width * 0.8, hb_height * 0.5, 0.04, (0, -bed_length/2, hb_height * 0.65))

    # Footboard Posts
    add_box(bm_wood, (post_thick, post_thick, fb_height), (-bed_width/2, bed_length/2, fb_height/2))
    add_box(bm_wood, (post_thick, post_thick, fb_height), (bed_width/2, bed_length/2, fb_height/2))
    # Footboard Top Rail
    add_box(bm_wood, (bed_width, post_thick, post_thick), (0, bed_length/2, fb_height))
    # Footboard Decorative Panel
    add_carved_panel(bm_wood, bed_width * 0.8, fb_height * 0.3, 0.03, (0, bed_length/2, fb_height * 0.45))

    # Side Rails
    # Y axis is length. Posts are at -bed_length/2 and +bed_length/2.
    rail_len = bed_length - post_thick * 2
    add_box(bm_wood, (post_thick, rail_len, rail_thick), (-bed_width/2, 0, leg_height + rail_thick/2))
    add_box(bm_wood, (post_thick, rail_len, rail_thick), (bed_width/2, 0, leg_height + rail_thick/2))

    # Legs
    leg_coords = [(-bed_width/2, -bed_length/2), (bed_width/2, -bed_length/2), 
                  (-bed_width/2, bed_length/2), (bed_width/2, bed_length/2)]
    for x, y in leg_coords:
        # Leg center is at height / 2 to make the bottom touch Z=0
        add_tapered_leg(bm_wood, post_thick*0.7, post_thick*0.4, leg_height, (x, y, leg_height/2))

    # Slats
    num_slats = 14
    slat_w = 0.05
    slat_d = 0.03
    available_len = bed_length - post_thick*2
    gap = (available_len - num_slats * slat_w) / (num_slats + 1)
    for i in range(num_slats):
        # Calculate y center for each slat
        y_pos = (-bed_length/2) + post_thick + gap * (i+1) + (slat_w * i)/2 # naive, let's be precise
        y_actual = (-bed_length/2) + post_thick + (i * (slat_w + gap)) + gap/2 + slat_w/2
        add_box(bm_wood, (bed_width - post_thick*2, slat_w, slat_d), (0, y_actual, leg_height + rail_thick/2))

    # Finalize Wood Mesh
    mesh_wood = bpy.data.meshes.new("BedFrame_Wood")
    bm_wood.to_mesh(mesh_wood)
    bm_wood.free()
    obj_wood = bpy.data.objects.new("BedFrame_Wood", mesh_wood)
    bpy.context.collection.objects.link(obj_wood)
    obj_wood.data.materials.append(wood_mat)

    # --- METAL ACCENTS ---
    bm_metal = bmesh.new()
    for x, y in leg_coords:
        # Ring at top of leg (near rail)
        add_cylinder(bm_metal, post_thick * 0.55, 0.02, (x, y, leg_height))
        # Ring at bottom of leg (near floor)
        add_cylinder(bm_metal, post_thick * 0.45, 0.02, (x, y, 0.05))

    mesh_metal = bpy.data.meshes.new("BedFrame_Metal")
    bm_metal.to_mesh(mesh_metal)
    bm_metal.free()
    obj_metal = bpy.data.objects.new("BedFrame_Metal", mesh_metal)
    bpy.context.collection.objects.link(obj_metal)
    obj_metal.data.materials.append(metal_mat)

if __name__ == "__main__":
    main()
