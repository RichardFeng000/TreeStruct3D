import bpy
import bmesh
import math

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a dark wood material with low specular for a matte look."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.8
        bsdf.inputs['Specular IOR Level'].default_value = 0.2
    return mat

def create_box(name, size, location, material):
    """Creates a box with a slight bevel for realism."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale to dimensions
    for v in bm.verts:
        v.co.x *= size[0] / 2
        v.co.y *= size[1] / 2
        v.co.z *= size[2] / 2
        
    # Apply a subtle bevel to all edges for wood carving look
    bmesh.ops.bevel(bm, geom=bm.edges, offset=0.005, segments=2, affect='EDGES')
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    obj.data.materials.append(material)
    return obj

def create_cylinder(name, radius, height, location, material):
    """Creates a vertical dowel peg."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, 
        cap_ends=True, 
        segments=16, 
        radius1=radius, 
        radius2=radius, 
        depth=height
    )
    
    # Bevel the top edge slightly for a rounded finish
    top_verts = [v for v in bm.verts if v.co.z > height * 0.4]
    top_edges = [e for e in bm.edges if all(v in top_verts for v in e.verts)]
    bmesh.ops.bevel(bm, geom=top_edges, offset=0.005, segments=2, affect='EDGES')

    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Dimensions
    width = 0.6       # Overall width
    depth = 0.2       # Overall depth
    thickness = 0.03  # Wood thickness
    height_base = 0.04 # Thickness of the base frame rails
    peg_radius = 0.015
    peg_height = 0.18
    num_pegs = 6      # Number of peg pairs along the width
    
    # Dark Wood Color (Dark Brown)
    dark_wood_color = (0.08, 0.04, 0.02, 1.0)
    mat = create_material("DarkWood", dark_wood_color)
    
    # --- Base Frame Construction ---
    # Long Rails (Front and Back)
    # Positioned at Y = +/- (depth - thickness)/2 to keep overall depth consistent
    y_offset = (depth - thickness) / 2
    create_box("RailFront", (width, thickness, height_base), (0, y_offset, 0), mat)
    create_box("RailBack", (width, thickness, height_base), (0, -y_offset, 0), mat)
    
    # End Rails (Left and Right)
    # These fit BETWEEN the long rails to avoid overlapping/floating issues
    x_offset = (width - thickness) / 2
    inner_depth = depth - (2 * thickness)
    create_box("RailLeft", (thickness, inner_depth, height_base), (-x_offset, 0, 0), mat)
    create_box("RailRight", (thickness, inner_depth, height_base), (x_offset, 0, 0), mat)

    # Crossbars for stability and support
    num_cross = 4
    for i in range(num_cross):
        cx = -width/2 + (i * (width / (num_cross - 1)))
        create_box(f"CrossBar_{i}", (thickness, inner_depth, height_base), (cx, 0, 0), mat)

    # --- Dowel Pegs Construction ---
    # Position pegs on top of the rails/crossbars
    peg_start_x = -width/2 + thickness*2
    peg_end_x = width/2 - thickness*2
    spacing = (peg_end_x - peg_start_x) / (num_pegs - 1)
    z_pos = (height_base / 2) + (peg_height / 2)

    for i in range(num_pegs):
        px = peg_start_x + (i * spacing)
        # Front Peg
        create_cylinder("PegF", peg_radius, peg_height, (px, y_offset, z_pos), mat)
        # Back Peg
        create_cylinder("PegB", peg_radius, peg_height, (px, -y_offset, z_pos), mat)

if __name__ == "__main__":
    main()
