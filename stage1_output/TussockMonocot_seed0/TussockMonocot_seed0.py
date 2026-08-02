import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears all default objects from the scene."""
    if "Cube" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
    if "Camera" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Camera"], do_unlink=True)
    if "Light" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Light"], do_unlink=True)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, color):
    """Creates a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_tussock():
    # Increased blade count for a "dense" mound
    num_blades = 1200
    min_length = 1.5
    max_length = 3.0
    blade_width_base = 0.02
    segments_per_blade = 8
    spread_radius = 0.4

    bm = bmesh.new()

    for i in range(num_blades):
        # Determine radiation direction
        phi = random.uniform(0, 2 * math.pi)
        # Bias towards upper hemisphere but keep the "spherical tuft" look
        theta = random.uniform(0, math.pi * 0.85) 
        
        direction = Vector((
            math.sin(theta) * math.cos(phi),
            math.sin(theta) * math.sin(phi),
            math.cos(theta)
        ))

        # Randomize base position within a small clump
        start_pos = Vector((
            random.uniform(-spread_radius, spread_radius) * 0.5,
            random.uniform(-spread_radius, spread_radius) * 0.5,
            random.uniform(-0.1, 0.1)
        ))

        length = random.uniform(min_length, max_length)
        
        # Create an organic curve for the blade
        # We use a combination of linear growth and a quadratic arch
        arch_vec = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.5, 0.5))).normalized()
        arch_strength = random.uniform(0.4, 1.2)
        
        blade_verts = []
        for s in range(segments_per_blade + 1):
            t = s / segments_per_blade
            # Basic linear path
            pos = start_pos + direction * (length * t)
            # Arching effect: push the middle of the blade out, then curve back slightly at tip
            # Parabolic arc for organic feel
            curve_offset = arch_vec * (arch_strength * (t - t**2) * 1.5)
            # Slight additive noise/jitter to avoid perfect geometry
            jitter = Vector((random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05))) * t
            
            final_pos = pos + curve_offset + jitter
            blade_verts.append(bm.verts.new(final_pos))

        # Ribbon construction for blade width
        # Determine a consistent "width" vector perpendicular to the direction and arch
        cross_vec = direction.cross(arch_vec)
        if cross_vec.length < 0.1:
            cross_vec = Vector((0, 1, 0)) if abs(direction.x) > 0.9 else Vector((1, 0, 0))
        side_offset_vec = cross_vec.normalized() * blade_width_base

        blade_verts_side = []
        for s in range(segments_per_blade + 1):
            t = s / segments_per_blade
            # Taper width from base to a sharp point at the tip
            current_width = (1.0 - t) * blade_width_base
            v_main = blade_verts[s].co
            offset = side_offset_vec * (current_width / blade_width_base if blade_width_base != 0 else 0)
            blade_verts_side.append(bm.verts.new(v_main + offset))

        # Connect ribbon faces
        for s in range(segments_per_blade):
            v1 = blade_verts[s]
            v2 = blade_verts[s+1]
            v3 = blade_verts_side[s+1]
            v4 = blade_verts_side[s]
            bm.faces.new((v1, v2, v3, v4))

    bm.normal_update()
    mesh_data = bpy.data.meshes.new("TussockGrass")
    bm.to_mesh(mesh_data)
    bm.free()

    obj = bpy.data.objects.new("TussockGrass", mesh_data)
    bpy.context.collection.objects.link(obj)
    return obj

def main():
    clear_scene()
    grass_obj = create_tussock()
    # Vibrant green coloring as requested
    green_mat = create_material("VibrantGreen", (0.1, 0.8, 0.2, 1.0))
    grass_obj.data.materials.append(green_mat)
    grass_obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
