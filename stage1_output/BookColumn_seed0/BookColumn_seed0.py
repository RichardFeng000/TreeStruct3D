import bpy
import bmesh
import math
import random

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_book_geometry(bm, height, thickness, depth):
    """
    Creates a book consisting of a page block and cover wraps.
    The geometry is centered around the origin for easier rotation later.
    """
    cover_thick = 0.003
    overhang = 0.004 # Cover extends slightly beyond pages

    # --- Page Block ---
    # Centered on X, and based at Z=0
    p_w = thickness - (cover_thick * 2)
    p_d = depth - overhang
    p_h = height - overhang
    
    # Create page block vertices
    px = [-p_w/2, p_w/2]
    py = [-p_d/2, p_d/2]
    pz = [0, p_h]
    
    pv = []
    for x in px:
        for y in py:
            for z in pz:
                pv.append(bm.verts.new((x, y, z)))

    # Page block faces (6 sides)
    # Faces defined to ensure consistency
    bm.faces.new((pv[0], pv[1], pv[3], pv[2])) # bottom/top side 1
    bm.faces.new((pv[4], pv[5], pv[7], pv[6])) # top/bottom side 2
    bm.faces.new((pv[0], pv[4], pv[6], pv[2])) 
    bm.faces.new((pv[1], pv[5], pv[7], pv[3])) 
    bm.faces.new((pv[0], pv[1], pv[5], pv[4])) 
    bm.faces.new((pv[2], pv[3], pv[7], pv[6])) 

    # --- Covers ---
    # Front Cover (X-Z plane, offset by depth/2)
    f_x = [-thickness/2, thickness/2]
    f_z = [0, height]
    f_y = depth/2
    fv = []
    for x in f_x:
        for z in f_z:
            fv.append(bm.verts.new((x, f_y, z)))
    
    fv_in = []
    for x in f_x:
        for z in f_z:
            fv_in.append(bm.verts.new((x, f_y - cover_thick, z)))
    
    bm.faces.new((fv[0], fv[1], fv[3], fv[2])) 
    bm.faces.new((fv_in[0], fv_in[2], fv_in[3], fv_in[1]))
    for i in range(4):
        bm.faces.new((fv[i], fv[(i+1)%4], fv_in[(i+1)%4], fv_in[i]))

    # Back Cover (X-Z plane, offset by -depth/2)
    b_x = [-thickness/2, thickness/2]
    b_z = [0, height]
    b_y = -depth/2
    bv = []
    for x in b_x:
        for z in b_z:
            bv.append(bm.verts.new((x, b_y, z)))
    
    bv_in = []
    for x in b_x:
        for z in b_z:
            bv_in.append(bm.verts.new((x, b_y + cover_thick, z)))

    bm.faces.new((bv[0], bv[2], bv[3], bv[1]))
    bm.faces.new((bv_in[0], bv_in[1], bv_in[3], bv_in[2]))
    for i in range(4):
        bm.faces.new((bv[i], bv[(i+1)%4], bv_in[(i+1)%4], bv_in[i]))

    # Spine (Y-Z plane, offset by -thickness/2)
    s_y = [-depth/2, depth/2]
    s_z = [0, height]
    s_x = -thickness/2
    sv = []
    for y in s_y:
        for z in s_z:
            sv.append(bm.verts.new((s_x, y, z)))
            
    sv_in = []
    for y in s_y:
        for z in s_z:
            sv_in.append(bm.verts.new((s_x + cover_thick, y, z)))

    bm.faces.new((sv[0], sv[2], sv[3], sv[1]))
    bm.faces.new((sv_in[0], sv_in[1], sv_in[3], sv_in[2]))
    for i in range(4):
        bm.faces.new((sv[i], sv[(i+1)%4], sv_in[(i+1)%4], sv_in[i]))

def setup_column():
    clear_scene()

    num_books = 12
    # Parameters for variation
    heights = (0.22, 0.35)
    thicknesses = (0.03, 0.06)
    depths = (0.14, 0.18)

    books_objects = []
    current_x = 0
    
    # Collective lean angle to make them look like they are leaning on each other
    base_lean = math.radians(12) 

    for i in range(num_books):
        h = random.uniform(*heights)
        t = random.uniform(*thicknesses)
        d = random.uniform(*depths)
        
        # Create a mesh and object for this book
        mesh = bpy.data.meshes.new(f"BookMesh_{i}")
        obj = bpy.data.objects.new(f"Book_{i}", mesh)
        bpy.context.collection.objects.link(obj)
        
        bm = bmesh.new()
        create_book_geometry(bm, h, t, d)
        bm.to_mesh(mesh)
        bm.free()

        # Rotation: Lean slightly more as we go along the row or keep it consistent
        lean_angle = base_lean + random.uniform(-0.03, 0.03)
        obj.rotation_euler.y = lean_angle

        # Positioning logic to avoid clipping and ensure ground contact
        # The books are centered on X in the mesh creation.
        # We place them such that the spine of book i touches the cover of book i-1.
        # For a tilt angle theta, the distance between centers is approx t * cos(theta).
        offset_x = t * math.cos(lean_angle)
        obj.location.x = current_x + (offset_x / 2)
        obj.location.y = 0
        obj.location.z = 0 # Since geometry base is at z=0, rotation happens around the bottom edge

        books_objects.append(obj)
        current_x += offset_x

    # Join all books into one object for final output
    bpy.ops.object.select_all(action='DESELECT')
    for b in books_objects:
        b.select_set(True)
    
    bpy.context.view_layer.objects.active = books_objects[0]
    bpy.ops.object.join()
    
    final_obj = bpy.context.view_layer.objects.active
    final_obj.name = "BookColumn"

    # Final touch: bevel for realism
    bev = final_obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.002
    bev.segments = 3

if __name__ == "__main__":
    setup_column()
