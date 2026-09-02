import bpy
import bmesh
import math
from mathutils import Vector, Matrix

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    # Clean up orphan data
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_wood_material():
    """Creates a light wood-colored material."""
    mat = bpy.data.materials.new(name="LightWood")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Light wood color (pale beige/yellowish)
    bsdf.inputs['Base Color'].default_value = (0.85, 0.78, 0.62, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.7
    
    mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def add_box(bm, w, h, d, x, y, z, rx=0, ry=0, rz=0):
    """Helper to create a box in the bmesh at specific dimensions and transform."""
    # Create unit cube (-0.5 to 0.5)
    bmesh.ops.create_cube(bm, size=1.0)
    verts = bm.verts[-8:]
    
    # Construct transformation matrix (4x4)
    # Using axis keyword to avoid TypeError from previous version
    mat = Matrix.Translation((x, y, z)) @ \
          Matrix.Rotation(rx, 4, 'X') @ \
          Matrix.Rotation(ry, 4, 'Y') @ \
          Matrix.Rotation(rz, 4, 'Z') @ \
          Matrix.Scale((w, h, d), 4)

    for v in verts:
        v.co = mat @ v.co

def build_shelf():
    clear_scene()
    
    # Parameters for a wide rectangular unit
    cols = 5
    rows = 3
    cell_w = 0.4
    cell_h = 0.3
    cell_d = 0.3
    t = 0.025 # Thickness of boards
    
    total_w = cols * cell_w + (cols + 1) * t
    total_h = rows * cell_h + (rows + 1) * t
    
    bm = bmesh.new()
    
    # 1. Outer Frame
    # Bottom board (full width)
    add_box(bm, total_w, t, cell_d, total_w/2, t/2, cell_d/2)
    # Top board (full width)
    add_box(bm, total_w, t, cell_d, total_w/2, total_h - t/2, cell_d/2)
    # Left board (between top and bottom)
    add_box(bm, t, total_h - 2*t, cell_d, t/2, total_h/2, cell_d/2)
    # Right board (between top and bottom)
    add_box(bm, t, total_h - 2*t, cell_d, total_w - t/2, total_h/2, cell_d/2)

    # 2. Interior Vertical Dividers
    for i in range(1, cols):
        x_pos = t + i * (cell_w + t) + t/2
        add_box(bm, t, total_h - 2*t, cell_d, x_pos, total_h/2, cell_d/2)

    # 3. Interior Horizontal Dividers
    for j in range(1, rows):
        y_pos = t + j * (cell_h + t) + t/2
        add_box(bm, total_w - 2*t, t, cell_d, total_w/2, y_pos, cell_d/2)

    # 4. Diagonal Cross-Dividers in each cell
    for i in range(cols):
        for j in range(rows):
            # Cell center coordinates
            cx = t + i * (cell_w + t) + cell_w/2
            cy = t + j * (cell_h + t) + cell_h/2
            cz = cell_d/2
            
            # Calculate diagonal length and angle relative to x-axis
            diag_len = math.sqrt(cell_w**2 + cell_h**2)
            angle = math.atan2(cell_h, cell_w)
            
            # We use a slightly smaller length for the diagonals to avoid clipping into outer walls
            effective_len = diag_len - 0.01
            
            # Diagonal 1: \ (Top-left to bottom-right approx)
            add_box(bm, effective_len, t, cell_d, cx, cy, cz, 0, 0, angle)
            # Diagonal 2: / (Bottom-left to top-right approx)
            add_box(bm, effective_len, t, cell_d, cx, cy, cz, 0, 0, -angle)

    # Finalize mesh and object
    mesh = bpy.data.meshes.new("CellShelf")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("CellShelf", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Assign material
    wood_mat = create_wood_material()
    obj.data.materials.append(wood_mat)
    
    # Center the object at origin (offset by half its total dimensions)
    obj.location = Vector((-total_w/2, -total_h/2, -cell_d/2))

if __name__ == "__main__":
    build_shelf()
