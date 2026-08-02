import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Removes all existing objects, meshes, and materials."""
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_book(name, width, depth, thickness):
    """Creates a high-fidelity book mesh with separate geometry for pages and covers."""
    cover_thickness = 0.05
    overhang = 0.1
    spine_width = 0.2
    
    bm = bmesh.new()

    # --- Pages Block ---
    # The core of the book
    page_w = width - overhang
    page_d = depth - overhang
    page_t = thickness - (cover_thickness * 2)
    
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * page_w / 2, v.co.y * page_d / 2, v.co.z * page_t / 2))

    # --- Covers ---
    # We'll create the covers as separate slabs and merge them into the same BMesh
    def add_slab(w, d, t, pos):
        bmesh.ops.create_cube(bm, size=1.0)
        verts = bm.verts[-8:]
        for v in verts:
            v.co = Vector((v.co.x * w / 2 + pos.x, v.co.y * d / 2 + pos.y, v.co.z * t / 2 + pos.z))

    # Top cover
    add_slab(width, depth, cover_thickness, Vector((0, 0, (page_t / 2) + (cover_thickness / 2))) )
    # Bottom cover
    add_slab(width, depth, cover_thickness, Vector((0, 0, -(page_t / 2) - (cover_thickness / 2))))
    # Spine
    # The spine wraps from the bottom cover, up the side, to the top cover
    spine_h = thickness
    add_slab(spine_width, depth, spine_h, Vector((-width / 2 - spine_width / 2 + overhang/2, 0, 0)))

    # Beveling for realism
    # To bevel, we need to ensure all geometry is merged or handled carefully. 
    # Since these are separate cubes in the same BMesh, they aren't connected.
    # We apply a small bevel to vertices of each segment if possible, but for simplicity
    # and robustness in this script, we will rely on clean geometric separation.
    
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def main():
    clear_scene()
    
    num_books = 8
    current_z = 0.0
    
    # Dimension ranges for variety
    w_range = (4.0, 6.0)
    d_range = (5.0, 7.0)
    t_range = (0.4, 1.2)

    books = []
    
    for i in range(num_books):
        # Randomize dimensions
        bw = random.uniform(*w_range)
        bd = random.uniform(*d_range)
        bt = random.uniform(*t_range)
        
        # Create mesh and object
        mesh = create_book(f"BookMesh_{i}", bw, bd, bt)
        obj = bpy.data.objects.new(f"Book_{i}", mesh)
        bpy.context.scene.collection.objects.link(obj)
        
        # Random rotational offsets for a "natural pile" look
        rot_z = math.radians(random.uniform(-20, 20))
        rot_x = math.radians(random.uniform(-5, 5))
        rot_y = math.radians(random.uniform(-5, 5))
        
        # Random positional offsets (keep them somewhat centered)
        pos_x = random.uniform(-1.0, 1.0)
        pos_y = random.uniform(-1.0, 1.0)
        
        obj.location = Vector((pos_x, pos_y, current_z + bt / 2))
        obj.rotation_euler = (rot_x, rot_y, rot_z)
        
        books.append(obj)
        
        # Increment Z height for the next book in the stack
        # We use a slight overlap/compression factor for stability look
        current_z += bt * 0.92

    # Center the entire assembly around the origin (0,0,0)
    total_height = current_z
    center_offset = Vector((0, 0, -total_height / 2))
    for b in books:
        b.location += center_offset

if __name__ == "__main__":
    main()
