import bpy
import bmesh
import math
import random

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_book_mesh(bm, height, thickness, depth, offset):
    """
    Adds a book to the bmesh at the specified offset.
    A book consists of a page block and a slightly larger cover wrap.
    """
    cover_thickness = 0.003
    overhang = 0.002

    # --- Page Block ---
    p_w = thickness - (cover_thickness * 2)
    p_d = depth - overhang
    p_h = height - overhang

    # Create page block vertices
    # Offset by 'offset' on X axis
    ox, oy, oz = offset, 0, 0
    
    # Vertices for the pages
    pv = []
    for x in [ox + cover_thickness, ox + thickness - cover_thickness]:
        for y in [oy, oy + p_d]:
            for z in [oz, oz + p_h]:
                pv.append(bm.verts.new((x, y, z)))

    # Page block faces
    bm.faces.new((pv[0], pv[1], pv[3], pv[2])) # back
    bm.faces.new((pv[4], pv[5], pv[7], pv[6])) # front
    bm.faces.new((pv[0], pv[4], pv[6], pv[2])) # left (spine)
    bm.faces.new((pv[1], pv[5], pv[7], pv[3])) # right
    bm.faces.new((pv[0], pv[1], pv[5], pv[4])) # bottom
    bm.faces.new((pv[2], pv[3], pv[7], pv[6])) # top

    # --- Cover (Front, Back, Spine) ---
    # We create the cover as a shell that slightly wraps around the pages
    # Front Cover
    f_v = []
    for x in [ox, ox + thickness]:
        for z in [oz - overhang/2, oz + p_h + overhang/2]:
            f_v.append(bm.verts.new((x, oy + depth, z)))
    # Give front cover some thickness
    f_v_in = []
    for x in [ox, ox + thickness]:
        for z in [oz - overhang/2, oz + p_h + overhang/2]:
            f_v_in.append(bm.verts.new((x, oy + depth - cover_thickness, z)))
    
    bm.faces.new((f_v[0], f_v[1], f_v[3], f_v[2])) 
    bm.faces.new((f_v_in[0], f_v_in[2], f_v_in[3], f_v_in[1]))
    for i in range(4):
        bm.faces.new((f_v[i], f_v[(i+1)%4], f_v_in[(i+1)%4], f_v_in[i]))

    # Back Cover
    b_v = []
    for x in [ox, ox + thickness]:
        for z in [oz - overhang/2, oz + p_h + overhang/2]:
            b_v.append(bm.verts.new((x, oy, z)))
    b_v_in = []
    for x in [ox, ox + thickness]:
        for z in [oz - overhang/2, oz + p_h + overhang/2]:
            b_v_in.append(bm.verts.new((x, oy + cover_thickness, z)))

    bm.faces.new((b_v[0], b_v[2], b_v[3], b_v[1]))
    bm.faces.new((b_v_in[0], b_v_in[1], b_v_in[3], b_v_in[2]))
    for i in range(4):
        bm.faces.new((b_v[i], b_v[(i+1)%4], b_v_in[(i+1)%4], b_v_in[i]))

    # Spine Cover
    s_v = []
    for y in [oy, oy + depth]:
        for z in [oz - overhang/2, oz + p_h + overhang/2]:
            s_v.append(bm.verts.new((ox, y, z)))
    s_v_in = []
    for y in [oy, oy + depth]:
        for z in [oz - overhang/2, oz + p_h + overhang/2]:
            s_v_in.append(bm.verts.new((ox + cover_thickness, y, z)))

    bm.faces.new((s_v[0], s_v[2], s_v[3], s_v[1]))
    bm.faces.new((s_v_in[0], s_v_in[1], s_v_in[3], s_v_in[2]))
    for i in range(4):
        bm.faces.new((s_v[i], s_v[(i+1)%4], s_v_in[(i+1)%4], s_v_in[i]))

def setup_column():
    clear_scene()

    num_books = 12
    mesh = bpy.data.meshes.new("BookColumn")
    obj = bpy.data.objects.new("BookColumn", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    current_x = 0
    heights = (0.20, 0.30)
    thicknesses = (0.03, 0.07)
    depths = (0.14, 0.18)

    # We build a temporary set of books then apply leaning transformation logic
    # to the vertices since we want a single mesh.
    # However, it's easier to create them as separate objects and join them at the end.
    
    temp_books = []
    for i in range(num_books):
        h = random.uniform(*heights)
        t = random.uniform(*thicknesses)
        d = random.uniform(*depths)
        
        # Create temporary object for each book to handle rotation easily
        b_mesh = bpy.data.meshes.new(f"TempBook_{i}")
        b_obj = bpy.data.objects.new(f"TempBook_{i}", b_mesh)
        bpy.context.collection.objects.link(b_obj)
        
        # Use BMesh to construct the geometry for this book
        bm_book = bmesh.new()
        create_book_mesh(bm_book, h, t, d, 0) # Offset handled by location
        bm_book.to_mesh(b_mesh)
        bm_book.free()

        # Position
        b_obj.location.x = current_x + (t / 2)
        b_obj.location.y = d / 2
        b_obj.location.z = h / 2

        # Leaning logic: all books lean in a general direction to look supported
        # Book 0 is the "anchor" on the left, others lean towards it or away.
        # Let's make them lean collectively to the right (positive X)
        lean_angle = math.radians(12 + random.uniform(-3, 3))
        b_obj.rotation_euler.y = lean_angle
        
        # Adjust location so they sit on ground after rotation
        # Offset Z by height/2 * sin(lean) to keep bottom at z=0
        b_obj.location.z = (h / 2) + (h / 2) * math.sin(lean_angle)
        # Adjust X so they aren't floating apart too much due to tilt
        b_obj.location.x -= (h / 2) * math.sin(lean_angle)

        temp_books.append(b_obj)
        current_x += t * 0.9 # Slight overlap for compactness

    # Join all books into one mesh
    bpy.ops.object.select_all(action='DESELECT')
    for b in temp_books:
        b.select_set(True)
    
    bpy.context.view_layer.objects.active = temp_books[0]
    bpy.ops.object.join()
    
    final_obj = bpy.context.view_layer.objects.active
    final_obj.name = "BookColumn"

    # Apply a bevel modifier to the final joined object for realism
    bev = final_obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.0015
    bev.segments = 2

if __name__ == "__main__":
    setup_column()
