import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    objs = [obj for obj in bpy.data.objects]
    for obj in objs:
        bpy.data.objects.remove(obj, do_unlink=True)
    
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, color, specular=0.1):
    """Creates a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.8 if specular < 0.2 else 0.4
        bsdf.inputs['Specular IOR Level'].default_value = specular
    return mat

def create_bowl():
    """Creates a wide shallow bowl with a low cylindrical profile and dark matte exterior."""
    # Profile points: (X=radius, Z=height)
    # Designing for a wider, flatter bottom and more vertical walls.
    profile_points = [
        (0.0, 0.0),      # Center bottom
        (1.6, 0.0),      # Inner bottom edge
        (1.7, 0.05),     # Outer bottom corner
        (1.8, 0.4),      # Lower wall (more vertical)
        (2.3, 0.5),      # Top outer rim peak
        (2.2, 0.55),     # Rim thickness top
        (1.7, 0.5),      # Interior rim edge
        (1.6, 0.1),      # Inner wall slope
        (0.0, 0.1)       # Closing the base (slightly offset for volume)
    ]

    mesh = bpy.data.meshes.new("BowlMesh")
    obj = bpy.data.objects.new("FruitBowl", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    verts = [bm.verts.new((p[0], 0, p[1])) for p in profile_points]
    for i in range(len(verts) - 1):
        bm.edges.new((verts[i], verts[i+1]))

    bm.to_mesh(mesh)
    bm.free()

    screw_mod = obj.modifiers.new(name="Screw", type='SCREW')
    screw_mod.angle = 2 * math.pi
    screw_mod.steps = 64
    screw_mod.axis = 'Z'

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=screw_mod.name)
    
    for poly in obj.data.polygons:
        poly.use_smooth = True

    # Material: Dark matte exterior
    dark_matte = create_material("BowlMat", (0.05, 0.05, 0.05, 1.0), specular=0.05)
    obj.data.materials.append(dark_matte)

    return obj

def create_fruit(name, radius, location):
    """Creates a spherical fruit with varied colors."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location, segments=32, ring_count=16)
    fruit = bpy.context.active_object
    fruit.name = name
    for poly in fruit.data.polygons:
        poly.use_smooth = True
    
    # Give fruits some varied colors (reds, greens, yellows)
    colors = [
        (0.8, 0.1, 0.1, 1.0), # Red
        (0.3, 0.6, 0.1, 1.0), # Green
        (0.9, 0.8, 0.2, 1.0), # Yellow
        (0.6, 0.3, 0.7, 1.0)  # Purple/Plum
    ]
    fruit_mat = create_material(f"FruitMat_{name}", random.choice(colors), specular=0.4)
    fruit.data.materials.append(fruit_mat)
    return fruit

def populate_bowl():
    """Places fruits so they realistically sit in the bowl."""
    num_fruits = 28
    inner_radius = 1.5
    max_height = 0.4
    
    placed_fruits = []
    
    for i in range(num_fruits):
        r = random.uniform(0.1, 0.2)
        placed = False
        attempts = 0
        while not placed and attempts < 150:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, inner_radius - r)
            x = math.cos(angle) * dist
            y = math.sin(angle) * dist
            # Start from the bottom surface (Z=0.1 is the base interior center)
            z = random.uniform(0.1 + r, max_height + r)
            
            loc = Vector((x, y, z))
            
            too_close = False
            for other_r, other_loc in placed_fruits:
                if (loc - other_loc).length < (r + other_r) * 0.9:
                    too_close = True
                    break
            
            # Ensure the fruit is roughly inside the bowl's interior volume
            # Interior radius at bottom is ~1.6, height ~0.5.
            if dist > (inner_radius - r):
                too_close = True

            if too_close:
                attempts += 1
            else:
                create_fruit(f"Fruit_{i}", r, loc)
                placed_fruits.append((r, loc))
                placed = True

def main():
    clear_scene()
    create_bowl()
    populate_bowl()
    bpy.context.view_layer.update()

if __name__ == "__main__":
    main()
