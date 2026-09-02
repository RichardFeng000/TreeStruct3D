import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_chopstick(name="Chopstick"):
    """Creates a single chopstick with squared-off top and tapered rounded tip."""
    # Dimensions for realistic chopsticks (30cm length)
    length = 0.30  
    top_size = 0.012 # 12 mm square width
    bottom_radius = 0.004 # 4 mm radius (rounded tip)
    segments = 64

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # Create top ring (Squared-off using Chebyshev distance for a square profile)
    top_ring = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        cx = math.cos(angle)
        cy = math.sin(angle)
        norm_factor = max(abs(cx), abs(cy))
        sq_x = (cx / norm_factor) * (top_size / 2)
        sq_y = (cy / norm_factor) * (top_size / 2)
        top_ring.append(bm.verts.new(Vector((sq_x, sq_y, length / 2))))

    # Create bottom ring (Rounded tip)
    bottom_ring = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        bx = math.cos(angle) * bottom_radius
        by = math.sin(angle) * bottom_radius
        bottom_ring.append(bm.verts.new(Vector((bx, by, -length / 2))))

    # Create faces connecting the two rings (the taper)
    for i in range(segments):
        v1 = top_ring[i]
        v2 = top_ring[(i + 1) % segments]
        v3 = bottom_ring[(i + 1) % segments]
        v4 = bottom_ring[i]
        bm.faces.new((v1, v2, v3, v4))

    # Close the ends (Cap faces)
    bm.faces.new(top_ring)
    bm.faces.new(reversed(bottom_ring))

    bm.to_mesh(mesh)
    bm.free()
    return obj

def main():
    clear_scene()

    # Create two chopsticks
    chop1 = create_chopstick("Chopstick_1")
    chop2 = create_chopstick("Chopstick_2")

    # To be "laid" crossed over each other, we rotate them 90 deg on X to lie flat in XY plane
    # Then rotate on Z to create the 'X' crossing.
    
    # Chopstick 1: Lying flat, angled at 30 degrees from center
    chop1.rotation_euler = (math.radians(90), 0, math.radians(30))
    
    # Chopstick 2: Lying flat, angled at -30 degrees from center
    chop2.rotation_euler = (math.radians(90), 0, math.radians(-30))

    # Offset slightly on Z to ensure they are stacked and not z-fighting
    # Since the diameter is ~12mm, an offset of 5mm keeps them close but separate
    chop1.location = Vector((0, 0, 0.006))
    chop2.location = Vector((0, 0, 0))

    # Material: Dark blue-black coloring
    mat = bpy.data.materials.new(name="DarkBlueBlack")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Extremely dark blue-black (R, G, B, A)
        bsdf.inputs['Base Color'].default_value = (0.01, 0.015, 0.04, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.2
        bsdf.inputs['Metallic'].default_value = 0.1

    chop1.data.materials.append(mat)
    chop2.data.materials.append(mat)

if __name__ == "__main__":
    main()
