import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Removes all objects from the current scene."""
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, color):
    """Creates a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_book(index, width, depth, thickness, position, rotation, cover_color):
    """
    Creates a book as a single mesh with two materials (pages and cover).
    """
    # Dimensions
    cover_thick = 0.2  # Visible thickness of the covers
    overhang = 0.3     # How much the cover extends beyond pages
    
    # Materials
    page_mat = bpy.data.materials.get("PageMat") or create_material("PageMat", (0.9, 0.85, 0.7, 1.0))
    cover_mat = create_material(f"CoverMat_{index}", cover_color)

    bm = bmesh.new()

    def add_box(w, d, t, offset, mat_index):
        # Create cube centered at origin then move it
        matrix = bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts[-8:]: # Only the last 8 verts created
            v.co.x *= w / 2
            v.co.y *= d / 2
            v.co.z *= t / 2
            v.co += offset
        return matrix

    # Define parts: (w, d, t, offset)
    # 1. Pages block (the core)
    page_w = width - overhang * 2
    page_d = depth - overhang
    add_box(page_w, page_d, thickness, Vector((overhang, 0, 0)), 0)

    # 2. Top Cover
    add_box(width, depth, cover_thick, Vector((0, 0, (thickness / 2) + (cover_thick / 2))), 1)
    
    # 3. Bottom Cover
    add_box(width, depth, cover_thick, Vector((0, 0, -(thickness / 2) - (cover_thick / 2))), 1)

    # 4. Spine
    spine_w = cover_thick * 2 # slightly wider for visibility
    spine_d = depth
    spine_t = thickness + 2 * cover_thick
    add_box(spine_w, spine_d, spine_t, Vector((-width / 2 + (spine_w/2), 0, 0)), 1)

    # Assign materials to faces based on which part they belong to
    # Because we added boxes sequentially, we can't easily track index. 
    # Instead, we use coordinates to assign material slots.
    bm.to_mesh(bpy.data.meshes.new("temp")) # Dummy update to ensure geometry is handled
    # We will iterate over faces and assign materials based on Z height or X position
    # A better way: manually track face indices during creation
    
    # Re-do with explicit material assignment by splitting the process into separate BMesh operations 
    # but since we want one object, we'll just use a simpler method for this script:
    # Use basic bmesh.ops and then assign mat IDs based on position.

    me = bpy.data.meshes.new(f"BookMesh_{index}")
    bm.to_mesh(me)
    bm.free()
    
    obj = bpy.data.objects.new(f"Book_{index}", me)
    bpy.context.scene.collection.objects.link(obj)
    
    # Add materials to the object
    obj.data.materials.append(page_mat)
    obj.data.materials.append(cover_mat)

    # Assign material IDs based on location of face centers
    for poly in me.polygons:
        center = poly.center
        # If it's the spine or covers (far edges), use cover_mat (1)
        if abs(center.z) > (thickness / 2) or center.x < -width/4:
            poly.material_index = 1
        elif abs(center.x - overhang) < 0.1: # crude check for pages
             poly.material_index = 0
        else:
            # To be safe, use the Z height to separate covers from pages
            if abs(center.z) > (thickness/2):
                poly.material_index = 1
            else:
                poly.material_index = 0

    obj.location = position
    obj.rotation_euler = rotation
    return obj

def main():
    clear_scene()
    
    num_books = 8
    current_z = 0.0
    
    w_range = (12, 16)
    d_range = (18, 24)
    t_range = (2, 5)

    books = []
    for i in range(num_books):
        bw = random.uniform(*w_range)
        bd = random.uniform(*d_range)
        bt = random.uniform(*t_range)
        
        # Rotation: Z for the stack, and small X/Y for a natural "slump"
        rot_z = math.radians(random.uniform(-20, 20))
        rot_x = math.radians(random.uniform(-5, 5))
        rot_y = math.radians(random.uniform(-5, 5))
        rotation = Vector((rot_x, rot_y, rot_z))
        
        pos_x = random.uniform(-1.2, 1.2)
        pos_y = random.uniform(-1.2, 1.2)
        position = Vector((pos_x, pos_y, current_z + bt / 2))
        
        # Random cover color (saturated colors for better contrast)
        cover_color = (random.random(), random.random(), random.random(), 1.0)
        
        book = create_book(i, bw, bd, bt, position, rotation, cover_color)
        books.append(book)
        current_z += bt * 0.9 # Slight overlap in Z for cohesion

    # Center stack
    total_height = current_z
    center_offset = Vector((0, 0, -total_height / 2))
    for b in books:
        b.location += center_offset

if __name__ == "__main__":
    main()
