import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_box(name, w, d, h, location):
    """Creates a rectangular box at the specified location with given dimensions."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    for v in bm.verts:
        v.co.x *= w
        v.co.y *= d
        v.co.z *= h
        
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    return obj

def main():
    clear_scene()
    
    # Dimensions for a low, wide TV stand
    W = 1.8      # Total Width
    D = 0.4      # Total Depth
    B_H = 0.35   # Body Height (excluding feet)
    T = 0.02     # Wood thickness
    F_H = 0.06   # Feet height
    
    parts = []

    # 1. Bottom Horizontal Plank
    bottom_z = F_H + T/2
    bottom = create_box("Bottom", W, D, T, (0, 0, bottom_z))
    parts.append(bottom)

    # 2. Top Horizontal Plank
    top_z = F_H + B_H - T/2
    top = create_box("Top", W, D, T, (0, 0, top_z))
    parts.append(top)

    # 3. Back Panel
    back_h = B_H - 2*T
    back_w = W - 2*T
    back_thickness = 0.01 
    back_z = F_H + (B_H / 2)
    back_y = -(D / 2) + (back_thickness / 2)
    back = create_box("Back", back_w, back_thickness, back_h, (0, back_y, back_z))
    parts.append(back)

    # 4. Vertical Partitions (creating 4 open compartments)
    num_compartments = 4
    num_verticals = num_compartments + 1
    inner_height = B_H - 2*T
    available_width = W - (num_verticals * T)
    comp_width = available_width / num_compartments
    
    for i in range(num_verticals):
        x_pos = (-W/2) + (T/2) + (i * (comp_width + T))
        z_pos = F_H + (inner_height / 2) + T
        y_pos = 0
        div_depth = D - back_thickness
        div = create_box(f"Divider_{i}", T, div_depth, inner_height, (x_pos, y_pos, z_pos))
        parts.append(div)

    # 5. Feet
    foot_size = 0.04
    foot_z = F_H / 2
    off_x = (W / 2) - foot_size/2
    off_y = (D / 2) - foot_size/2
    
    foot_coords = [
        (off_x, off_y, foot_z),
        (-off_x, off_y, foot_z),
        (off_x, -off_y, foot_z),
        (-off_x, -off_y, foot_z),
    ]
    
    for i, coord in enumerate(foot_coords):
        foot = create_box(f"Foot_{i}", foot_size, foot_size, F_H, coord)
        parts.append(foot)

    # Join all parts into one object
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:
        p.select_set(True)
    
    if parts:
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.join()
        final_obj = bpy.context.active_object
        final_obj.name = "TV_Stand"
        
        # Add bevel for realism
        bev = final_obj.modifiers.new(name="Bevel", type='BEVEL')
        bev.width = 0.004
        bev.segments = 3

    # Material: Pale Peach-Blond Wood Finish
    mat = bpy.data.materials.new(name="PeachBlondWood")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    # A pale, warm peach-blonde color (R=0.92, G=0.85, B=0.74)
    bsdf.inputs['Base Color'].default_value = (0.92, 0.85, 0.74, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.6
    
    if bpy.context.active_object:
        bpy.context.active_object.data.materials.append(mat)

if __name__ == "__main__":
    main()
