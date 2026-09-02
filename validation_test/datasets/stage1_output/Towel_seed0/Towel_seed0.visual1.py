import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.9):
    """Creates a principled BSDF material with specified color and roughness."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_towel_layer(name, dimensions, position, material):
    """Creates a single folded layer of the towel with fluffiness."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=position)
    obj = bpy.context.active_object
    obj.name = name
    
    # Scale to rectangular slab
    obj.scale = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Round corners for softness using Bevel
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.bevel(bm, geom=bm.edges, offset=0.15, segments=4, affect='EDGES')
    bm.to_mesh(obj.data)
    bm.free()
    
    # Subsurf for smooth geometry base
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3
    
    # Terry cloth fluffiness: high-frequency noise displacement
    tex = bpy.data.textures.new(name=f"TowelTex_{name}", type='CLOUDS')
    tex.noise_scale = 0.02 # Very fine grain for fabric
    
    disp = obj.modifiers.new(name="Fluff", type='DISPLACE')
    disp.texture = tex
    disp.strength = 0.06  # Increased strength for more visible texture
    
    obj.data.materials.append(material)
    return obj

def create_accent_stripe(name, dimensions, position, material):
    """Creates a thin decorative stripe on the edge."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=position)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Give the stripe a slight bevel so it's not razor sharp
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.bevel(bm, geom=bm.edges, offset=0.02, segments=2, affect='EDGES')
    bm.to_mesh(obj.data)
    bm.free()
    
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Colors: Light sky blue and variants
    sky_blue = (0.4, 0.7, 0.9, 1.0)     
    lightest_blue = (0.6, 0.85, 1.0, 1.0) 
    teal_accent = (0.0, 0.4, 0.4, 1.0)   
    
    mat_blue = create_material("Mat_Blue", sky_blue)
    mat_light_blue = create_material("Mat_LightBlue", lightest_blue)
    mat_teal = create_material("Mat_Teal", teal_accent)
    
    # Towel stack parameters
    width = 3.0   # X axis (long side)
    depth = 2.0   # Y axis (short side)
    thickness = 0.45 # Z axis (per layer thickness)
    num_layers = 3
    
    materials_pool = [mat_blue, mat_light_blue]
    
    for i in range(num_layers):
        # Stack layers with slight organic offsets
        z_pos = (i * thickness) + (thickness / 2)
        x_off = random.uniform(-0.03, 0.03)
        y_off = random.uniform(-0.03, 0.03)
        
        mat = materials_pool[i % len(materials_pool)]
        layer_obj = create_towel_layer(
            f"TowelLayer_{i}", 
            (width, depth, thickness), 
            (x_off, y_off, z_pos), 
            mat
        )
        # Subtle random tilt for organic folding look
        layer_obj.rotation_euler[0] = random.uniform(-0.01, 0.01)
        layer_obj.rotation_euler[1] = random.uniform(-0.01, 0.01)

    # Create thin teal stripe accents on the folded edges (Y-axis sides)
    # Instead of huge walls, we create narrow ribbons along the side edges
    stripe_w = 0.08  # Thin width
    stripe_d = depth # Match towel depth
    stripe_h = thickness * num_layers # Full stack height
    
    # Positioning stripes at the ends of the long axis (X)
    # Shift slightly outward to be visible on surface but embedded
    create_accent_stripe(
        "Stripe_L", 
        (stripe_w, stripe_d, stripe_h * 0.1), # Thin band height for a "detail" look
        (-width/2, 0, (num_layers * thickness)/2), 
        mat_teal
    )
    
    # Create multiple thin stripes on the edge for a more professional fabric look
    for j in range(3):
        z_offset = ((num_layers * thickness)/2) - (thickness * (num_layers/2)) + (j * thickness)
        create_accent_stripe(
            f"Stripe_R_{j}", 
            (stripe_w, stripe_d, thickness * 0.3), 
            (width/2, 0, z_offset), 
            mat_teal
        )

    # Ensure all objects are in the scene
    bpy.context.view_layer.update()

if __name__ == "__main__":
    main()
