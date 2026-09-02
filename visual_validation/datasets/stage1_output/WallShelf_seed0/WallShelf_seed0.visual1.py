import bpy
import bmesh
import math

def clear_scene():
    """Clears all objects from the current scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a Principled BSDF material with the specified RGBA color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        # Slightly adjust roughness to avoid washed-out looks in renders
        bsdf.inputs['Roughness'].default_value = 0.6
    return mat

def create_board(width, depth, thickness, material):
    """Creates the main horizontal shelf board."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    board = bpy.context.active_object
    board.name = "ShelfBoard"
    board.scale = (width, depth, thickness)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    board.data.materials.append(material)
    return board

def create_arch_bracket(br_width, br_height, br_depth, material):
    """Creates a rounded arch-shaped bracket using bmesh."""
    bm = bmesh.new()
    
    radius = br_width / 2
    rect_h = br_height - radius
    
    # Create vertices for the outer profile of the arch face (XZ plane)
    segs = 32
    
    # Bottom base points
    v1 = bm.verts.new((-radius, 0, 0))
    v2 = bm.verts.new((radius, 0, 0))
    
    # Arc points from right (angle=0) to left (angle=pi)
    arc_pts = []
    for i in range(segs + 1):
        angle = (math.pi * (i / segs))
        vx = radius * math.cos(angle)
        vz = rect_h + radius * math.sin(angle)
        arc_pts.append(bm.verts.new((vx, 0, vz)))

    # Combine into a single face: Base left -> Base right -> Arc Right-to-Left -> Base left (closed by bmesh)
    full_poly = [v1, v2] + arc_pts
    bm.faces.new(full_poly)
    
    # Extrude the face along Y axis to give it thickness/depth
    geom = bm.faces[:]
    res = bmesh.ops.extrude_face_region(bm, geom=geom)
    
    verts_ex = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts_ex, vec=(0, br_depth, 0))
    
    # Finalize mesh and create object
    mesh = bpy.data.meshes.new("ArchBracketMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Bracket", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Colors (RGBA) - Saturated slightly more to ensure visibility in renders
    black_color = (0.01, 0.01, 0.01, 1.0) # Deep dark black
    mauve_color = (0.4, 0.3, 0.5, 1.0)     # Muted purple-mauve
    
    black_mat = create_material("BlackMat", black_color)
    mauve_mat = create_material("MauveMat", mauve_color)
    
    # Board dimensions: wider and thicker for better proportions
    bw, bd, bt = 2.0, 0.4, 0.06
    board = create_board(bw, bd, bt, black_mat)
    board.location = (0, 0, 0)

    # Bracket parameters: adjusted for better visual balance
    br_width = 0.15  # Width of the arch profile
    br_height = 0.4   # Total height from base to top of arc
    br_depth = 0.35  # Depth along board's Y axis (almost full depth of board)
    
    # Symmetrically place two brackets on the surface of the board
    for side in [-1, 1]:
        bracket = create_arch_bracket(br_width, br_height, br_depth, mauve_mat)
        
        # Position: offset along X, center on Y (by subtracting half depth), 
        # and set Z to board top surface.
        offset_x = bw * 0.25
        bracket.location = (side * offset_x, -br_depth / 2, bt / 2)

if __name__ == "__main__":
    main()
