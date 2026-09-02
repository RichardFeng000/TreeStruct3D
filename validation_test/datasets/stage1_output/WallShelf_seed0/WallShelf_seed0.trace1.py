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
    """Creates a simple principled BSDF material with a specific color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
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
    
    # We define the profile in XZ plane and extrude along Y
    radius = br_width / 2
    rect_h = br_height - radius
    
    # Create vertices for the outer profile of the arch (the face)
    segs = 24
    pts = []
    
    # Bottom base points
    v1 = bm.verts.new((-radius, 0, 0))
    v2 = bm.verts.new((radius, 0, 0))
    pts.append(v1)
    pts.append(v2)
    
    # Arc points (from right to left, semi-circle on top)
    for i in range(segs + 1):
        angle = - (math.pi * (i / segs)) # from 0 to -pi (clockwise relative to center)
        # Actually simpler: angle from 0 to pi for a dome
        # Let's use: x = r*cos(t), z = rect_h + r*sin(t) where t is 0..pi
    
    # Recalculating arc points properly
    arc_pts = []
    for i in range(segs + 1):
        angle = (math.pi * (i / segs)) # 0 to pi
        vx = radius * math.cos(angle)
        vz = rect_h + radius * math.sin(angle)
        arc_pts.append(bm.verts.new((vx, 0, vz)))

    # To form a proper face polygon: v1 -> v2 -> arc_points... (but reversed for order)
    # Order: (-r,0,0), (r,0,0), then arc points from angle 0 to pi
    full_poly = [v1, v2] + arc_pts
    bm.faces.new(full_poly)
    
    # Extrude the face along Y axis
    geom = bm.faces[:]
    res = bmesh.ops.extrude_face_region(bm, geom=geom)
    
    # Translate extruded vertices by br_depth
    verts_ex = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts_ex, vec=(0, br_depth, 0))
    
    # Finalize mesh
    mesh = bpy.data.meshes.new("ArchBracketMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Bracket", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Colors (RGBA)
    black_color = (0.02, 0.02, 0.02, 1.0)
    mauve_color = (0.45, 0.38, 0.48, 1.0) # Muted purple-mauve
    
    black_mat = create_material("BlackMat", black_color)
    mauve_mat = create_material("MauveMat", mauve_color)
    
    # Board dimensions
    bw, bd, bt = 1.6, 0.3, 0.04
    board = create_board(bw, bd, bt, black_mat)
    board.location = (0, 0, 0)

    # Bracket parameters
    br_width = 0.12 # Thickness of the arch profile width
    br_height = 0.35 # Total height from base to top of arc
    br_depth = 0.25  # Extrusion depth (along board's Y axis)
    
    for side in [-1, 1]:
        bracket = create_arch_bracket(br_width, br_height, br_depth, mauve_mat)
        
        # Position: symmetrically along X, centered on Y, sitting on top of the board
        # The bracket's geometry is created from z=0 to br_height and y=0 to br_depth.
        # We want it centered at (side * offset, 0, bt/2)
        # Shift in Y by -br_depth/2 to center it on the board depth axis.
        bracket.location = (side * (bw * 0.3), -br_depth / 2, bt / 2)

if __name__ == "__main__":
    main()
