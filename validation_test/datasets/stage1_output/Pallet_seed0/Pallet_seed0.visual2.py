import bpy
import bmesh
import mathutils

def clear_scene():
    """Removes all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_wood_material():
    """Creates a rich dark brown wooden material."""
    mat = bpy.data.materials.new(name="DarkWood")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    # Dark Brown color (R, G, B)
    bsdf.inputs['Base Color'].default_value = (0.12, 0.06, 0.03, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.85
    return mat

def create_box(name, width, depth, height, location, material):
    """Creates a box mesh with given dimensions."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale to desired dimensions
    scale = mathutils.Vector((width, depth, height))
    for v in bm.verts:
        v.co *= scale
        
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    wood_mat = create_wood_material()

    # Pallet Dimensions (Meters)
    L = 1.2   # Length (Y axis)
    W = 1.0   # Width (X axis)
    plank_t = 0.025  # Plank thickness (Z)
    plank_w = 0.10   # Plank width
    block_size = 0.10 # Block size (cubic feet)
    runner_h = 0.08   # Runner height / thickness

    # Elevation logic
    z_block_center = block_size / 2
    z_runner_center = block_size + runner_h / 2
    z_top_plank_center = block_size + runner_h + plank_t / 2

    # --- BLOCK FEET (3x3 Grid) ---
    # These create the elevation needed for forklift entry on all sides.
    block_coords_x = [-W/2 + block_size/2, 0, W/2 - block_size/2]
    block_coords_y = [-L/2 + block_size/2, 0, L/2 - block_size/2]

    for bx in block_coords_x:
        for by in block_coords_y:
            create_box(
                "Block",
                block_size, block_size, block_size,
                (bx, by, z_block_center),
                wood_mat
            )

    # --- RUNNER BOARDS (Along X - Perpendicular to Top Planks) ---
    # Positioned on the blocks. Since they are raised, forklift entry is possible from long sides.
    for by in block_coords_y:
        create_box(
            "Runner",
            W, block_size, runner_h,
            (0, by, z_runner_center),
            wood_mat
        )

    # --- TOP PLANKS (Along Y - Grid of planks in one direction) ---
    num_top = 7
    spacing_x = W / (num_top + 1)
    for i in range(1, num_top + 1):
        pos_x = -W/2 + i * spacing_x
        create_box(
            "TopPlank",
            plank_w, L, plank_t,
            (pos_x, 0, z_top_plank_center),
            wood_mat
        )

    # Add subtle bevel to all pieces for realism
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
            bevel.width = 0.004
            bevel.segments = 2

if __name__ == "__main__":
    main()
