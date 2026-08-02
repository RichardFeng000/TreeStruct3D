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
    # Create a cube of size 1 centered at origin
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale the vertices to match desired width, depth, and height
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
    F_H = 0.05   # Feet height
    
    # Coordinate system: X=Width, Y=Depth, Z=Height
    
    parts = []

    # 1. Bottom Horizontal Plank
    # Positioned at the bottom of the body (above feet)
    bottom_z = F_H + T/2
    bottom = create_box("Bottom", W, D, T, (0, 0, bottom_z))
    parts.append(bottom)

    # 2. Top Horizontal Plank
    top_z = F_H + B_H - T/2
    top = create_box("Top", W, D, T, (0, 0, top_z))
    parts.append(top)

    # 3. Back Panel
    # Sits inside the top and bottom, slightly recessed or flush
    back_h = B_H - 2*T
    back_w = W - 2*T
    back_thickness = 0.01  # Thinner back panel
    back_z = F_H + (B_H / 2)
    back_y = -(D / 2) + (back_thickness / 2)
    back = create_box("Back", back_w, back_thickness, back_h, (0, back_y, back_z))
    parts.append(back)

    # 4. Vertical Partitions
    num_compartments = 4
    num_verticals = num_compartments + 1
    inner_height = B_H - 2*T
    
    # Available width for gaps between vertical planks
    available_width = W - (num_verticals * T)
    comp_width = available_width / num_compartments
    
    for i in range(num_verticals):
        # Calculate X position
        # Start from left edge (-W/2), move by half thickness, then add spacing
        x_pos = (-W/2) + (T/2) + (i * (comp_width + T))
        z_pos = F_H + (inner_height / 2) + T
        y_pos = 0 # centered in depth (ignoring the back panel overlap for simplicity)
        # Depth of vertical partitions is Total Depth - thickness of back panel
        div_depth = D - back_thickness
        
        div = create_box(f"Divider_{i}", T, div_depth, inner_height, (x_pos, y_pos, z_pos))
        parts.append(div)

    # 5. Feet
    foot_size = 0.04
    # Foot Z is half the height of the foot
    foot_z = F_H / 2
    # Offset from edges
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
        
        # Add a bevel modifier to simulate rounded wood edges and increase fidelity
        bev = final_obj.modifiers.new(name="Bevel", type='BEVEL')
        bev.width = 0.005
        bev.segments = 3

if __name__ == "__main__":
    main()
