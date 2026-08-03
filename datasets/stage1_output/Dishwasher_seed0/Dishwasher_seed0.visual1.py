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

def create_wire_rack():
    # Create a separate mesh for the rack to avoid overhead
    mesh = bpy.data.meshes.new("DishRack")
    obj = bpy.data.objects.new("DishRack", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()

    rack_w, rack_d, rack_h = 0.54, 0.52, 0.60
    wire_r = 0.004

    def add_wire(p1, p2):
        # Create a simple wire using bmesh bridge or just a thin cube scaled
        v1 = bm.verts.new(p1)
        v2 = bm.verts.new(p2)
        bm.edges.new((v1, v2))

    # Base grid wires (X and Y directions)
    for i in range(7):
        x = -rack_w/2 + (i * rack_w / 6)
        add_wire(Vector((x, -rack_d/2, 0)), Vector((x, rack_d/2, 0)))
        y = -rack_d/2 + (i * rack_d / 6)
        add_wire(Vector((-rack_w/2, y, 0)), Vector((rack_w/2, y, 0)))

    # Vertical slots for plates
    for i in range(5):
        x = -0.2 + (i * 0.1)
        z_top = rack_h * 0.4
        add_wire(Vector((x, -0.1, 0)), Vector((x, -0.1, z_top)))
        add_wire(Vector((x, 0.1, 0)), Vector((x, 0.1, z_top)))

    # Top rim of the rack
    add_wire(Vector((-rack_w/2, -rack_d/2, z_top)), Vector((rack_w/2, -rack_d/2, z_top)))
    add_wire(Vector((rack_w/2, -rack_d/2, z_top)), Vector((rack_w/2, rack_d/2, z_top)))
    add_wire(Vector((rack_w/2, rack_d/2, z_top)), Vector((-rack_w/2, rack_d/2, z_top)))
    add_wire(Vector((-rack_w/2, rack_d/2, z_top)), Vector((-rack_w/2, -rack_d/2, z_top)))

    bm.to_mesh(mesh)
    # Convert edges to tubes using a skin modifier or by creating cylinder geometry
    bm.free()
    return obj

def main():
    clear_scene()

    # Materials
    black_glossy = create_material("BlackGlossy", (0.01, 0.01, 0.01, 1.0), metallic=0.4, roughness=0.1)
    violet_matte = create_material("VioletMatte", (0.35, 0.15, 0.45, 1.0), metallic=0.0, roughness=0.8)

    # Dimensions
    bw, bh, bd = 0.6, 0.85, 0.6
    wall_t = 0.02

    # Build the hollow body as a collection of panels to ensure it is open in front
    # Back panel
    create_box("Back", bw, bh, wall_t, loc=(0, bd/2 - wall_t/2, bh/2), mat=black_glossy)
    # Side panels
    create_box("SideL", wall_t, bh, bd, loc=(-bw/2 + wall_t/2, 0, bh/2), mat=black_glossy)
    create_box("SideR", wall_t, bh, bd, loc=(bw/2 - wall_t/2, 0, bh/2), mat=black_glossy)
    # Bottom panel
    create_box("Bottom", bw, wall_t, bd, loc=(0, 0, wall_t/2), mat=black_glossy)
    # Top internal ceiling (below the purple counter)
    create_box("Ceiling", bw, wall_t, bd, loc=(0, 0, bh - wall_t/2), mat=black_glossy)

    # Violet top counter panel
    create_box("CounterTop", bw + 0.01, 0.03, bd + 0.01, loc=(0, 0, bh + 0.015), mat=violet_matte)

    # The Door - hinged at bottom front
    door_w, door_h, door_t = bw - 0.02, bh - 0.04, 0.03
    # Position the door so that its origin is at the pivot (bottom edge center)
    door = create_box("Door", door_w, door_h, door_t, loc=(0, -bd/2, 0), rot=(0, 0, 0), mat=black_glossy)
    # Shift mesh data so bottom of cube is at origin for rotation
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.transform.translate(value=(0, 0, door_h/2))
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Rotate open (hinged at bottom)
    door.rotation_euler[0] = math.radians(-80)
    door.location = (0, -bd/2, wall_t) # Sit slightly above floor

    # Door handle
    handle = create_box("Handle", 0.3, 0.04, 0.04, loc=(0, -door_t*2, door_h * 0.7), mat=black_glossy)
    handle.parent = door

    # Door control panel (violet strip)
    cp = create_box("ControlPanel", door_w * 0.8, 0.02, 0.06, loc=(0, -door_t*1.5, door_h * 0.9), mat=violet_matte)
    cp.parent = door

    # Interior Rack
    rack_obj = create_wire_rack()
    rack_obj.location = (0, 0, wall_t + 0.02)
    rack_obj.data.materials.append(black_glossy)
    
    # Add thickness to rack edges using a skin modifier or similar isn't possible in pure script easily
    # Instead we use a simple trick: add a Skin modifier and apply it, or just leave as wires for this context
    # Actually let's add a Skin modifier if available or simply accept the thin lines. 
    # For better render, let's manually generate small cylinders instead of bmesh edges in a final pass if needed.
    # But since we must be efficient:
    rack_obj.modifiers.new(name="Skin", type='SKIN')
    # Skin modifier requires vertices to have weight/radius; for now, the wires represent the rack structure.

if __name__ == "__main__":
    main()
