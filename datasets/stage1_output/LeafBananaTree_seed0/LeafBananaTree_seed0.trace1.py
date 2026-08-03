import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene of all objects."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_leaf_materials():
    """Creates materials for the upper and lower surfaces of the leaf."""
    mat_top = bpy.data.materials.new(name="BananaLeaf_Top")
    mat_top.use_nodes = True
    nodes_top = mat_top.node_tree.nodes
    bsdf_top = nodes_top.get("Principled BSDF")
    if bsdf_top:
        bsdf_top.inputs['Base Color'].default_value = (0.2, 0.6, 0.1, 1.0)
        bsdf_top.inputs['Roughness'].default_value = 0.3

    mat_bot = bpy.data.materials.new(name="BananaLeaf_Bottom")
    mat_bot.use_nodes = True
    nodes_bot = mat_bot.node_tree.nodes
    bsdf_bot = nodes_bot.get("Principled BSDF")
    if bsdf_bot:
        bsdf_bot.inputs['Base Color'].default_value = (0.05, 0.2, 0.05, 1.0)
        bsdf_bot.inputs['Roughness'].default_value = 0.6

    return mat_top, mat_bot

def build_banana_leaf():
    # Parameters for a broad, large leaf
    length = 7.0
    width_max = 2.8
    res_u = 120      # Length resolution (along midrib)
    res_v = 64       # Width resolution (across blade)
    thickness = 0.015
    
    bm = bmesh.new()

    grid = []
    
    for i in range(res_u):
        # u from -1 to 1 along length
        u = ((i / (res_u - 1)) * 2.0) - 1.0 
        
        # Elliptical/tapered width factor
        w_factor = math.sqrt(max(0, 1.0 - u*u))
        # Adjust the shape to be more "leaf-like" (blunter at center)
        current_width = w_factor * width_max
        
        row = []
        for j in range(res_v):
            # v from -1 to 1 across width
            v = ((j / (res_v - 1)) * 2.0) - 1.0 
            
            # Basic coordinates
            x = v * current_width * 0.5
            y = u * (length * 0.5)
            z = 0.0
            
            # 1. Prominent Midrib: Central structural ridge
            midrib_influence = math.exp(- (v**2) * 20.0)
            z += midrib_influence * 0.2

            # 2. Fine Parallel Lateral Veins: Ridges running lengthwise
            # These are parallel to the midrib, so they vary with v, not u
            vein_freq = 30.0 
            vein_amp = 0.025
            z += math.sin(v * vein_freq) * vein_amp * (1.0 - abs(u)*0.5)

            # 3. Organic Curvature
            # Gentle downward bend along the length
            z -= (u**2) * 0.6
            # Widthwise droop: edges curl down more than center
            z -= (v**2) * 0.4 * (1.0 - abs(u)*0.5)
            # Twist/S-curve for natural look
            x += math.sin(y * 0.6) * 0.8
            z += math.cos(y * 0.4) * 0.3

            vert = bm.verts.new(Vector((x, y, z)))
            row.append(vert)
        grid.append(row)

    # Top Surface Faces
    top_faces = []
    for i in range(res_u - 1):
        for j in range(res_v - 1):
            face = bm.faces.new([
                grid[i][j], 
                grid[i+1][j], 
                grid[i+1][j+1], 
                grid[i][j+1]
            ])
            top_faces.append(face)

    # Bottom Surface: Offset the top surface slightly along -Z (approx normal)
    bot_grid = []
    for i in range(res_u):
        row = []
        for j in range(res_v):
            co = grid[i][j].co
            new_co = co + Vector((0, 0, -thickness))
            vert = bm.verts.new(new_co)
            row.append(vert)
        bot_grid.append(row)

    # Bottom Surface Faces (reversed winding for normals)
    bottom_faces = []
    for i in range(res_u - 1):
        for j in range(res_v - 1):
            face = bm.faces.new([
                bot_grid[i][j+1], 
                bot_grid[i+1][j+1], 
                bot_grid[i+1][j], 
                bot_grid[i][j]
            ])
            bottom_faces.append(face)

    # Rim / Edges: Connecting Top and Bottom grids to make it manifold
    # Lengthwise edges (left and right sides)
    for i in range(res_u - 1):
        # Left edge
        bm.faces.new([grid[i][0], grid[i+1][0], bot_grid[i+1][0], bot_grid[i][0]])
        # Right edge
        bm.faces.new([grid[i][res_v-1], bot_grid[i][res_v-1], bot_grid[i+1][res_v-1], grid[i+1][res_v-1]])

    # Widthwise edges (tip and base)
    for j in range(res_v - 1):
        # Base edge
        bm.faces.new([grid[0][j], bot_grid[0][j], bot_grid[0][j+1], grid[0][j+1]])
        # Tip edge
        bm.faces.new([grid[res_u-1][j], grid[res_u-1][j+1], bot_grid[res_u-1][j+1], bot_grid[res_u-1][j]])

    mesh = bpy.data.meshes.new("BananaLeafMesh")
    bm.to_mesh(mesh)
    
    top_indices = [f.index for f in top_faces]
    bottom_indices = [f.index for f in bottom_faces]
    bm.free()
    
    obj = bpy.data.objects.new("BananaLeaf", mesh)
    bpy.context.collection.objects.link(obj)
    return obj, top_indices, bottom_indices

def assign_materials(obj, mat_top, mat_bot, top_indices, bot_indices):
    obj.data.materials.append(mat_top)
    obj.data.materials.append(mat_bot)
    for idx in top_indices:
        if idx < len(obj.data.polygons):
            obj.data.polygons[idx].material_index = 0
    for idx in bot_indices:
        if idx < len(obj.data.polygons):
            obj.data.polygons[idx].material_index = 1

def main():
    clear_scene()
    
    mat_top, mat_bot = create_leaf_materials()
    leaf_obj, top_indices, bot_indices = build_banana_leaf()
    
    assign_materials(leaf_obj, mat_top, mat_bot, top_indices, bot_indices)
    
    bpy.context.view_layer.objects.active = leaf_obj
    bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')
    leaf_obj.location = (0, 0, 0)
    
    bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    main()
