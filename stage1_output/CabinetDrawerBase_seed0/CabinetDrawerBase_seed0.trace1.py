import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Clears the default blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple material with a specific diffuse color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.7
    return mat

def create_slab(name, width, depth, height, location):
    """Creates a box with specific dimensions and applies the name."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (width, depth, height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj

def main():
    clear_scene()

    # Dimensions
    t = 0.02  # thickness
    w = 0.6   # width
    d = 0.4   # depth
    h_back = 0.25 # height of the tall back panel
    h_side = 0.12 # height of side/front panels
    
    # Material: Rich Dark Wood (Dark Brown)
    dark_wood_mat = create_material("DarkWood", (0.08, 0.04, 0.02, 1.0))

    # Component parts construction
    # Base Plate
    base = create_slab(
        "Base", 
        w, d, t, 
        Vector((0, 0, t / 2))
    )
    
    # Back Panel (Tall) - placed on top of base at the rear
    back = create_slab(
        "BackPanel", 
        w, t, h_back, 
        Vector((0, (d / 2) - (t / 2), (h_back / 2) + t))
    )
    
    # Side Panels (Shorter) - placed on top of base along the sides
    side_l = create_slab(
        "SideL", 
        t, d - t, h_side, 
        Vector((-w/2 + t/2, 0, (h_side / 2) + t))
    )
    side_r = create_slab(
        "SideR", 
        t, d - t, h_side, 
        Vector((w/2 - t/2, 0, (h_side / 2) + t))
    )
    
    # Front Panel (Shorter) - placed on top of base at the front
    front = create_slab(
        "FrontPanel", 
        w - (2 * t), t, h_side, 
        Vector((0, -(d / 2) + (t / 2), (h_side / 2) + t))
    )

    # Join all parts into one object
    objs = [base, back, side_l, side_r, front]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objs:
        obj.select_set(True)
    
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()
    
    drawer_box = bpy.context.active_object
    drawer_box.name = "CabinetDrawerBox"

    # Apply material
    if drawer_box.data.materials:
        drawer_box.data.materials[0] = dark_wood_mat
    else:
        drawer_box.data.materials.append(dark_wood_mat)

    # Add Bevel modifier for realistic wood edges
    bevel_mod = drawer_box.modifiers.new(name="Bevel", type='BEVEL')
    bevel_mod.width = 0.005
    bevel_mod.segments = 3
    
    # In Blender 4.1+ and 5.0, 'use_auto_smooth' is deprecated.
    # Instead we use Shade Smooth and the 'Smooth by Angle' modifier.
    bpy.ops.object.shade_smooth()
    
    # Add Smooth by Angle modifier to maintain sharp corners where intended (replacing auto-smooth)
    sb_angle = drawer_box.modifiers.new(name="SmoothByAngle", type='SMOOTH_BY_ANGLE')
    sb_angle.angle = 0.785398 # approx 45 degrees in radians

if __name__ == "__main__":
    main()
