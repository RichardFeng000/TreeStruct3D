import bpy
import bmesh
import mathutils

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_box(name, size, location, material=None):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # create_cube size is the full diameter (2x2x2 if size=2)
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    
    bm.to_mesh(mesh)
    bm.free()
    obj.location = location
    if material:
        obj.data.materials.append(material)
    return obj

def create_shaker_door(name, width, height, thickness, location, material):
    # Outer Frame
    frame_w = width
    frame_h = height
    frame_t = thickness
    frame = create_box(f"{name}_frame", (frame_w, frame_t, frame_h), location, material)
    
    # Recessed Panel (slightly smaller and pushed back)
    panel_margin = 0.03
    p_w = width - panel_margin * 2
    p_h = height - panel_margin * 2
    p_t = thickness * 0.6
    # Offset the panel so it sits inside the frame's front face
    panel_loc = (location[0], location[1] - thickness*0.2, location[2])
    panel = create_box(f"{name}_panel", (p_w, p_t, p_h), panel_loc, material)
    return frame

def build_kitchen():
    clear_scene()
    
    # Materials
    mat_wood = create_material("Wood", (0.8, 0.75, 0.6, 1))
    mat_counter = create_material("Countertop", (0.95, 0.95, 0.9, 1))
    mat_backsplash = create_material("Backsplash", (0.9, 0.9, 0.85, 1))
    mat_metal = create_material("Metal", (0.4, 0.4, 0.4, 1))

    # Dimensions
    CAB_W = 0.7
    NUM_CABS = 3
    BASE_H = 0.85
    BASE_D = 0.6
    COUNTER_T = 0.04
    BACKSPLASH_H = 0.6
    UPPER_H = 0.8
    UPPER_D = 0.3
    TOTAL_W = CAB_W * NUM_CABS

    # Base Cabinets Run
    for i in range(NUM_CABS):
        x_pos = (i - (NUM_CABS-1)/2) * CAB_W
        
        # Cabinet Body
        body = create_box(f"BaseBody_{i}", (CAB_W * 0.98, BASE_D, BASE_H), (x_pos, 0, BASE_H/2), mat_wood)
        
        # Doors - placed on the front face (-Y)
        door_w = (CAB_W * 0.46)
        door_h = BASE_H * 0.85
        door_t = 0.03
        for side in [-1, 1]:
            dx = x_pos + (side * door_w / 2 + 0.01 * side) # Small gap between doors
            dy = -BASE_D/2 - door_t/2
            dz = BASE_H/2 - 0.05
            create_shaker_door(f"Door_{i}_{side}", door_w, door_h, door_t, (dx, dy, dz), mat_wood)
            
            # Handle
            hx = dx + (0.1 * side)
            hy = dy - 0.02
            hz = dz - 0.15
            create_box(f"Handle_{i}_{side}", (0.01, 0.02, 0.1), (hx, hy, hz), mat_metal)

    # Countertop
    counter_w = TOTAL_W + 0.04
    counter_d = BASE_D + 0.05
    create_box("Countertop", (counter_w, counter_d, COUNTER_T), (0, -0.025, BASE_H + COUNTER_T/2), mat_counter)

    # Backsplash Area
    create_box("Backsplash", (counter_w, 0.02, BACKSPLASH_H), (0, BASE_D/2, BASE_H + COUNTER_T + BACKSPLASH_H/2), mat_backsplash)

    # Upper Cabinets Run
    upper_z_base = BASE_H + COUNTER_T + BACKSPLASH_H
    for i in range(NUM_CABS):
        x_pos = (i - (NUM_CABS-1)/2) * CAB_W
        z_center = upper_z_base + UPPER_H/2
        t = 0.02 # Shell thickness

        # Upper Body parts (Open front)
        # Sides
        for side in [-1, 1]:
            create_box(f"UpperSide_{i}_{side}", (t, UPPER_D, UPPER_H), (x_pos + side*CAB_W/2, 0, z_center), mat_wood)
        # Top & Bottom
        for vert in [-1, 1]:
            create_box(f"UpperHoriz_{i}_{vert}", (CAB_W, UPPER_D, t), (x_pos, 0, z_center + vert*UPPER_H/2), mat_wood)
        # Back
        create_box(f"UpperBack_{i}", (CAB_W, t, UPPER_H), (x_pos, BASE_D/2, z_center), mat_wood)

        # Internal Shelves
        shelf_count = 2
        for s in range(1, shelf_count + 1):
            s_z = upper_z_base + (UPPER_H / (shelf_count + 1)) * s
            create_box(f"Shelf_{i}_{s}", (CAB_W * 0.95, UPPER_D * 0.9, t), (x_pos, 0, s_z), mat_wood)

if __name__ == "__main__":
    build_kitchen()
