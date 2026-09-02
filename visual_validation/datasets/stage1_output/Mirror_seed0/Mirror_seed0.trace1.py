import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Removes all objects from the current scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple BSDF material with a specific color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_mirror():
    # Parameters for the mirror dimensions
    WIDTH = 0.8
    HEIGHT = 2.2
    DEPTH = 0.05  # Thickness of the frame
    BORDER_WIDTH = 0.04 # Width of the frame border
    GLASS_THICKNESS = 0.01 # Glass thickness
    GLASS_RECESSED = 0.01 # How far back the glass sits relative to front face

    clear_scene()

    # Materials
    # Dark Frame: Near black/dark grey
    dark_frame_mat = create_material("DarkFrame", (0.02, 0.02, 0.02, 1.0))
    # Mirror Glass: Warm cream-beige / Pale Taupe
    glass_mat = create_material("MirrorGlass", (0.85, 0.80, 0.74, 1.0))

    # --- Create the Frame using BMesh ---
    bm = bmesh.new()

    def add_box(w, h, d, pos):
        """Helper to create a box in BMesh at a specific position."""
        # Vertices for a cube of size (w, h, d) centered at local 0,0,0
        v = []
        for x in [-w/2, w/2]:
            for y in [-d/2, d/2]:
                for z in [-h/2, h/2]:
                    v.append(bm.verts.new(Vector((x, y, z)) + pos))
        
        # Face indices for a standard cube
        f_idx = [
            (0, 1, 3, 2), (4, 5, 7, 6), # bottom, top
            (0, 2, 6, 4), (1, 5, 7, 3), # left, right
            (0, 1, 5, 4), (2, 3, 7, 6)  # front, back
        ]
        for f in f_idx:
            try:
                bm.faces.new([v[i] for i in f])
            except ValueError:
                pass # Face might already exist

    # The frame is composed of four planks
    # Vertical side bars
    add_box(BORDER_WIDTH, HEIGHT, DEPTH, Vector((-WIDTH/2 + BORDER_WIDTH/2, 0, 0)))
    add_box(BORDER_WIDTH, HEIGHT, DEPTH, Vector((WIDTH/2 - BORDER_WIDTH/2, 0, 0)))
    
    # Horizontal top and bottom bars (fitting between the vertical ones)
    inner_w = WIDTH - (2 * BORDER_WIDTH)
    add_box(inner_w, BORDER_WIDTH, DEPTH, Vector((0, 0, HEIGHT/2 - BORDER_WIDTH/2)))
    add_box(inner_w, BORDER_WIDTH, DEPTH, Vector((0, 0, -HEIGHT/2 + BORDER_WIDTH/2)))

    # Clean up geometry
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
    
    # Scale to mirror glass dimensions
    scale_vec = Vector((glass_w, GLASS_THICKNESS, glass_h))
    bmesh.ops.scale(bm_glass, vec=scale_vec, verts=bm_glass.verts)
    
    # Offset the glass so it's recessed from the front of the frame
    # Frame is centered at 0 on Y axis (from -DEPTH/2 to +DEPTH/2).
    # We want the glass face to be slightly behind the front face (+DEPTH/2).
    # Recess position: Front Face (DEPTH/2) minus GLASS_RECESSED.
    # Glass center is then that value minus half its thickness.
    y_pos = (DEPTH / 2) - GLASS_RECESSED - (GLASS_THICKNESS / 2)
    bmesh.ops.translate(bm_glass, vec=Vector((0, y_pos, 0)), verts=bm_glass.verts)

    glass_mesh = bpy.data.meshes.new("MirrorGlassMesh")
    glass_obj = bpy.data.objects.new("MirrorGlass", glass_mesh)
    bpy.context.collection.objects.link(glass_obj)
    bm_glass.to_mesh(glass_mesh)
    bm_glass.free()
    
    glass_obj.data.materials.append(glass_mat)

    # Add bevel to the frame for a more realistic, high-quality look
    bevel = frame_obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.003
    bevel.segments = 3
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = 0.785 # 45 degrees

if __name__ == "__main__":
    create_mirror()
