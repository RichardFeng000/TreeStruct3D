import bpy
import bmesh
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple principled BSDF material for wood finish."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Base Color
        bsdf.inputs['Base Color'].default_value = color
        # Wood-like roughness (semi-matte)
        bsdf.inputs['Roughness'].default_value = 0.35
        # Specular level for a polished finish
        if 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.2
        elif 'Specular' in bsdf.inputs:
            bsdf.inputs['Specular'].default_value = 0.2
    return mat

def create_box(name, width, depth, height, location):
    """Helper to create a box mesh with specific dimensions."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # create_cube size=2.0 means -1 to 1, so we scale by width/2 etc
    bmesh.ops.create_cube(bm, size=2.0)
    
    scale_vec = Vector((width / 2, depth / 2, height / 2))
    for v in bm.verts:
        v.co *= scale_vec # Apply scaling relative to center
        v.co += Vector(location)
        
    bm.to_mesh(mesh)
    bm.free()
    return obj

def create_cabinet():
    """Constructs the tall narrow storage cabinet."""
    # Dimensions for a 'tall and narrow' look
    width = 0.6
    depth = 0.45
    height = 2.1
    plinth_height = 0.08
    plinth_inset = 0.03
    bevel_amount = 0.01 # Slightly larger bevel for high-fidelity visual appeal
    
    # Create Main Body
    # Center the body on X and Y, place it above the plinth height
    body_loc = (0, 0, plinth_height + (height / 2))
    body = create_box("CabinetBody", width, depth, height, body_loc)
    
    # Create Plinth Base (the recessed bottom part)
    p_width = width - (plinth_inset * 2)
    p_depth = depth - (plinth_inset * 2)
    p_loc = (0, 0, plinth_height / 2)
    plinth = create_box("CabinetPlinth", p_width, p_depth, plinth_height, p_loc)
    
    # Join plinth and body into one object for a cohesive mesh
    bpy.context.view_layer.objects.active = body
    plinth.select_set(True)
    body.select_set(True)
    bpy.ops.object.join()
    
    final_obj = bpy.context.active_object
    final_obj.name = "StorageCabinet"

    # Use Bevel Modifier to create high-fidelity smooth edges on the rectangular box.
    # This avoids the need for Auto-Smooth by creating actual geometry transitions.
    bev = final_obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = bevel_amount
    bev.segments = 5 # High segment count for a very smooth rounded edge
    bev.limit_method = 'ANGLE'
    bev.angle_limit = 0.785398  # 45 degrees

    # Apply Smooth Shading. The Bevel modifier handles the normals so that 
    # flat panels stay flat while edges are curved.
    bpy.ops.object.shade_smooth()
    
    # Material: Dark Espresso / Walnut Finish (Deep Brown)
    dark_wood_color = (0.1, 0.06, 0.04, 1.0)
    mat = create_material("EspressoWood", dark_wood_color)
    final_obj.data.materials.append(mat)

if __name__ == "__main__":
    clear_scene()
    create_cabinet()
