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
    bmesh.ops.create_cube(bm, size=1.0)
    # Scale to exact total dimensions
    for v in bm.verts:
        v.co.x *= size[0] / 2.0
        v.co.y *= size[1] / 2.0
        v.co.z *= size[2] / 2.0
        
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = mathutils.Vector(location)
    if material:
        obj.data.materials.append(material)
    return obj

def add_bevel(obj, amount=0.01):
    mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    mod.width = amount
    mod.segments = 3
    return mod

def create_handle(parent_obj, size=(0.02, 0.01, 0.08), material=None):
    # Handle is placed on the front surface of the panel (Y axis)
    # Panel's front face is at Y = +size[1]/2 relative to its center
    mesh = bpy.data.meshes.new("Handle")
    obj = bpy.data.objects.new("Handle", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0] / 2.0
        v.co.y *= size[1] / 2.0
        v.co.z *= size[2] / 2.0
    bm.to_mesh(mesh)
    bm.free()
    
    # Position: Front face of the parent panel, slightly offset outwards
    panel_w = parent_obj.dimensions.y # This is actually depth in our setup
    # In build_kitchen_island, we set Y for panels to be 0.02 (thickness)
    # They are centered at Y=0, so face is at +0.01
    loc = parent_obj.location + mathutils.Vector((0, 0.015, 0))
    obj.location = loc
    if material:
        obj.data.materials.append(material)
    return obj

def build_kitchen_island():
    clear_scene()
    
    # Dimensions
    L = 2.4  # Length (X)
    W = 0.9  # Width/Depth (Y)
    H = 0.9  # Total Height (Z)
    CounterT = 0.05
    KickH = 0.1
    PanelThick = 0.02
    Gap = 0.01
    
    # Materials
    mat_counter = create_material("Mat_Counter", (0.9, 0.9, 0.85, 1.0)) # Light marble
    mat_carcass = create_material("Mat_Carcass", (0.2, 0.2, 0.2, 1.0))   # Dark interior/base
    mat_kick = create_material("Mat_Kick", (0.1, 0.1, 0.1, 1.0))        # Very dark base
    tones = [
        create_material("Tone_Light", (0.8, 0.75, 0.7, 1.0)), # Beige/Cream
        create_material("Tone_Mid", (0.6, 0.55, 0.5, 1.0)),   # Muted Grey-Brown
        create_material("Tone_Dark", (0.4, 0.35, 0.3, 1.0))    # Deep Taupe
    ]
    mat_handle = create_material("Mat_Handle", (0.7, 0.7, 0.7, 1.0))

    # 1. Countertop
    counter = create_box("Countertop", (L + 0.05, W + 0.05, CounterT), 
                        (0, 0, H - CounterT/2), mat_counter)
    add_bevel(counter, 0.015)

    # 2. Main Cabinet Carcass (The "box" that holds everything)
    carcass_h = H - CounterT - KickH
    carcass = create_box("Carcass", (L, W, carcass_h), 
                        (0, 0, KickH + carcass_h/2), mat_carcass)
    # We don't bevel the carcass much as it's hidden by panels

    # 3. Recessed Kickplate
    kick = create_box("Kickplate", (L - 0.1, W - 0.1, KickH),
                      (0, 0, KickH/2), mat_kick)

    # 4. Front Panels (Doors and Drawers)
    sections = [
        {"type": "drawers", "count": 3},
        {"type": "cupboard", "count": 1}, 
        {"type": "mixed", "count": 2}, # Top drawer, bot door
        {"type": "cupboard", "count": 1}
    ]
    
    sec_w = L / len(sections)
    start_x = -L/2 + sec_w/2
    
    for i, sec in enumerate(sections):
        x_pos = start_x + i * sec_w
        material = tones[i % len(tones)]
        # Panels are placed on the front face (Y = W/2)
        y_pos = W/2 
        
        if sec["type"] == "drawers":
            d_h = (carcass_h - Gap * 4) / 3
            for j in range(3):
                z_pos = KickH + Gap + j * (d_h + Gap) + d_h/2
                p = create_box(f"Drawer_{i}_{j}", (sec_w - Gap, PanelThick, d_h),
                              (x_pos, y_pos, z_pos), material)
                add_bevel(p, 0.005)
                create_handle(p, material=mat_handle)

        elif sec["type"] == "cupboard":
            z_pos = KickH + carcass_h/2 + Gap/2
            p = create_box(f"Door_{i}", (sec_w - Gap, PanelThick, carcass_h - Gap),
                          (x_pos, y_pos, z_pos), material)
            add_bevel(p, 0.005)
            create_handle(p, size=(0.02, 0.01, 0.08), material=mat_handle)

        elif sec["type"] == "mixed":
            d_h = (carcass_h - Gap * 3) / 4
            # Drawer on top
            z_draw = H - CounterT - d_h/2 - Gap/2
            p_draw = create_box(f"Drawer_{i}_top", (sec_w - Gap, PanelThick, d_h),
                               (x_pos, y_pos, z_draw), material)
            add_bevel(p_draw, 0.005)
            create_handle(p_draw, material=mat_handle)
            
            # Door below
            door_h = carcass_h - d_h - Gap*2
            z_door = KickH + Gap + door_h/2
            p_door = create_box(f"Door_{i}_bot", (sec_w - Gap, PanelThick, door_h),
                               (x_pos, y_pos, z_door), material)
            add_bevel(p_door, 0.005)
            create_handle(p_door, size=(0.02, 0.01, 0.08), material=mat_handle)

if __name__ == "__main__":
    build_kitchen_island()
