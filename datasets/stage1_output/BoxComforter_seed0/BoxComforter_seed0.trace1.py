import bpy
import bmesh
import mathutils
import random

def clear_scene():
    """Clear default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Create a simple material with a base color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_comforter():
    # Parameters
    width = 2.4
    length = 3.2
    thickness = 0.06
    rows = 5 # quilt blocks along length
    cols = 7 # quilt blocks along width
    puffiness = 0.04
    
    # Materials
    mat_peach = create_material("PeachPink", (1.0, 0.75, 0.65, 1.0))
    mat_lavender = create_material("Lavender", (0.7, 0.6, 0.9, 1.0))
    mat_cream = create_material("Cream", (0.95, 0.92, 0.8, 1.0))
    mat_blue = create_material("PaleBlue", (0.7, 0.85, 0.95, 1.0))
    materials = [mat_peach, mat_lavender, mat_cream, mat_blue]

    # Create the main body mesh
    bm = bmesh.new()
    
    # Generate grid vertices
    # We create a simple plane first
    verts = []
    for i in range(rows + 1):
        row_verts = []
        for j in range(cols + 1):
            x = (j / cols - 0.5) * width
            y = (i / rows - 0.5) * length
            row_verts.append(bm.verts.new((x, y, 0)))
        verts.append(row_verts)

    # Create initial faces
    faces = []
    for i in range(rows):
        for j in range(cols):
            v1 = verts[i][j]
            v2 = verts[i+1][j]
            v3 = verts[i+1][j+1]
            v4 = verts[i][j+1]
            f = bm.faces.new((v1, v2, v3, v4))
            faces.append(f)

    # To create the "puffed" box stitch effect:
    # We subdivide each face to get a center point and then lift it.
    # bmesh.ops.subdivide_edges creates new vertices at midpoints.
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1, use_grid_fill=True)
    
    # After subdivision, the center vertex of each original quad is a new vertex.
    # Let's identify which vertices to lift. 
    # A vertex should be lifted if it is NOT on the boundary and NOT on the original grid lines.
    # Since we did one cut, the 'original' vertices are those where coordinates are multiples of (width/cols) or (length/rows).
    for v in bm.verts:
        # Check if vertex is at a center of a box (approximate check)
        is_on_grid_x = any(abs(v.co.x - (j / cols - 0.5) * width) < 0.001 for j in range(cols + 1))
        is_on_grid_y = any(abs(v.co.y - (i / rows - 0.5) * length) < 0.001 for i in range(rows + 1))
        if not is_on_grid_x and not is_on_grid_y:
            v.co.z += puffiness

    # Assign materials based on the original block layout
    # Each original block (now 4 smaller quads) gets a color.
    material_pool = [0, 0, 0, 1, 2, 3] # indices into 'materials' list
    
    # Map each face to its original block center
    for f in bm.faces:
        center = f.calc_center_median()
        # Determine which original block this belongs to
        col_idx = int(((center.x / width) + 0.5) * cols)
        row_idx = int(((center.y / length) + 0.5) * rows)
        # Clamp indices
        col_idx = max(0, min(cols - 1, col_idx))
        row_idx = max(0, min(rows - 1, row_idx))
        
        # Use a deterministic seed for the block's color based on its position
        block_seed = row_idx * cols + col_idx
        random.seed(block_seed)
        mat_idx = random.choice(material_pool)
        f.material_index = mat_idx

    # Finalize main mesh
    mesh_data = bpy.data.meshes.new("ComforterMesh")
    bm.to_mesh(mesh_data)
    bm.free()
    
    comforter_obj = bpy.data.objects.new("Comforter", mesh_data)
    bpy.context.collection.objects.link(comforter_obj)
    
    # Assign materials to the object's material slots
    for mat in materials:
        comforter_obj.data.materials.append(mat)
    
    # Modifiers for smoothness and thickness
    subsurf = comforter_obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    
    solidify = comforter_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify.thickness = thickness
    solidify.offset = -1 # Push solidify downwards

    # Create the border strip (lavender)
    border_w = width + 0.02
    border_h = 0.35
    
    bm_border = bmesh.new()
    bmesh.ops.create_cube(bm_border, size=1.0)
    
    # Scale it to a strip
    # Dim: border_w (X), border_h (Y), thickness (Z)
    scale = mathutils.Vector((border_w / 2, border_h / 2, thickness / 2))
    for v in bm_border.verts:
        v.co *= scale
        
    # Position at the top end of comforter and fold it slightly
    offset_y = (length / 2) - (border_h * 0.4)
    for v in bm_border.verts:
        v.co.y += offset_y
        # Fold logic: bend the edge that is further "out"
        if v.co.y > 0 and abs(v.co.x) < 0.1:
            v.co.z += 0.02
        if v.co.y > offset_y + 0.1:
             v.co.z += 0.03

    border_mesh = bpy.data.meshes.new("BorderMesh")
    bm_border.to_mesh(border_mesh)
    bm_border.free()
    
    border_obj = bpy.data.objects.new("BorderStrip", border_mesh)
    bpy.context.collection.objects.link(border_obj)
    
    # Material for border (Lavender)
    border_mat = materials[1]
    border_obj.data.materials.append(border_mat)

    return comforter_obj

if __name__ == "__main__":
    clear_scene()
    create_comforter()
