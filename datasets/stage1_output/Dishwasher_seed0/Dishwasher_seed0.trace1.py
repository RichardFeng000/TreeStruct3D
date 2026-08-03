import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_box(name, w, h, d, loc=(0, 0, 0), rot=(0, 0, 0), mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (w, d, h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    return obj

def create_wire_segment(name, start, end, radius, mat):
    direction = end - start
    length = direction.length
    if length < 1e-6:
        return None
    
    midpoint = (start + end) / 2
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, location=midpoint)
    wire = bpy.context.active_object
    wire.name = name
    
    # Use rotation_difference to align Z-axis of cylinder with the direction vector
    rot_quat = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    wire.rotation_mode = 'QUATERNION'
    wire.rotation_quaternion = rot_quat
    if mat:
        wire.data.materials.append(mat)
    return wire

def create_dish_rack(loc, mat):
    rw, rd, rh = 0.54, 0.52, 0.60 # dimensions of the rack
    wire_r = 0.005
    
    # Base grid (X direction wires)
    for i in range(8):
        y = -rd/2 + (i * rd / 7)
        create_wire_segment(f"WireX_{i}", Vector((-rw/2, y, 0)) + loc, Vector((rw/2, y, 0)) + loc, wire_r, mat)
    
    # Base grid (Y direction wires)
    for i in range(8):
        x = -rw/2 + (i * rw / 7)
        create_wire_segment(f"WireY_{i}", Vector((x, -rd/2, 0)) + loc, Vector((x, rd/2, 0)) + loc, wire_r, mat)

    # Vertical slots for plates (tines)
    for i in range(10):
        x = -0.2 + (i * 0.04)
        z_top = rh * 0.8
        y_pos = 0.05
        create_wire_segment(f"Tine_{i}_A", Vector((x, y_pos, 0)) + loc, Vector((x, y_pos, z_top)) + loc, wire_r, mat)
        create_wire_segment(f"Tine_{i}_B", Vector((x, -y_pos, 0)) + loc, Vector((x, -y_pos, z_top)) + loc, wire_r, mat)

    # Top frame rim
    z_top = rh * 0.8
    create_wire_segment("Rim1", Vector((-rw/2, -rd/2, z_top)) + loc, Vector((rw/2, -rd/2, z_top)) + loc, wire_r, mat)
    create_wire_segment("Rim2", Vector((rw/2, -rd/2, z_top)) + loc, Vector((rw/2, rd/2, z_top)) + loc, wire_r, mat)
    create_wire_segment("Rim3", Vector((rw/2, rd/2, z_top)) + loc, Vector((-rw/2, rd/2, z_top)) + loc, wire_r, mat)
    create_wire_segment("Rim4", Vector((-rw/2, rd/2, z_top)) + loc, Vector((-rw/2, -rd/2, z_top)) + loc, wire_r, mat)

def main():
    clear_scene()

    # Materials: Glossy Black and Matte Violet
    black_glossy = create_material("BlackGlossy", (0.01, 0.01, 0.01, 1.0), metallic=0.6, roughness=0.1)
    violet_matte = create_material("VioletMatte", (0.3, 0.1, 0.4, 1.0), metallic=0.0, roughness=0.8)

    # Body Dimensions
    bw, bh, bd = 0.6, 0.85, 0.6
    wall_t = 0.02

    # Build the hollow body (built-in style: open front)
    create_box("Back", bw, bh, wall_t, loc=(0, bd/2 - wall_t/2, bh/2), mat=black_glossy)
    create_box("SideL", wall_t, bh, bd, loc=(-bw/2 + wall_t/2, 0, bh/2), mat=black_glossy)
    create_box("SideR", wall_t, bh, bd, loc=(bw/2 - wall_t/2, 0, bh/2), mat=black_glossy)
    create_box("Bottom", bw, wall_t, bd, loc=(0, 0, wall_t/2), mat=black_glossy)
    create_box("Ceiling", bw, wall_t, bd, loc=(0, 0, bh - wall_t/2), mat=black_glossy)

    # Violet top counter panel
    create_box("CounterTop", bw + 0.02, 0.04, bd + 0.02, loc=(0, 0, bh + 0.02), mat=violet_matte)

    # The Door - pivoted at bottom front edge
    door_w, door_h, door_t = bw - 0.04, bh - 0.06, 0.03
    # Create the door mesh shifted so its pivot is at its bottom center
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    door = bpy.context.active_object
    door.name = "Door"
    door.scale = (door_w, door_t, door_h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    door.data.materials.append(black_glossy)
    
    # Move mesh geometry so origin is at the bottom edge of the door
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.transform.translate(value=(0, 0, door_h/2))
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Position and rotate the door to be open (downwards)
    door.location = (0, -bd/2, wall_t)
    door.rotation_euler[0] = math.radians(-85)

    # Door handle
    handle = create_box("Handle", 0.3, 0.04, 0.04, loc=(0, -door_t * 2, door_h * 0.7), mat=black_glossy)
    handle.parent = door

    # Door control panel (violet strip on the top edge of the door)
    cp = create_box("ControlPanel", door_w * 0.8, 0.02, 0.06, loc=(0, -door_t * 1.5, door_h * 0.9), mat=violet_matte)
    cp.parent = door

    # Visible Interior Dish Rack
    create_dish_rack(loc=Vector((0, 0, wall_t + 0.02)), mat=black_glossy)

if __name__ == "__main__":
    main()
