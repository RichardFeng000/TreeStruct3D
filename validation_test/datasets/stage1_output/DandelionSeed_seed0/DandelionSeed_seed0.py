import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Base Color'].default_value = color
    if name == "White":
        node_principled.inputs['Roughness'].default_value = 0.4
        node_principled.inputs['Specular IOR Level'].default_value = 0.2
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_achene():
    """Creates the elongated, tapered dark brown seed."""
    # Use a cylinder as base for better control over tapering than a sphere
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.04, depth=0.25, location=(0, 0, -0.125))
    achene = bpy.context.active_object
    achene.name = "Achene"
    
    # Use bmesh to taper the bottom and slightly round the top
    bm = bmesh.new()
    bm.from_mesh(achene.data)
    for v in bm.verts:
        if v.co.z < 0: # Taper the bottom half more aggressively
            factor = (v.co.z + 0.125) / 0.25  # Normalized from 0 to 1
            taper = 0.3 + 0.7 * (1.0 - factor)
            v.co.x *= taper
            v.co.y *= taper
        else: # Slightly round the top
            v.co.x *= 0.8
            v.co.y *= 0.8

    bm.to_mesh(achene.data)
    bm.free()
    bpy.ops.object.shade_smooth()
    
    mat = create_material("Brown", (0.1, 0.05, 0.02, 1.0))
    achene.data.materials.append(mat)
    return achene

def create_stalk():
    """Creates the thin stalk connecting seed to pappus."""
    # Slightly longer than before for better separation
    bpy.ops.mesh.primitive_cylinder_add(radius=0.01, depth=0.2, location=(0, 0, 0.1))
    stalk = bpy.context.active_object
    stalk.name = "Stalk"
    bpy.ops.object.shade_smooth()
    mat = create_material("Brown", (0.1, 0.05, 0.02, 1.0))
    stalk.data.materials.append(mat)
    return stalk

def create_pappus():
    """Creates the radiating organic parasol pappus."""
    num_filaments = 70
    radius_outer = 0.8
    hub_z = 0.2
    filament_thickness = 0.003
    mat = create_material("White", (0.95, 0.95, 0.95, 1.0))

    filaments = []
    for i in range(num_filaments):
        angle = (2 * math.pi / num_filaments) * i
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Organic variation per filament
        jitter_r = random.uniform(0.85, 1.15)
        jitter_z = random.uniform(-0.05, 0.05)
        
        curve_data = bpy.data.curves.new(name=f"Fil_{i}", type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.fill_mode = 'FULL'
        curve_data.bevel_depth = filament_thickness
        curve_data.bevel_resolution = 2

        polyline = curve_data.splines.new('BEZIER')
        polyline.bezier_points.add(2)

        # P0: Hub
        p0 = polyline.bezier_points[0]
        p0.co = Vector((0, 0, hub_z))
        p0.handle_left = Vector((0, 0, hub_z - 0.1))
        p0.handle_right = Vector((cos_a * 0.05, sin_a * 0.05, hub_z + 0.1))

        # P1: Mid-arc (The lift)
        mid_dist = radius_outer * 0.4 * jitter_r
        p1_z = hub_z + 0.3 + random.uniform(-0.05, 0.05)
        p1 = polyline.bezier_points[1]
        p1.co = Vector((cos_a * mid_dist, sin_a * mid_dist, p1_z))
        p1.handle_left = Vector((cos_a * (mid_dist - 0.1), sin_a * (mid_dist - 0.1), p1_z + 0.1))
        p1.handle_right = Vector((cos_a * (mid_dist + 0.1), sin_a * (mid_dist + 0.1), p1_z - 0.1))

        # P2: End point (The flare)
        end_dist = radius_outer * jitter_r
        end_z = hub_z + 0.1 + jitter_z
        p2 = polyline.bezier_points[2]
        p2.co = Vector((cos_a * end_dist, sin_a * end_dist, end_z))
        p2.handle_left = Vector((cos_a * (end_dist - 0.1), sin_a * (end_dist - 0.1), end_z + 0.1))
        p2.handle_right = Vector((cos_a * (end_dist + 0.1), sin_a * (end_dist + 0.1), end_z - 0.1))

        obj = bpy.data.objects.new(f"Fil_{i}", curve_data)
        bpy.context.scene.collection.objects.link(obj)
        obj.data.materials.append(mat)
        filaments.append(obj)

    # Convert and Join
    bpy.ops.object.select_all(action='DESELECT')
    for f in filaments:
        f.select_set(True)
    bpy.context.view_layer.objects.active = filaments[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    pappus = bpy.context.active_object
    pappus.name = "Pappus"
    bpy.ops.object.shade_smooth()
    return pappus

def main():
    clear_scene()
    achene = create_achene()
    stalk = create_stalk()
    pappus = create_pappus()
    
    # Combine everything into one mesh assembly
    bpy.ops.object.select_all(action='DESELECT')
    achene.select_set(True)
    stalk.select_set(True)
    pappus.select_set(True)
    bpy.context.view_layer.objects.active = pappus
    bpy.ops.object.join()
    bpy.context.active_object.name = "DandelionSeed"

if __name__ == "__main__":
    main()
