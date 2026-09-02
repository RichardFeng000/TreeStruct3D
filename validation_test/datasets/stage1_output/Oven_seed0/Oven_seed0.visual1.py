import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Creates a principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_box(name, w, d, h, location=(0, 0, 0), material=None):
    """Helper to create a box mesh."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (w, d, h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    return obj

def add_cylinder(name, r, h, location=(0, 0, 0), rotation=(0, 0, 0), material=None):
    """Helper to create a cylinder."""
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=location, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    return obj

def create_burner_grate(pos_x, pos_y, height, mat):
    """Creates a cast-iron gas burner grate sitting at specific height."""
    # Base ring
    bpy.ops.mesh.primitive_torus_add(align='WORLD', location=(pos_x, pos_y, height), 
                                    major_radius=0.12, minor_radius=0.015)
    ring = bpy.context.active_object
    ring.name = "BurnerRing"
    ring.data.materials.append(mat)
    
    # Cross bars to form a grate
    for i in range(4):
        angle = math.radians(i * 90 + 45)
        dx = math.cos(angle) * 0.12
        dy = math.sin(angle) * 0.12
        # Bars sit slightly above the ring
        bpy.ops.mesh.primitive_cylinder_add(radius=0.01, depth=0.25, 
                                           location=(pos_x + dx/2, pos_y + dy/2, height + 0.03), 
                                           rotation=(math.radians(90), 0, angle))
        bar = bpy.context.active_object
        bar.name = "GrateBar"
        bar.data.materials.append(mat)

def run():
    clear_scene()

    # Materials: Gray stone-textured metallic body (Darker gray)
    mat_body = create_material("StoneMetallic", (0.25, 0.25, 0.26, 1), metallic=0.6, roughness=0.7)
    mat_black_glass = create_material("BlackGlass", (0.01, 0.01, 0.01, 1), metallic=0.2, roughness=0.1)
    mat_cast_iron = create_material("CastIron", (0.05, 0.05, 0.05, 1), metallic=0.8, roughness=0.6)
    mat_display = create_material("DisplayScreen", (0.02, 0.02, 0.02, 1), metallic=0.1, roughness=0.2)
    mat_led = create_material("LEDGreen", (0.0, 1.0, 0.2, 1), metallic=0.0, roughness=0.1)

    # --- Main Body ---
    # Height: 0.85m, Width: 0.7m, Depth: 0.6m
    body = create_box("OvenBody", 0.7, 0.6, 0.85, location=(0, 0, 0.425), material=mat_body)
    
    # Back Control Panel (Rises above the body)
    panel = create_box("ControlPanel", 0.7, 0.1, 0.25, location=(0, -0.25, 0.95), material=mat_body)

    # Black Glass Cooktop surface (on top of body)
    cooktop_z = 0.86  # Top of body is 0.85 + half of thickness
    cooktop = create_box("Cooktop", 0.68, 0.58, 0.02, location=(0, 0, cooktop_z), material=mat_black_glass)

    # --- Burners (Positioned on top of the glass) ---
    # Height for burners to sit is top of the cooktop surface
    burner_h = cooktop_z + 0.01
    burner_pos = [(-0.18, -0.15), (0.18, -0.15), (-0.18, 0.15), (0.18, 0.15)]
    for bx, by in burner_pos:
        create_burner_grate(bx, by, burner_h, mat_cast_iron)

    # --- Control Panel Details ---
    # Knobs
    knob_count = 6
    for i in range(knob_count):
        kx = -0.25 + (i * 0.09)
        add_cylinder("Knob", 0.03, 0.05, location=(kx, -0.31, 0.95), rotation=(math.radians(90), 0, 0), material=mat_cast_iron)

    # Clock Display
    display = create_box("ClockDisplay", 0.12, 0.01, 0.06, location=(0, -0.3, 0.98), material=mat_display)
    
    # Digit "12:01" representation
    # '1'
    create_box("d1", 0.008, 0.005, 0.03, location=(-0.04, -0.29, 0.98), material=mat_led)
    # '2' (simplified block)
    create_box("d2", 0.018, 0.005, 0.03, location=(-0.01, -0.29, 0.98), material=mat_led)
    # ':'
    create_box("c1", 0.004, 0.005, 0.006, location=(0.02, -0.29, 0.99), material=mat_led)
    create_box("c2", 0.004, 0.005, 0.006, location=(0.02, -0.29, 0.97), material=mat_led)
    # '0' (simplified block)
    create_box("d3", 0.018, 0.005, 0.03, location=(0.06, -0.29, 0.98), material=mat_led)
    # '1'
    create_box("d4", 0.008, 0.005, 0.03, location=(0.09, -0.29, 0.98), material=mat_led)

    # --- Oven Door ---
    door = create_box("OvenDoor", 0.66, 0.04, 0.5, location=(0, 0.3, 0.3), material=mat_body)
    window = create_box("DoorWindow", 0.5, 0.05, 0.3, location=(0, 0.3, 0.35), material=mat_black_glass)

    # Handle
    handle_y = 0.34
    handle_z = 0.5
    add_cylinder("HandleBar", 0.02, 0.4, location=(0, handle_y, handle_z), rotation=(math.radians(90), 0, 0), material=mat_cast_iron)
    add_cylinder("SupportL", 0.015, 0.08, location=(-0.18, handle_y - 0.02, handle_z), rotation=(0, 0, 0), material=mat_cast_iron)
    add_cylinder("SupportR", 0.015, 0.08, location=(0.18, handle_y - 0.02, handle_z), rotation=(0, 0, 0), material=mat_cast_iron)

    # Bevels for cleaner edges
    for obj in [body, panel, door]:
        bev = obj.modifiers.new(name="Bevel", type='BEVEL')
        bev.width = 0.01

if __name__ == "__main__":
    run()
