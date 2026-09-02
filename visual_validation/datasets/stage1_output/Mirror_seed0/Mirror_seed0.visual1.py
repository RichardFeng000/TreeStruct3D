import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Removes all objects from the current scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Creates a BSDF material with specific properties."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_mirror():
    # Parameters for the mirror dimensions
    WIDTH = 0.8
    HEIGHT = 2.2
    DEPTH = 0.04  # Thickness of the frame
    BORDER_WIDTH = 0.02 # Thinner border as per description "thin dark border"
    GLASS_THICKNESS = 0.01 
    GLASS_RECESSED = 0.005

    clear_scene()

    # Materials
    # Dark Frame: Near black, satin finish
    dark_frame_mat = create_material("DarkFrame", (0.01, 0.01, 0.01, 1.0), metallic=0.2, roughness=0.4)
    # Mirror Glass: Warm cream-beige / Pale Taupe with high reflectivity
    # Using a slightly deeper taupe to ensure the tone is visible in renders
    glass_mat = create_material("MirrorGlass", (0.82, 0.76, 0.66, 1.0), metallic=1.0, roughness=0.05)

    # --- Create the Frame using BMesh ---
    bm = bmesh.new()

    def add_box(w, h, d, pos):
        """Helper to create a box in BMesh at a specific position."""
        v = []
        for x in [-w/2, w/2]:
            for y in [-d/2, d/2]:
                for z in [-h/2, h/2]:
                    v.append(bm.verts.new(Vector((x, y, z)) + pos))
        
        f_idx = [
            (0, 1, 3, 2), (4, 5, 7, 6), # bottom, top
            (0, 2, 6, 4), (1, 5, 7, 3), # left, right
            (0, 1, 5, 4), (2, 3, 7, 6)  # front, back
        ]
        for f in f_idx:
            try:
                bm.faces.new([v[i] for i in f])
            except ValueError:
                pass

    # Frame assembly
    # Vertical side bars
    add_box(BORDER_WIDTH, HEIGHT, DEPTH, Vector((-WIDTH/2 + BORDER_WIDTH/2, 0, 0)))
    add_box(BORDER_WIDTH, HEIGHT, DEPTH, Vector((WIDTH/2 - BORDER_WIDTH/2, 0, 0)))
    
    # Horizontal bars (fitting between the vertical ones)
    inner_w = WIDTH - (2 * BORDER_WIDTH)
    add_box(inner_w, BORDER_WIDTH, DEPTH, Vector((0, 0, HEIGHT/2 - BORDER_WIDTH/2)))
    add_box(inner_w, BORDER_WIDTH, DEPTH, Vector((0, 0, -HEIGHT/2 + BORDER_WIDTH/2)))

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    
    frame_mesh = bpy.data.meshes.new("MirrorFrameMesh")
    frame_obj = bpy.data.objects.new("MirrorFrame", frame_mesh)
    bpy.context.collection.objects.link(frame_obj)
    bm.to_mesh(frame_mesh)
    bm.free()
    
    frame_obj.data.materials.append(dark_frame_mat)

    # --- Create the Mirror Glass Panel ---
    glass_w = WIDTH - (2 * BORDER_WIDTH)
    glass_h = HEIGHT - (2 * BORDER_WIDTH)
    
    bm_glass = bmesh.new()
    bmesh.ops.create_cube(bm_glass, size=1.0)
    
    scale_vec = Vector((glass_w, GLASS_THICKNESS, glass_h))
    bmesh.ops.scale(bm_glass, vec=scale_vec, verts=bm_glass.verts)
    
    # Recess the glass slightly from the front face (DEPTH/2)
    y_pos = (DEPTH / 2) - GLASS_RECESSED - (GLASS_THICKNESS / 2)
    bmesh.ops.translate(bm_glass, vec=Vector((0, y_pos, 0)), verts=bm_glass.verts)

    glass_mesh = bpy.data.meshes.new("MirrorGlassMesh")
    glass_obj = bpy.data.objects.new("MirrorGlass", glass_mesh)
    bpy.context.collection.objects.link(glass_obj)
    bm_glass.to_mesh(glass_mesh)
    bm_glass.free()
    
    glass_obj.data.materials.append(glass_mat)

    # Bevel the frame for realism
    bevel = frame_obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.002
    bevel.segments = 3
    bevel.limit_method = 'ANGLE'

if __name__ == "__main__":
    create_mirror()
