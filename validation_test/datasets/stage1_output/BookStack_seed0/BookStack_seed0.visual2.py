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

def create_book_mesh(width, depth, thickness, cover_color):
    """Creates a single book mesh with pages and covers."""
    # Parameters for a believable book
    cover_thick = 0.15
    overhang = 0.2
    
    bm = bmesh.new()

    def add_box(w, d, t, offset, mat_idx):
        # Create cube and scale it
        bmesh.ops.create_cube(bm, size=1.0)
        verts = bm.verts[-8:]
        for v in verts:
            v.co.x *= w / 2
            v.co.y *= d / 2
            v.co.z *= t / 2
            v.co += offset
        # Assign material to the faces of this box
        faces = bm.faces[-6:]
        for f in faces:
            f.material_index = mat_idx

    # 1. Pages (The core block) - Index 0
    # Slightly smaller than cover
    add_box(width, depth, thickness, Vector((overhang/2, 0, 0)), 0)

    # 2. Top Cover - Index 1
    add_box(width + overhang, depth + overhang, cover_thick, 
            Vector((0, 0, (thickness / 2) + (cover_thick / 2)), 1))
    
    # 3. Bottom Cover - Index 1
    add_box(width + overhang, depth + overhang, cover_thick, 
            Vector((0, 0, -(thickness / 2) - (cover_thick / 2)), 1))

    # 4. Spine - Index 1
    spine_w = cover_thick + overhang/2
    add_box(spine_w, depth + overhang, thickness + 2 * cover_thick, 
            Vector((-width / 2 - (overhang / 2) - spine_w / 2, 0, 0), 1))

    mesh = bpy.data.meshes.new("BookMesh")
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def main():
    clear_scene()
    
    # Materials
    page_mat = create_material("PageMat", (0.95, 0.9, 0.8, 1.0))
    
    num_books = 7
    current_z = 0.0
    
    w_range = (6, 8)
    d_range = (9, 11)
    t_range = (0.5, 1.2)

    books = []
    for i in range(num_books):
        bw = random.uniform(*w_range)
        bd = random.uniform(*d_range)
        bt = random.uniform(*t_range)
        
        # Rotation: slight offsets for a natural look
        rot_z = math.radians(random.uniform(-15, 15))
        rot_x = math.radians(random.uniform(-3, 3))
        rot_y = math.radians(random.uniform(-3, 3))
        
        # Random position offset in X and Y
        pos_x = random.uniform(-0.8, 0.8)
        pos_y = random.uniform(-0.8, 0.8)
        
        # Random cover color
        cover_color = (random.random(), random.random(), random.random(), 1.0)
        cov_mat = create_material(f"CoverMat_{i}", cover_color)
        
        mesh = create_book_mesh(bw, bd, bt, cover_color)
        obj = bpy.data.objects.new(f"Book_{i}", mesh)
        bpy.context.scene.collection.objects.link(obj)
        
        # Add materials to the object in order (0: pages, 1: cover)
        obj.data.materials.append(page_mat)
        obj.data.materials.append(cov_mat)

        obj.location = Vector((pos_x, pos_y, current_z + bt / 2))
        obj.rotation_euler = (rot_x, rot_y, rot_z)
        
        books.append(obj)
        # Stack books: increment z by book thickness with a tiny overlap for stability
        current_z += bt * 0.95

    # Center the entire stack around origin
    total_height = current_z
    center_offset = Vector((0, 0, -total_height / 2))
    for b in books:
        b.location += center_offset

if __name__ == "__main__":
    main()
