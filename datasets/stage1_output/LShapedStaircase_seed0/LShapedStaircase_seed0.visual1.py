import bpy
import bmesh
import math

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, alpha=1.0, transmission=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    node_bsdf.inputs['Base Color'].default_value = color
    node_bsdf.inputs['Alpha'].default_value = alpha
    node_bsdf.inputs['Transmission Weight'].default_value = transmission 
    
    mat.node_tree.links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    
    if alpha < 1.0:
        mat.blend_method = 'BLEND'
        
    return mat

def create_box(name, size, location, rotation=(0, 0, 0), material=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    return obj

def create_beam(p1, p2, radius, material):
    # Create a box beam between two points
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dz = p2[2] - p1[2]
    length = math.sqrt(dx*dx + dy*dy + dz*dz)
    mid = ((p1[0] + p2[0])/2, (p1[1] + p2[1])/2, (p1[2] + p2[2])/2)
    
    # Rotation for the beam
    rot_z = math.atan2(dy, dx)
    rot_y = -math.atan2(dz, math.sqrt(dx*dx + dy*dy))
    
    return create_box("Beam", (length, radius, radius), mid, (rot_y, 0, rot_z), material)

def main():
    clear_scene()

    # Parameters
    step_w = 1.2   
    step_h = 0.18  
    step_d = 0.3   
    num_steps = 8
    landing_size = 1.2
    rail_h = 1.1
    frame_thickness = 0.1
    
    # Materials
    mat_navy = create_material("NavyBlue", (0.01, 0.02, 0.1, 1.0)) 
    mat_glass = create_material("BrownGlass", (0.4, 0.3, 0.2, 0.5), alpha=0.4, transmission=0.9)

    # Coordinates for L-shape
    # Flight 1: starts at origin, moves along +Y
    f1_start = (0, 0, 0)
    f1_end_y = num_steps * step_d
    f1_end_z = num_steps * step_h
    
    # Flight 1 Steps
    for i in range(num_steps):
        create_box(f"S1_{i}", (step_w, step_d, step_h), 
                  (0, i * step_d + step_d/2, i * step_h + step_h/2), (0,0,0), mat_navy)

    # Landing
    landing_pos = (0, f1_end_y + landing_size/2, f1_end_z + step_h/2)
    create_box("Landing", (step_w, landing_size, step_h), landing_pos, (0,0,0), mat_navy)

    # Flight 2: Starts from landing edge, moves along +X
    f2_start_x = step_w / 2
    f2_start_y = f1_end_y + landing_size
    for i in range(num_steps):
        create_box(f"S2_{i}", (step_d, step_w, step_h), 
                  (f2_start_x + i * step_d + step_d/2, f2_start_y - step_w/2, f1_end_z + i * step_h + step_h/2), (0,0,0), mat_navy)

    # --- Structural Framing ---
    # Flight 1 Stringers
    for side in [-1, 1]:
        off = (step_w / 2) * side
        create_beam((-off if side==-1 else off, 0, 0), (off, f1_end_y, f1_end_z), frame_thickness, mat_navy)
    
    # Landing Frame
    create_box("LandFrame", (step_w + 0.1, landing_size, 0.05), (0, f1_end_y + landing_size/2, f1_end_z), (0,0,0), mat_navy)

    # Flight 2 Stringers
    for side in [-1, 1]:
        off = (step_w / 2) * side
        create_beam((f2_start_x, f2_start_y + off, f1_end_z), 
                    (f2_start_x + num_steps*step_d, f2_start_y + off, f1_end_z + num_steps*step_h), frame_thickness, mat_navy)

    # --- Railings (Smooth Glass Panels) ---
    def add_glass_panel(p1, p2, h):
        # p1 and p2 are base points on the floor/stairs
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        mid = ((p1[0] + p2[0])/2, (p1[1] + p2[1])/2, (p1[2] + p2[2])/2 + h/2)
        rot_z = math.atan2(dy, dx)
        rot_y = -math.atan2(dz, math.sqrt(dx*dx + dy*dy))
        return create_box("GlassPanel", (length, 0.03, h), mid, (rot_y, 0, rot_z), mat_glass)

    # Flight 1 Railings
    for side in [-1, 1]:
        off = (step_w / 2) * side
        add_glass_panel((off, 0, 0), (off, f1_end_y, f1_end_z), rail_h)

    # Landing Railings
    # Front edge of landing
    add_glass_panel((-step_w/2, f1_end_y + landing_size, f1_end_z), 
                    (step_w/2, f1_end_y + landing_size, f1_end_z), rail_h)
    # Side edge of landing (where it's open)
    add_glass_panel((-step_w/2, f1_end_y, f1_end_z), 
                    (-step_w/2, f1_end_y + landing_size, f1_end_z), rail_h)

    # Flight 2 Railings
    for side in [-1, 1]:
        off = (step_w / 2) * side
        add_glass_panel((f2_start_x, f2_start_y + off, f1_end_z), 
                        (f2_start_x + num_steps*step_d, f2_start_y + off, f1_end_z + num_steps*step_h), rail_h)

    # --- Rail Posts for visual support ---
    def add_post(p, h):
        create_box("Post", (0.05, 0.05, h), (p[0], p[1], p[2] + h/2), (0,0,0), mat_navy)

    # F1 posts
    for side in [-1, 1]:
        off = (step_w / 2) * side
        add_post((off, 0, 0), rail_h)
        add_post((off, f1_end_y, f1_end_z), rail_h)

    # Landing posts
    add_post((-step_w/2, f1_end_y + landing_size, f1_end_z), rail_h)
    add_post((step_w/2, f1_end_y + landing_size, f1_end_z), rail_h)

    # F2 posts
    for side in [-1, 1]:
        off = (step_w / 2) * side
        add_post((f2_start_x, f2_start_y + off, f1_end_z), rail_h)
        add_post((f2_start_x + num_steps*step_d, f2_start_y + off, f1_end_z + num_steps*step_h), rail_h)

if __name__ == "__main__":
    main()
