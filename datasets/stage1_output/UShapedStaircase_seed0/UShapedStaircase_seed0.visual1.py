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
    shader.inputs['Transmission Weight'].default_value = transmission
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
    GLASS_T = 0.02

    FRAME_COLOR = (0.05, 0.02, 0.15, 1.0) # Navy/Purple
    GLASS_COLOR = (0.4, 0.3, 0.2, 0.6)     # Brownish glass

    frame_mat = create_material("FrameMat", FRAME_COLOR)
    glass_mat = create_material("GlassMat", GLASS_COLOR, alpha=0.5, transmission=0.9)

    total_width = (SW * 2) + GAP
    flight_len = N_STEPS * SD
    landing_z = N_STEPS * SH

    # --- Flight 1 (Upwards) ---
    for i in range(N_STEPS):
        z = i * SH
        y = i * SD
        x = SW / 2
        # Tread
        create_box(f"Tread1_{i}", (SW, SD, 0.05), (x, y + SD/2, z + 0.025), material=frame_mat)
        # Riser
        create_box(f"Riser1_{i}", (SW, 0.05, SH), (x, y, z + SH/2), material=frame_mat)

    # --- Landing ---
    # Positioned at the end of Flight 1
    landing_y = flight_len + L_DEPTH / 2
    create_box("Landing", (total_width, L_DEPTH, 0.15), (total_width/2, landing_y, landing_z), material=frame_mat)

    # --- Flight 2 (Upwards again, opposite direction) ---
    for i in range(N_STEPS):
        z = landing_z + (i * SH)
        # Moves back from the end of the landing toward the start
        y = (flight_len + L_DEPTH) - (i * SD) - SD/2
        x = total_width - SW / 2
        # Tread
        create_box(f"Tread2_{i}", (SW, SD, 0.05), (x, y, z + 0.025), material=frame_mat)
        # Riser
        create_box(f"Riser2_{i}", (SW, 0.05, SH), (x, y + SD/2, z + SH/2), material=frame_mat)

    # --- Stringers ---
    # Flight 1 Side Beams
    create_box("Str1L", (0.1, flight_len, 0.15), (0.05, flight_len/2, landing_z/2), material=frame_mat)
    create_box("Str1R", (0.1, flight_len, 0.15), (SW + 0.05, flight_len/2, landing_z/2), material=frame_mat)
    # Flight 2 Side Beams
    create_box("Str2L", (0.1, flight_len, 0.15), (total_width - SW - 0.05, (flight_len + L_DEPTH)/2, landing_z + (N_STEPS*SH)/2), material=frame_mat)
    create_box("Str2R", (0.1, flight_len, 0.15), (total_width + 0.05, (flight_len + L_DEPTH)/2, landing_z + (N_STEPS*SH)/2), material=frame_mat)

    # --- Balustrades Logic ---
    def add_rail_section(start, end, z_start, z_end, is_glass=True):
        dx, dy = end[0] - start[0], end[1] - start[1]
        dist = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)
        mid = ((start[0]+end[0])/2, (start[1]+end[1])/2)
        avg_z = (z_start + z_end)/2

        if is_glass:
            # Glass Panel
            create_box("Glass", (GLASS_T, dist, RAIL_H * 0.8), 
                      (mid[0], mid[1], avg_z + (RAIL_H * 0.4)), 
                      rotation=(0, 0, angle), material=glass_mat)

        # Top Handrail
        create_box("Handrail", (0.05, dist, 0.05), 
                  (mid[0], mid[1], avg_z + RAIL_H), 
                  rotation=(0, 0, angle), material=frame_mat)

    # --- Perimeter Railings ---
    # Outer Perimeter: Flight 1 Left -> Landing Front -> Flight 2 Right
    add_rail_section((0, 0), (0, flight_len), 0, landing_z)
    add_rail_section((0, flight_len + L_DEPTH), (total_width, flight_len + L_DEPTH), landing_z, landing_z)
    add_rail_section((total_width, flight_len + L_DEPTH), (total_width, flight_len), landing_z, landing_z + N_STEPS*SH)

    # Inner Perimeter: Flight 1 Right -> Landing Gap -> Flight 2 Left
    add_rail_section((SW, 0), (SW, flight_len), 0, landing_z)
    # Small inner transition at landing if needed, usually left open or simple rail
    add_rail_section((SW + GAP, flight_len), (SW + GAP, flight_len + L_DEPTH), landing_z, landing_z + N_STEPS*SH)

if __name__ == "__main__":
    main()
