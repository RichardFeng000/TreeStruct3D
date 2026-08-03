import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        # Wood-like roughness
        bsdf.inputs['Roughness'].default_value = 0.35
        bsdf.inputs['Specular IOR Level'].default_value = 0.2
    return mat

def create_box(name, width, depth, height, location):
    """Helper to create a box mesh."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale and position
    scale_vec = Vector((width, depth, height))
    for v in bm.verts:
        v.co *= scale_vec
        v.co += Vector(location)
        
    bm.to_mesh(mesh)
    bm.free()
    return obj

def create_cabinet():
    """Constructs the tall narrow storage cabinet."""
    # Dimensions
    width = 0.6
    depth = 0.45
    height = 2.1
    plinth_height = 0.08
    plinth_inset = 0.03
    bevel_amount = 0.008
    
    # Create Main Body
    # Center the body on X and Y, place it above the plinth height
    body_loc = (0, 0, plinth_height + (height / 2))
    body = create_box("CabinetBody", width, depth, height, body_loc)
    
    # Create Plinth Base
    p_width = width - (plinth_inset * 2)
    p_depth = depth - (plinth_inset * 2)
    p_loc = (0, 0, plinth_height / 2)
    plinth = create_box("CabinetPlinth", p_width, p_depth, plinth_height, p_loc)
    
    # Join plinth and body into one object
    bpy.context.view_layer.objects.active = body
    plinth.select_set(True)
    body.select_set(True)
    bpy.ops.object.join()
    
    final_obj = bpy.context.active_object
    final_obj.name = "StorageCabinet"

    # Bevel Modifier to create high-fidelity smooth edges on the rectangular box
    bev = final_obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = bevel_amount
    bev.segments = 3
    bev.limit_method = 'ANGLE'
    bev.angle_limit = 0.785398  # 45 degrees

    # Smooth Shading setup for Blender 5.0
    bpy.ops.object.shade_smooth()
    
    # "Smooth by Angle" modifier replaces the old auto-smooth property
    sm_angle = final_obj.modifiers.new(name="SmoothAngle", type='SMOOTH_BY_ANGLE')
    sm_angle.angle = 0.785398

    # Material: Dark Espresso / Walnut Finish
    dark_wood_color = (0.1, 0.06, 0.04, 1.0) # Deep espresso brown
    mat = create_material("EspressoWood", dark_wood_color)
    final_obj.data.materials.append(mat)

if __name__ == "__main__":
    clear_scene()
    create_cabinet()
