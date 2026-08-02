import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Removes all existing objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple diffuse material using Principled BSDF."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_bsdf.inputs['Base Color'].default_value = color
    node_bsdf.inputs['Roughness'].default_value = 0.7
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_bowl():
    """Creates a wide, shallow bowl with a pastel purple exterior."""
    radius = 5.0
    height_scale = 0.3
    wall_thickness = 0.3
    
    # Create base sphere
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(0, 0, 0))
    bowl = bpy.context.active_object
    bowl.name = "PlantContainer"
    
    # Squash to make it shallow
    bowl.scale[2] = height_scale
    bpy.ops.object.transform_apply(scale=True)
    
    # Use bmesh to remove the top half
    bm = bmesh.new()
    bm.from_mesh(bowl.data)
    
    # Delete faces that are above a certain Z threshold (the "opening" of the bowl)
    faces_to_delete = [f for f in bm.faces if f.calc_center_median().z > 0.1]
    bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')
    
    bm.to_mesh(bowl.data)
    bm.free()
    
    # Add thickness via Solidify Modifier
    mod = bowl.modifiers.new(name="Thickness", type='SOLIDIFY')
    mod.thickness = wall_thickness
    mod.offset = 1.0 # Offset outward to preserve internal dimensions
    
    bpy.context.view_layer.objects.active = bowl
    bpy.ops.object.shade_smooth()
    
    # Material: Light pastel purple
    purple_mat = create_material("PastelPurple", (0.8, 0.7, 0.9, 1.0))
    bowl.data.materials.append(purple_mat)
    
    return bowl

def create_soil():
    """Creates a sandy soil disk inside the bowl."""
    radius = 4.6
    depth = 0.8
    
    # Use a cylinder for soil base
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=radius, depth=depth, location=(0, 0, -0.1))
    soil_obj = bpy.context.active_object
    soil_obj.name = "Soil"
    
    # Jitter the top surface for a natural sandy look
    bm = bmesh.new()
    bm.from_mesh(soil_obj.data)
    
    for v in bm.verts:
        if v.co.z > 0: # Top vertices
            v.co.z += random.uniform(-0.2, 0.2)
            v.co.x += random.uniform(-0.1, 0.1)
            v.co.y += random.uniform(-0.1, 0.1)
            
    bm.to_mesh(soil_obj.data)
    bm.free()
    
    # Material: Sandy Brown
    brown_mat = create_material("SandyBrown", (0.35, 0.25, 0.15, 1.0))
    soil_obj.data.materials.append(brown_mat)
    
    return soil_obj

def create_mushroom(location):
    """Creates a single mushroom plant at the given location."""
    stem_height = random.uniform(1.2, 2.5)
    cap_radius = random.uniform(0.6, 1.3)
    cap_scale_z = 0.4
    
    # --- Create Stem ---
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.15, radius2=0.25, depth=stem_height, location=(location[0], location[1], stem_height / 2))
    stem_obj = bpy.context.active_object
    stem_obj.name = "MushroomStem"
    bpy.context.view_layer.objects.active = stem_obj
    bpy.ops.object.shade_smooth()

    # --- Create Cap ---
    bpy.ops.mesh.primitive_uv_sphere_add(radius=cap_radius, location=(location[0], location[1], stem_height))
    cap_obj = bpy.context.active_object
    cap_obj.name = "MushroomCap"
    
    # Squash sphere into a cap shape
    cap_obj.scale[2] = cap_scale_z
    bpy.ops.object.transform_apply(scale=True)
    
    # Remove the bottom half of the sphere to make it a dome
    bm_cap = bmesh.new()
    bm_cap.from_mesh(cap_obj.data)
    faces_to_delete = [f for f in bm_cap.faces if f.calc_center_median().z < (stem_height - 0.1)]
    bmesh.ops.delete(bm_cap, geom=faces_to_delete, context='FACES')
    bm_cap.to_mesh(cap_obj.data)
    bm_cap.free()
    
    bpy.context.view_layer.objects.active = cap_obj
    bpy.ops.object.shade_smooth()
    
    # Material: Off-white/Cream
    cream_mat = create_material("MushroomCream", (0.95, 0.9, 0.8, 1.0))
    stem_obj.data.materials.append(cream_mat)
    cap_obj.data.materials.append(cream_mat)
    
    return [stem_obj, cap_obj]

def main():
    clear_scene()
    
    # Create the container components
    create_bowl()
    create_soil()
    
    # Create a few mushrooms distributed in the soil
    num_mushrooms = 6
    max_radius = 3.8 # Stay inside bowl edges
    
    for _ in range(num_mushrooms):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0.5, max_radius)
        x = math.cos(angle) * dist
        y = math.sin(angle) * dist
        # Place mushrooms on the soil surface (around Z=0.3 due to bowl bottom/soil height)
        create_mushroom((x, y, 0.3))

if __name__ == "__main__":
    main()
