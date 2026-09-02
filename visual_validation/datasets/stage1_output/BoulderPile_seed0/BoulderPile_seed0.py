import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Removes all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        # Make rocks look a bit more matte/stony
        bsdf.inputs['Roughness'].default_value = 0.9
        bsdf.inputs['Specular IOR Level'].default_value = 0.2
    return mat

def generate_rock_mesh(name, size_range):
    """Generates a single angular rock using bmesh."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    # Start with a low-poly ico sphere to get basic volume and distribution
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)

    # Randomly perturb vertices to create an irregular, angular shape
    for v in bm.verts:
        perturbation = Vector((
            random.uniform(-0.6, 0.6),
            random.uniform(-0.6, 0.6),
            random.uniform(-0.6, 0.6)
        ))
        v.co += perturbation

    # Randomly scale the whole rock on each axis for variety in proportions
    scale_factor = random.uniform(size_range[0], size_range[1])
    axis_scales = Vector((
        random.uniform(0.7, 1.3),
        random.uniform(0.7, 1.3),
        random.uniform(0.4, 0.8) # Generally flatter rocks
    ))
    
    for v in bm.verts:
        v.co *= scale_factor
        v.co *= axis_scales

    # Collapse some random edges to create sharper facets
    edges = bm.edges[:]
    random.shuffle(edges)
    collapse_count = random.randint(2, 8)
    for i in range(min(collapse_count, len(edges))):
        try:
            bmesh.ops.collapse(bm, edges=[edges[i]])
        except:
            pass

    bm.to_mesh(mesh)
    bm.free()
    return obj

def scatter_rocks():
    clear_scene()

    # Define colors for the split
    white_gray = (0.85, 0.85, 0.82, 1.0)
    dark_black = (0.05, 0.05, 0.07, 1.0)

    mat_light = create_material("Mat_LightRock", white_gray)
    mat_dark = create_material("Mat_DarkRock", dark_black)

    num_rocks_per_side = 40
    spread = 6.0 # Area radius
    
    # Generate rocks for both sides
    for i in range(num_rocks_per_side * 2):
        # Split logic: first half light, second half dark
        if i < num_rocks_per_side:
            is_light = True
            mat = mat_light
            # Offset X to the left side (mostly)
            x_offset = -spread / 3.0
        else:
            is_light = False
            mat = mat_dark
            # Offset X to the right side (mostly)
            x_offset = spread / 3.0

        # Random size variation
        size_range = (0.2, 0.8) if random.random() > 0.3 else (0.1, 0.4)
        rock_name = f"Rock_{'Light' if is_light else 'Dark'}_{i}"
        rock = generate_rock_mesh(rock_name, size_range)
        
        # Assign material
        rock.data.materials.append(mat)

        # Position: Cluster them but allow some overlap in the middle
        x = x_offset + random.uniform(-spread / 2, spread / 2)
        y = random.uniform(-spread / 2, spread / 2)
        z = 0 # Base on flat plane

        rock.location = (x, y, z)

        # Random rotation for natural look
        rock.rotation_euler = (
            random.uniform(0, math.pi * 2),
            random.uniform(0, math.pi * 2),
            random.uniform(0, math.pi * 2)
        )

        # Slightly adjust Z so they sit on the plane rather than centered in it
        # We calculate a rough radius of the rock based on its size_range center
        approx_radius = (size_range[0] + size_range[1]) / 4.0
        rock.location.z += approx_radius

if __name__ == "__main__":
    scatter_rocks()
