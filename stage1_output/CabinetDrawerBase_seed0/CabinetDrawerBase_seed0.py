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
        # Base Color is usually the first input in Principled BSDF
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.6
        bsdf.inputs['Specular IOR Level'].default_value = 0.5 if 'Specular IOR Level' in bsdf.inputs else 0.5
    return mat

def create_box(name, w, d, h, location):
    """Creates a box with specific dimensions."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (w, d, h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj

def main():
    clear_scene()

    # Parametric Dimensions
    t = 0.02  # thickness of wood panels
    w = 0.6   # total width
    d = 0.4   # total depth
    h_back = 0.25 # height of the tall back panel
    h_side = 0.12 # height of side and front panels
    
    # Material: Rich Dark Wood (Dark Brown/Espresso)
    dark_wood_mat = create_material("DarkWood", (0.06, 0.03, 0.01, 1.0))

    # Construction components
    # Base Plate - the bottom of the drawer
    base = create_box(
        "Base", 
        w, d, t, 
        Vector((0, 0, t / 2))
    )
    
    # Back Panel (Tall) - Sits on top of base at the rear edge
    # Positioned such that it's flush with the back and extends to full width
    back = create_box(
        "BackPanel", 
        w, t, h_back, 
        Vector((0, (d / 2) - (t / 2), t + (h_back / 2)))
    )
    
    # Side Panels (Shorter) - Sit on top of base between front and back panel
    # Depth is d minus thickness of the back wall
    side_depth = d - t
    side_l = create_box(
        "SideL", 
        t, side_depth, h_side, 
        Vector((-w/2 + t/2, 0, t + (h_side / 2)))
    )
    side_r = create_box(
        "SideR", 
        t, side_depth, h_side, 
        Vector((w/2 - t/2, 0, t + (h_side / 2)))
    )
    
    # Front Panel (Shorter) - Sits on top of base and between sides
    # Width is total width minus two side thicknesses
    front_width = w - (2 * t)
    front = create_box(
        "FrontPanel", 
        front_width, t, h_side, 
        Vector((0, -(d / 2) + (t / 2), t + (h_side / 2)))
    )

    # Join components into a single mesh for unified processing
    objs = [base, back, side_l, side_r, front]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objs:
        obj.select_set(True)
    
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()
    
    drawer_box = bpy.context.active_object
    drawer_box.name = "CabinetDrawerBox"

    # Assign material
    if drawer_box.data.materials:
        drawer_box.data.materials[0] = dark_wood_mat
    else:
        drawer_box.data.materials.append(dark_wood_mat)

    # Add Bevel modifier for realistic rounded edges of the wood
    bevel_mod = drawer_box.modifiers.new(name="Bevel", type='BEVEL')
    bevel_mod.width = 0.004
    bevel_mod.segments = 3
    bevel_mod.limit_method = 'ANGLE'
    bevel_mod.angle_limit = 0.785398 # 45 degrees

    # Shading setup
    # We use shade_smooth combined with Weighted Normal modifier to keep flat faces flat
    bpy.ops.object.shade_smooth()
    
    wn_mod = drawer_box.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
    wn_mod.keep_sharp = True

if __name__ == "__main__":
    main()
