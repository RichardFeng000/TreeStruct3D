import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.9):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_towel_layer(name, dimensions, position, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=position)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Bevel for organic rounded edges of a folded towel
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.bevel(bm, geom=bm.edges, offset=0.2, segments=6, affect='EDGES')
    bm.to_mesh(obj.data)
    bm.free()
    
    # Smooth the base
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    
    # Terry cloth texture - using multiple displacement passes for richness
    # Pass 1: General fluffiness
    tex1 = bpy.data.textures.new(name=f"TowelTex1_{name}", type='CLOUDS')
    tex1.noise_scale = 0.15
    disp1 = obj.modifiers.new(name="Fluff1", type='DISPLACE')
    disp1.texture = tex1
    disp1.strength = 0.08
    
    # Pass 2: Fine grain noise
    tex2 = bpy.data.textures.new(name=f"TowelTex2_{name}", type='CLOUDS')
    tex2.noise_scale = 0.03
    disp2 = obj.modifiers.new(name="Fluff2", type='DISPLACE')
    disp2.texture = tex2
    disp2.strength = 0.04
    
    obj.data.materials.append(material)
    return obj

def create_edge_stripe(name, dimensions, position, material):
    """Creates a thin stripe that is physically integrated into the side of the towel."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=position)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Very small bevel to prevent razor edges but keep it a stripe
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.bevel(bm, geom=bm.edges, offset=0.01, segments=2, affect='EDGES')
    bm.to_mesh(obj.data)
    bm.free()
    
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Colors
    sky_blue = (0.45, 0.75, 0.95, 1.0)     
    lightest_blue = (0.6, 0.85, 1.0, 1.0) 
    teal_accent = (0.0, 0.3, 0.35, 1.0)   
    
    mat_blue = create_material("Mat_Blue", sky_blue)
    mat_light_blue = create_material("Mat_LightBlue", lightest_blue)
    mat_teal = create_material("Mat_Teal", teal_accent)
    
    # Towel stack config
    width = 3.2   # X axis
    depth = 2.0   # Y axis
    thickness = 0.5 # Z axis
    num_layers = 3
    
    mats = [mat_blue, mat_light_blue]
    
    for i in range(num_layers):
        z_pos = (i * thickness) + (thickness / 2)
        # Add slight organic variations to the position and scale for "folded" feel
        x_off = random.uniform(-0.05, 0.05)
        y_off = random.uniform(-0.05, 0.05)
        w_var = width * random.uniform(0.98, 1.02)
        d_var = depth * random.uniform(0.97, 1.03)
        
        create_towel_layer(
            f"TowelLayer_{i}", 
            (w_var, d_var, thickness), 
            (x_off, y_off, z_pos), 
            mats[i % len(mats)]
        )

    # Integrate stripes directly on the side faces (X-edges)
    # We make them extremely thin and offset slightly so they sit ON the surface
    stripe_thick = 0.03 
    stripe_width = depth * 0.95 # Slightly shorter than towel to look woven in
    stripe_height = thickness * num_layers
    
    # Left side stripe (X-axis)
    create_edge_stripe(
        "Stripe_L", 
        (stripe_thick, stripe_width, stripe_height), 
        (-width/2 + stripe_thick/2, 0, (num_layers * thickness)/2), 
        mat_teal
    )
    
    # Right side stripe (X-axis)
    create_edge_stripe(
        "Stripe_R", 
        (stripe_thick, stripe_width, stripe_height), 
        (width/2 - stripe_thick/2, 0, (num_layers * thickness)/2), 
        mat_teal
    )

    bpy.context.view_layer.update()

if __name__ == "__main__":
    main()
