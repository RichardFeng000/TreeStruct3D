import bpy
import bmesh
import mathutils

def clear_scene():
    """Removes all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_wood_material():
    """Creates a very dark brown wooden material."""
    mat = bpy.data.materials.new(name="DarkWood")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    # Deep Dark Brown color: RGB (0.07, 0.03, 0.01) for maximum contrast
    bsdf.inputs['Base Color'].default_value = (0.07, 0.03, 0.01, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.8
    return mat

def create_box(name, width, depth, height, location, material):
    """Procedurally creates a box mesh with given dimensions."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
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
    block_size = 0.10 # Cube size for feet blocks
    runner_h = 0.10   # Runner height

    # Elevation constants
    z_block_base = 0.05 # Block center (half of block_size)
    z_runner_bottom = z_block_base + block_size/2 
    z_top_surface = z_runner_bottom + runner_h

    # --- BLOCK FEET ---
    # 3x3 grid of blocks to ensure structural support and 4-way entry channels
    block_coords_x = [-W/2 + block_size/2, 0, W/2 - block_size/2]
    block_coords_y = [-L/2 + block_size/2, 0, L/2 - block_size/2]

    for bx in block_coords_x:
        for by in block_coords_y:
            create_box(
                "Block",
                block_size, block_size, block_size,
                (bx, by, z_block_base),
                wood_mat
            )

    # --- RUNNER BOARDS (Internal/Support) ---
    # To allow 4-way entry, runners cannot be full width at the ends.
    # We place support beams along Y connecting blocks, and bottom boards along X.
    
    # Longitude supports (Along Y) - These are the "runners" that hold top planks
    for bx in block_coords_x:
        create_box(
            "RunnerY",
            block_size, L - block_size, runner_h,
            (bx, 0, z_runner_bottom + runner_h/2),
            wood_mat
        )

    # --- BOTTOM PLANKS ---
    # Placed along X axis to tie the runners together and provide base stability
    num_bot = 3
    for i in range(num_bot):
        pos_y = -L/2 + (i+1) * (L / (num_bot + 1))
        create_box(
            "BottomPlank",
            W, plank_w, plank_t,
            (0, pos_y, z_block_base - block_size/2 + plank_t/2),
            wood_mat
        )

    # --- TOP PLANKS ---
    # Grid of planks along the Y axis (as per description: "running in one direction")
    num_top = 7
    spacing_x = W / (num_top - 1) if num_top > 1 else W
    for i in range(num_top):
        pos_x = -W/2 + i * spacing_x
        # Clamp to width
        if pos_x > W/2: pos_x = W/2
        create_box(
            "TopPlank",
            plank_w, L, plank_t,
            (pos_x, 0, z_top_surface + plank_t/2),
            wood_mat
        )

    # Apply Bevel for realism
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
            bevel.width = 0.005
            bevel.segments = 2

if __name__ == "__main__":
    main()
