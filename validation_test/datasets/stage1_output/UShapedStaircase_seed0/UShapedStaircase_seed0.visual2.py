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
    shader = nodes.new('ShaderNodeBsdfPrincipled')
    output = nodes.new('ShaderNodeOutputMaterial')
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Alpha'].default_value = alpha
    # Transmission is 'Transmission Weight' in newer Blender versions
    if 'Transmission Weight' in shader.inputs:
        shader.inputs['Transmission Weight'].default_value = transmission
    else:
        shader.inputs['Transmission'].default_value = transmission
        
    shader.inputs['Roughness'].default_value = 0.1 if transmission > 0 else 0.4
    mat.node_tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    mat.blend_method = 'BLEND' if alpha < 1.0 else 'OPAQUE'
    return mat

def create_box(name, size, location, rotation=(0,0,0), material=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    return obj

def main():
    clear_scene()

    # --- Configuration ---
    SW = 1.2      # Step Width
    SD = 0.3      # Step Depth (tread)
    SH = 0.18     # Step Height (riser)
    N_STEPS = 10  # Steps per flight
    GAP = 0.4     # Gap between flights
    L_DEPTH = 1.5 # Landing depth
    RAIL_H = 1.0  # Railing height
    GLASS_T = 0.03

    FRAME_COLOR = (0.05, 0.02, 0.15, 1.0) # Navy/Purple
    GLASS_COLOR = (0.4, 0.3, 0.2, 0.6)     # Brownish glass

    frame_mat = create_material("FrameMat", FRAME_COLOR)
    glass_mat = create_material("GlassMat", GLASS_COLOR, alpha=0.5, transmission=0.9)

    total_width = (SW * 2) + GAP
    flight_len = N_STEPS * SD
    landing_z = N_STEPS * SH

    # --- Flight 1 ---
    for i in range(N_STEPS):
        z = i * SH
        y = i * SD
        x = SW / 2
        create_box(f"Tread1_{i}", (SW, SD, 0.05), (x, y + SD/2, z + 0.025), material=frame_mat)
        create_box(f"Riser1_{i}", (SW, 0.05, SH), (x, y, z + SH/2), material=frame_mat)

    # --- Landing ---
    landing_y = flight_len + L_DEPTH / 2
    create_box("Landing", (total_width, L_DEPTH, 0.15), (total_width/2, landing_y, landing_z), material=frame_mat)

    # --- Flight 2 ---
    for i in range(N_STEPS):
        z = landing_z + (i * SH)
        # Start from the far end of landing and go back
        y = (flight_len + L_DEPTH) - (i * SD) - SD/2
        x = total_width - SW / 2
        create_box(f"Tread2_{i}", (SW, SD, 0.05), (x, y, z + 0.025), material=frame_mat)
        # Riser for Flight 2 is shifted forward relative to the tread
        create_box(f"Riser2_{i}", (SW, 0.05, SH), (x, y - SD/2, z + SH/2), material=frame_mat)

    # --- Stringers (Structural Framing) ---
    # Flight 1
    create_box("Str1L", (0.1, flight_len, 0.2), (0.05, flight_len/2, landing_z/2), material=frame_mat)
    create_box("Str1R", (0.1, flight_len, 0.2), (SW + 0.05, flight_len/2, landing_z/2), material=frame_mat)
    # Flight 2
    create_box("Str2L", (0.1, flight_len, 0.2), (total_width - SW - 0.05, (flight_len + L_DEPTH)/2, landing_z + (N_STEPS*SH)/2), material=frame_mat)
    create_box("Str2R", (0.1, flight_len, 0.2), (total_width + 0.05, (flight_len + L_DEPTH)/2, landing_z + (N_STEPS*SH)/2), material=frame_mat)

    # --- Balustrades with Slope Logic ---
    def create_sloped_rail(start_pos, end_pos, height, is_glass=False):
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        dz = end_pos[2] - start_pos[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        mid = ((start_pos[0]+end_pos[0])/2, (start_pos[1]+end_pos[1])/2, (start_pos[2]+end_pos[2])/2)
        
        # Calculate rotation to align the X-axis of the cube with the direction vector
        # Simple approach for these specific directions: 
        # we use a temporary object to align or manually calculate Euler.
        # Since flights are aligned with Y, we only need rotation around X and Z.
        angle_z = math.atan2(dy, dx)
        angle_x = math.atan2(dz, math.sqrt(dx*dx + dy*dy))
        
        if is_glass:
            # Glass panel - slightly thinner than rail
            create_box("GlassPanel", (GLASS_T, dist, height * 0.8), 
                      (mid[0], mid[1], mid[2] + (height * 0.4) - 0.2), 
                      rotation=(angle_x, 0, angle_z), material=glass_mat)
        else:
            # Handrail
            create_box("RailBar", (0.05, dist, 0.05), 
                      (mid[0], mid[1], mid[2] + height), 
                      rotation=(angle_x, 0, angle_z), material=frame_mat)

    # Perimeter Rails: Outer edge
    # Flight 1 Left (Outer)
    p1_s = (0, 0, 0); p1_e = (0, flight_len, landing_z)
    create_sloped_rail(p1_s, p1_e, RAIL_H, is_glass=True)
    create_sloped_rail(p1_s, p1_e, RAIL_H, is_glass=False)

    # Landing Outer (Front)
    pL_s = (0, flight_len + L_DEPTH, landing_z); pL_e = (total_width, flight_len + L_DEPTH, landing_z)
    create_sloped_rail(pL_s, pL_e, RAIL_H, is_glass=True)
    create_sloped_rail(pL_s, pL_e, RAIL_H, is_glass=False)

    # Flight 2 Right (Outer)
    p2_s = (total_width, flight_len + L_DEPTH, landing_z); p2_e = (total_width, flight_len, landing_z + N_STEPS*SH)
    create_sloped_rail(p2_s, p2_e, RAIL_H, is_glass=True)
    create_sloped_rail(p2_s, p2_e, RAIL_H, is_glass=False)

    # Perimeter Rails: Inner edge (with gap at landing)
    # Flight 1 Right (Inner)
    pi1_s = (SW, 0, 0); pi1_e = (SW, flight_len, landing_z)
    create_sloped_rail(pi1_s, pi1_e, RAIL_H, is_glass=True)
    create_sloped_rail(pi1_s, pi1_e, RAIL_H, is_glass=False)

    # Flight 2 Left (Inner)
    pi2_s = (SW + GAP, flight_len + L_DEPTH, landing_z); pi2_e = (SW + GAP, flight_len, landing_z + N_STEPS*SH)
    create_sloped_rail(pi2_s, pi2_e, RAIL_H, is_glass=True)
    create_sloped_rail(pi2_s, pi2_e, RAIL_H, is_glass=False)

if __name__ == "__main__":
    main()
