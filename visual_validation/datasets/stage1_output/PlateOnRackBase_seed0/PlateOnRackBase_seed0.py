import bpy
import bmesh
import math
from mathutils import Vector, Euler

def clear_scene():
    """Clear all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Create a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Set base color (RGBA)
    node_principled.inputs['Base Color'].default_value = color
    
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_plate():
    """Creates a dark purple circular plate."""
    radius = 0.3
    thickness = 0.015
    segments = 64
    
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=segments, 
        radius=radius, 
        depth=thickness, 
        location=(0, 0, 0)
    )
    plate = bpy.context.active_object
    plate.name = "Plate"
    
    # Dark Purple Color (Very dark purple)
    purple_mat = create_material("DarkPurpleCeramic", (0.1, 0.02, 0.15, 1.0))
    plate.data.materials.append(purple_mat)
    
    return plate

def create_rack():
    """Creates a wooden stand with vertical pegs to support the plate upright."""
    wood_mat = create_material("Wood", (0.35, 0.2, 0.1, 1.0))
    
    # Base: A rectangular board for the plate to sit on
    base_w = 0.7
    base_d = 0.4
    base_h = 0.03
    
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, base_h / 2))
    base = bpy.context.active_object
    base.scale = (base_w/2, base_d/2, base_h/2)
    base.name = "RackBase"
    base.data.materials.append(wood_mat)

    # Vertical Pegs: Two supports at the back of the base
    peg_radius = 0.015
    peg_height = 0.4
    # Place pegs at the back end of the base board
    peg_x_pos = 0.18
    peg_y_pos = (base_d / 2) - 0.05
    
    pegs = []
    for x in [-peg_x_pos, peg_x_pos]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=peg_radius, 
            depth=peg_height, 
            location=(x, peg_y_pos, peg_height / 2)
        )
        peg = bpy.context.active_object
        peg.name = f"Peg_{x}"
        peg.data.materials.append(wood_mat)
        pegs.append(peg)

    return [base] + pegs

def main():
    clear_scene()
    
    # Create the rack first to establish coordinates
    rack_parts = create_rack()
    
    # Create the plate
    plate = create_plate()
    
    # POSITIONING AND ORIENTATION
    # We want the plate leaning upright. 
    # Lean angle: approx 15 degrees from vertical (75 degrees from ground)
    lean_angle = math.radians(15) 
    plate.rotation_euler = Euler((0, lean_angle, 0), 'XYZ')
    
    # Place the bottom edge of the plate on the base
    # The center of the cylinder is at (0,0,0). To make it lean:
    # Rotate around the bottom edge.
    offset_z = 0.03 / 2 # Start just above the base surface
    plate.location.z = offset_z + 0.15 * math.cos(lean_angle)
    # Position Y so it leans back against the pegs
    # Pegs are at y ~ 0.15. Plate radius is 0.3.
    # The distance from plate center to its edge is 0.3.
    plate.location.y = 0.1 - (0.15 * math.sin(lean_angle))
    plate.location.x = 0

    # Fine-tune: Ensure the bottom rim of the plate sits on the baseboard
    # Bottom edge z is roughly plate.loc.z - radius*sin(lean)
    # We want: PlateLocZ - (radius * sin(angle)) = BaseTopZ
    plate.location.z = 0.03 + (0.3 * math.sin(lean_angle))
    # Position Y so the back edge touches the pegs
    # The back rim is at plate.loc.y + radius * cos(angle)
    # Pegs are at y = 0.15
    plate.location.y = 0.15 - (0.3 * math.cos(lean_angle))

if __name__ == "__main__":
    main()
