import bpy
import bmesh
import math

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_wood_material():
    """Creates a dark wood material."""
    mat = bpy.data.materials.new(name="DarkWood")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Very dark brown for "dark wood-grain" appearance
        bsdf.inputs['Base Color'].default_value = (0.05, 0.02, 0.01, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.7
        bsdf.inputs['Specular IOR Level'].default_value = 0.1
    return mat

def create_beam(name, size, location, material):
    """Creates a rectangular beam (box)."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    # Scale the cube to match the requested beam dimensions
    for v in bm.verts:
        v.co.x *= size[0] / 2
        v.co.y *= size[1] / 2
        v.co.z *= size[2] / 2
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    obj.data.materials.append(material)
    return obj

def create_peg(name, radius, height, location, material):
    """Creates a cylindrical peg."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Use create_cone for cylinders in Blender's BMesh
    bmesh.ops.create_cone(
        bm, 
        cap_ends=True, 
        segments=16, 
        radius1=radius, 
        radius2=radius, 
        depth=height
    )
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Dimensions
    width = 0.6        # X axis
    depth = 0.25       # Y axis
    thickness = 0.03   # Wood thickness (W, H)
    peg_radius = 0.012
    peg_height = 0.18
    num_pegs_per_row = 7
    
    mat = create_wood_material()
    
    # --- Base Frame Construction ---
    # Front and Back Long Rails (along X)
    y_pos = (depth - thickness) / 2
    create_beam("RailFront", (width, thickness, thickness), (0, y_pos, 0), mat)
    create_beam("RailBack", (width, thickness, thickness), (0, -y_pos, 0), mat)
    
    # End Rails (along Y)
    x_pos = (width - thickness) / 2
    inner_depth = depth - (2 * thickness)
    create_beam("RailLeft", (thickness, inner_depth, thickness), (-x_pos, 0, 0), mat)
    create_beam("RailRight", (thickness, inner_depth, thickness), (x_pos, 0, 0), mat)
    
    # Horizontal Crossbars for structural support (connecting Front to Back)
    num_cross = 3 # Middle supports
    for i in range(1, num_cross):
        cx = -width/2 + (i * (width / (num_cross + 1)))
        create_beam(f"CrossBar_{i}", (thickness, inner_depth, thickness), (cx, 0, 0), mat)

    # --- Dowel Pegs Construction ---
    # Position pegs on top of the rails.
    # The base rails are centered at z=0 with height 'thickness', so the top surface is at z = thickness/2.
    z_offset = (thickness / 2) + (peg_height / 2)
    
    peg_margin = 0.05 # Padding from edges of the rack
    start_x = -width/2 + peg_margin
    end_x = width/2 - peg_margin
    spacing = (end_x - start_x) / (num_pegs_per_row - 1)

    for i in range(num_pegs_per_row):
        px = start_x + (i * spacing)
        # Front row of pegs
        create_peg(f"PegF_{i}", peg_radius, peg_height, (px, y_pos, z_offset), mat)
        # Back row of pegs
        create_peg(f"PegB_{i}", peg_radius, peg_height, (px, -y_pos, z_offset), mat)

if __name__ == "__main__":
    main()
