import bpy
import bmesh
import math

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, alpha=1.0, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = color
    if alpha < 1.0:
        mat.blend_method = 'BLEND'
        bsdf.inputs['Alpha'].default_value = alpha
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_cube(name, size, location, rotation=(0, 0, 0), material=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    obj.rotation_euler = rotation
    if material:
        obj.data.materials.append(material)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj

def create_staircase():
    # --- Parameters ---
    num_steps = 15
    step_width = 1.2
    step_depth = 0.3
    step_height = 0.18
    tread_thickness = 0.04
    stringer_w = 0.15 # Width of structural beam
    stringer_h = 0.20 # Height of structural beam
    railing_height = 0.9
    glass_thickness = 0.02
    post_spacing = 5

    # --- Materials ---
    # Dark maroon/purple structural frame
    maroon_mat = create_material("FrameMat", (0.2, 0.01, 0.1, 1.0), metallic=0.4, roughness=0.3)
    # Semi-transparent brownish-grey glass
    glass_mat = create_material("GlassMat", (0.4, 0.38, 0.35, 0.6), alpha=0.5, metallic=0.1, roughness=0.1)

    # --- Steps ---
    for i in range(num_steps):
        z = i * step_height
        y = i * step_depth
        # Tread (the flat part you step on)
        create_cube(f"Tread_{i}", 
                    (step_width, step_depth, tread_thickness), 
                    (0, y + step_depth/2, z + tread_thickness/2), 
                    material=maroon_mat)
        # Riser (the vertical part)
        create_cube(f"Riser_{i}", 
                    (step_width, tread_thickness, step_height - tread_thickness), 
                    (0, y + tread_thickness/2, z + (step_height - tread_thickness)/2), 
                    material=maroon_mat)

    # --- Stringers (Structural Frame) ---
    total_depth = num_steps * step_depth
    total_height = num_steps * step_height
    slope_angle = math.atan2(total_height, total_depth)
    rail_length = math.sqrt(total_depth**2 + total_height**2)

    # Offset stringers slightly outward from the steps
    stringer_offset = (step_width / 2) + (stringer_w / 2)
    for side in [-1, 1]:
        x_pos = stringer_offset * side
        create_cube(f"Stringer_{side}", 
                    (stringer_w, rail_length, stringer_h), 
                    (x_pos, total_depth/2, (total_height / 2) - (stringer_h / 2)), 
                    rotation=(0, -slope_angle, 0), 
                    material=maroon_mat)

    # --- Railings ---
    for side in [-1, 1]:
        x_pos = (step_width / 2) * side
        
        # Posts and Glass Panels
        for i in range(0, num_steps + 1, post_spacing):
            z_base = i * step_height
            y_pos = i * step_depth
            
            # Post: vertical support
            create_cube(f"Post_{side}_{i}", 
                        (0.04, 0.04, railing_height), 
                        (x_pos, y_pos, z_base + railing_height/2), 
                        material=maroon_mat)
            
            # Glass Panel between this post and the next
            if i < num_steps:
                next_i = min(i + post_spacing, num_steps)
                p1_y, p1_z = y_pos, z_base
                p2_y, p2_z = next_i * step_depth, next_i * step_height
                
                mid_y = (p1_y + p2_y) / 2
                mid_z = (p1_z + p2_z) / 2
                dist = math.sqrt((p2_y - p1_y)**2 + (p2_z - p1_z)**2)
                # Glass height is slightly less than post height to avoid overlap issues
                glass_h = railing_height * 0.85
                create_cube(f"Glass_{side}_{i}", 
                            (glass_thickness, dist, glass_h), 
                            (x_pos, mid_y, mid_z + (glass_h / 2)), 
                            rotation=(0, -slope_angle, 0), 
                            material=glass_mat)

        # Top Handrail: connects posts firmly
        start_y = 0
        start_z = railing_height
        end_y = num_steps * step_depth
        end_z = num_steps * step_height + railing_height
        
        handrail_len = math.sqrt((end_y - start_y)**2 + (end_z - start_z)**2)
        create_cube(f"Handrail_{side}", 
                    (0.05, handrail_len, 0.05), 
                    (x_pos, (start_y + end_y)/2, (start_z + end_z)/2), 
                    rotation=(0, -slope_angle, 0), 
                    material=maroon_mat)

# Execute
clear_scene()
create_staircase()
