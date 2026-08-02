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
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dz = p2[2] - p1[2]
    length = math.sqrt(dx*dx + dy*dy + dz*dz)
    mid = ((p1[0] + p2[0])/2, (p1[1] + p2[1])/2, (p1[2] + p2[2])/2)
    
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
    rail_h = 1.0
    frame_t = 0.1
    
    # Materials - Darker Navy, Richer Brown Glass
    mat_navy = create_material("NavyBlue", (0.005, 0.01, 0.1, 1.0)) 
    mat_glass = create_material("BrownGlass", (0.45, 0.25, 0.1, 0.6), alpha=0.5, transmission=0.9)

    # --- Flight 1: Moves along +Y ---
    f1_end_y = num_steps * step_d
    f1_end_z = num_steps * step_h
    
    for i in range(num_steps):
        create_box(f"S1_{i}", (step_w, step_d, step_h), 
                  (0, i * step_d + step_d/2, i * step_h + step_h/2), (0,0,0), mat_navy)

    # --- Landing Platform ---
    # Center of landing is at X=0, Y = f1_end_y + step_w/2
    land_center_y = f1_end_y + step_w / 2
    create_box("Landing", (step_w, step_w, step_h), 
              (0, land_center_y, f1_end_z + step_h/2), (0,0,0), mat_navy)

    # --- Flight 2: Moves along +X ---
    # Starts from the edge of landing. The width of F2 is in Y direction.
    f2_start_x = step_w / 2
    f2_end_x = f2_start_x + (num_steps * step_d)
    
    for i in range(num_steps):
        create_box(f"S2_{i}", (step_d, step_w, step_h), 
                  (f2_start_x + i * step_d + step_d/2, land_center_y, f1_end_z + i * step_h + step_h/2), (0,0,0), mat_navy)

    # --- Structural Framing ---
    # F1 Stringers
    for side in [-1, 1]:
        off = (step_w / 2) * side
        create_beam((off, 0, 0), (off, f1_end_y, f1_end_z), frame_t, mat_navy)
    
    # Landing Frame
    create_box("LandFrame", (step_w + 0.1, step_w + 0.1, 0.05), (0, land_center_y, f1_end_z), (0,0,0), mat_navy)

    # F2 Stringers
    for side in [-1, 1]:
        off = (step_w / 2) * side
        create_beam((f2_start_x, land_center_y + off, f1_end_z), 
                    (f2_end_x, land_center_y + off, f1_end_z + num_steps*step_h), frame_t, mat_navy)

    # --- Railings ---
    def add_glass(p1, p2, h):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        mid = ((p1[0] + p2[0])/2, (p1[1] + p2[1])/2, (p1[2] + p2[2])/2 + h/2)
        rot_z = math.atan2(dy, dx)
        rot_y = -math.atan2(dz, math.sqrt(dx*dx + dy*dy))
        return create_box("GlassPanel", (length, 0.03, h), mid, (rot_y, 0, rot_z), mat_glass)

    # Flight 1 Railings (Sides)
    for side in [-1, 1]:
        off = (step_w / 2) * side
        add_glass((off, 0, 0), (off, f1_end_y, f1_end_z), rail_h)

    # Landing Railings (Outer edges of L-shape)
    # Outside edge X = -step_w/2
    add_glass((-step_w/2, f1_end_y, f1_end_z), (-step_w/2, land_center_y + step_w/2, f1_end_z), rail_h)
    # Front edge Y = land_center_y + step_w/2 (if not blocked by F2)
    # Since F2 is at center X=0 going +X, the railing for landing's front edge only exists where F2 isn't.
    # But typically we rail the outer perimeter. Let's nail the exterior boundary:
    add_glass((-step_w/2, land_center_y + step_w/2, f1_end_z), (0, land_center_y + step_w/2, f1_end_z), rail_h)

    # Flight 2 Railings (Sides)
    for side in [-1, 1]:
        off = (step_w / 2) * side
        add_glass((f2_start_x, land_center_y + off, f1_end_z), 
                  (f2_end_x, land_center_y + off, f1_end_z + num_steps*step_h), rail_h)

    # --- Rail Posts ---
    def add_post(p, h):
        create_box("Post", (0.05, 0.05, h), (p[0], p[1], p[2] + h/2), (0,0,0), mat_navy)

    # F1 Posts
    for side in [-1, 1]:
        off = (step_w / 2) * side
        add_post((off, 0, 0), rail_h)
        add_post((off, f1_end_y, f1_end_z), rail_h)

    # Landing Posts
    add_post((-step_w/2, land_center_y + step_w/2, f1_end_z), rail_h)
    add_post((0, land_center_y + step_w/2, f1_end_z), rail_h)

    # F2 Posts
    for side in [-1, 1]:
        off = (step_w / 2) * side
        add_post((f2_start_x, land_center_y + off, f1_end_z), rail_h)
        add_post((f2_end_x, land_center_y + off, f1_end_z + num_steps*step_h), rail_h)

if __name__ == "__main__":
    main()
