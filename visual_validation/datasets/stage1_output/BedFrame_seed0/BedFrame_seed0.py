import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
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
    # Create cube at origin and then move/scale
    bmesh.ops.create_cube(bm, size=1.0)
    verts = bm.verts[-8:] # Cubes always have 8 verts
    for v in verts:
        v.co.x *= size[0] * 0.5
        v.co.y *= size[1] * 0.5
        v.co.z *= size[2] * 0.5
        v.co += Vector(location)

def add_tapered_leg(bm, top_rad, bot_rad, height, location):
    # Capture current vertex count to identify new vertices exactly
    start_verts = len(bm.verts)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=bot_rad, radius2=top_rad, depth=height)
    new_verts = bm.verts[start_verts:]
    loc_vec = Vector(location)
    for v in new_verts:
        # Shift so the top is at location and it grows downwards
        v.co.z -= height / 2
        v.co += loc_vec

def add_cylinder(bm, radius, height, location):
    start_verts = len(bm.verts)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=radius, radius2=radius, depth=height)
    new_verts = bm.verts[start_verts:]
    loc_vec = Vector(location)
    for v in new_verts:
        v.co += loc_vec

def add_decorative_panel(bm, width, height, depth, location):
    # Frame outer edges (simulating molding)
    frame_w = 0.05
    # Top rail
    add_box(bm, (width, depth * 1.2, frame_w), (location[0], location[1], location[2] + height/2 - frame_w/2))
    # Bottom rail
    add_box(bm, (width, depth * 1.2, frame_w), (location[0], location[1], location[2] - height/2 + frame_w/2))
    # Side rails
    add_box(bm, (frame_w, depth * 1.2, height - 2*frame_w), (location[0] - width/2 + frame_w/2, location[1], location[2]))
    add_box(bm, (frame_w, depth * 1.2, height - 2*frame_w), (location[0] + width/2 - frame_w/2, location[1], location[2]))
    # Recessed center panel
    inner_w = width - 2 * frame_w
    inner_h = height - 2 * frame_w
    add_box(bm, (inner_w, depth * 0.5, inner_h), location)

def main():
    clear_scene()
    
    bed_width = 1.6
    bed_length = 2.0
    hb_height = 1.4
    fb_height = 0.7
    leg_height = 0.3
    post_thick = 0.08
    rail_thick = 0.06

    wood_mat = create_material("Wood", (0.15, 0.08, 0.04, 1.0))
    metal_mat = create_material("Metal", (0.7, 0.7, 0.7, 1.0))

    bm_wood = bmesh.new()
    
    # Headboard posts and rails
    add_box(bm_wood, (post_thick, post_thick, hb_height), (-bed_width/2, -bed_length/2, hb_height/2))
    add_box(bm_wood, (post_thick, post_thick, hb_height), (bed_width/2, -bed_length/2, hb_height/2))
    add_box(bm_wood, (bed_width, post_thick, post_thick), (0, -bed_length/2, hb_height))
    add_decorative_panel(bm_wood, bed_width * 0.85, hb_height * 0.6, 0.04, (0, -bed_length/2, hb_height * 0.6))

    # Footboard posts and rails
    add_box(bm_wood, (post_thick, post_thick, fb_height), (-bed_width/2, bed_length/2, fb_height/2))
    add_box(bm_wood, (post_thick, post_thick, fb_height), (bed_width/2, bed_length/2, fb_height/2))
    add_box(bm_wood, (bed_width, post_thick, post_thick), (0, bed_length/2, fb_height))
    add_decorative_panel(bm_wood, bed_width * 0.85, fb_height * 0.4, 0.03, (0, bed_length/2, fb_height * 0.4))

    # Side rails connecting head and foot
    rail_len = bed_length - post_thick * 2
    add_box(bm_wood, (post_thick, rail_len, rail_thick), (-bed_width/2, 0, leg_height + rail_thick/2))
    add_box(bm_wood, (post_thick, rail_len, rail_thick), (bed_width/2, 0, leg_height + rail_thick/2))

    # Tapered Legs
    leg_coords = [(-bed_width/2, -bed_length/2), (bed_width/2, -bed_length/2), 
                  (-bed_width/2, bed_length/2), (bed_width/2, bed_length/2)]
    for x, y in leg_coords:
        add_tapered_leg(bm_wood, post_thick * 0.8, post_thick * 0.5, leg_height, (x, y, leg_height))

    # Slats
    num_slats = 12
    slat_w = 0.04
    gap = (rail_len - num_slats * slat_w) / (num_slats + 1)
    for i in range(num_slats):
        y_pos = (-bed_length/2 + post_thick/2) + gap * (i+1) + (slat_w * i / 2)
        # Correcting spacing logic
        y_actual = (-bed_length/2) + post_thick + (i * (slat_w + gap)) + gap/2 + slat_w/2 - 0.01 # adjust for offset
        # Just use linear interpolation for simplicity and accuracy
        t = i / (num_slats - 1) if num_slats > 1 else 0.5
        y_interp = (-bed_length/2 + post_thick) + t * (rail_len - 2*post_thick)
        add_box(bm_wood, (bed_width - post_thick*2, slat_w, rail_thick), (0, y_interp, leg_height + rail_thick/2))

    mesh_wood = bpy.data.meshes.new("BedFrame_Wood")
    bm_wood.to_mesh(mesh_wood)
    bm_wood.free()
    obj_wood = bpy.data.objects.new("BedFrame_Wood", mesh_wood)
    bpy.context.collection.objects.link(obj_wood)
    obj_wood.data.materials.append(wood_mat)

    # Metal Accents (Rings on legs)
    bm_metal = bmesh.new()
    for x, y in leg_coords:
        add_cylinder(bm_metal, post_thick * 0.45, 0.02, (x, y, leg_height)) # Top ring
        add_cylinder(bm_metal, post_thick * 0.3, 0.02, (x, y, 0.05))      # Bottom ring

    mesh_metal = bpy.data.meshes.new("BedFrame_Metal")
    bm_metal.to_mesh(mesh_metal)
    bm_metal.free()
    obj_metal = bpy.data.objects.new("BedFrame_Metal", mesh_metal)
    bpy.context.collection.objects.link(obj_metal)
    obj_metal.data.materials.append(metal_mat)

if __name__ == "__main__":
    main()
