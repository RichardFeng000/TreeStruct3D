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
    # Parameters: slightly increased for visibility in render
    length = 0.30  # 30 cm
    top_size = 0.012 # 12 mm square width (squared-off top)
    bottom_radius = 0.004 # 4 mm radius (rounded tip)
    segments = 64

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # Create top ring (Squared-off)
    top_ring = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        cx = math.cos(angle)
        cy = math.sin(angle)
        
        # Convert circle to square via Chebyshev distance scaling
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

    # Arrange them to be crossed over each other
    # Chopstick 1: angled across the center
    chop1.rotation_euler = (math.radians(15), 0, math.radians(30))
    
    # Chopstick 2: opposite angle
    chop2.rotation_euler = (math.radians(-15), 0, math.radians(-30))

    # Offset slightly on Z to prevent z-fighting and show they are stacked
    chop1.location = Vector((0, 0, 0.005))
    chop2.location = Vector((0, 0, -0.005))

    # Dark blue-black material
    mat = bpy.data.materials.new(name="DarkBlueBlack")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Very dark blue-black (R, G, B, A)
        bsdf.inputs['Base Color'].default_value = (0.02, 0.03, 0.08, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.25
        # Slight metallic look often found in lacquered chopsticks
        bsdf.inputs['Metallic'].default_value = 0.1

    chop1.data.materials.append(mat)
    chop2.data.materials.append(mat)

if __name__ == "__main__":
    main()
