import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Removes all objects from the current scene."""
    if bpy.context.active_object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_lobed_profile(center, normal, radius, amplitude, ribs, resolution):
    """Generates a list of vertices forming a lobed circle."""
    vertices = []
    # Create local coordinate system for the ring (orthonormal basis)
    up = normal.normalized()
    if abs(up.x) < 0.9:
        right = up.cross(Vector((1, 0, 0))).normalized()
    else:
        right = up.cross(Vector((0, 1, 0))).normalized()
    forward = right.cross(up).normalized()

    for i in range(resolution):
        theta = (2 * math.pi * i) / resolution
        # Radius varies according to the number of ribs
        r = radius + amplitude * math.cos(ribs * theta)
        x = math.cos(theta) * r
        y = math.sin(theta) * r
        pos = center + (right * x) + (forward * y)
        vertices.append(pos)
    return vertices

def build_cactus():
    clear_scene()

    # Parameters for the columnar cactus
    main_height = 8.0
    main_radius = 0.6
    rib_count = 8
    rib_amplitude = 0.15
    resolution = 64  # Increased for higher fidelity base mesh
    segments = 80    # Higher vertical resolution

    bm = bmesh.new()

    # --- 1. Create Main Stem ---
    main_rings = []
    for i in range(segments + 1):
        z = (i / segments) * main_height
        # Taper slightly towards the top for a natural look
        taper = 1.0 - (z / main_height) * 0.25
        r = main_radius * taper
        amp = rib_amplitude * taper
        
        center = Vector((0, 0, z))
        normal = Vector((0, 0, 1))
        
        ring_verts_pos = create_lobed_profile(center, normal, r, amp, rib_count, resolution)
        current_ring = [bm.verts.new(v) for v in ring_verts_pos]
        main_rings.append(current_ring)

    # Connect main stem rings with faces
    for i in range(segments):
        r1 = main_rings[i]
        r2 = main_rings[i+1]
        for j in range(resolution):
            v1 = r1[j]
            v2 = r1[(j + 1) % resolution]
            v3 = r2[(j + 1) % resolution]
            v4 = r2[j]
            bm.faces.new((v1, v2, v3, v4))

    # --- 2. Create Curved Arm ---
    arm_segments = 60
    arm_radius_start = main_radius * 0.85
    arm_radius_end = main_radius * 0.5
    arm_height_start = 1.8  # Lower left branching point
    
    # Path for the arm: Quadratic Bezier Curve
    p0 = Vector((0, 0, arm_height_start)) # Start inside stem
    p1 = Vector((-2.5, -1.0, arm_height_start + 2.0)) # Mid-point (out and left)
    p2 = Vector((-3.5, 0.5, arm_height_start + 6.5))  # End point

    def get_bezier_point(t):
        return (1-t)**2 * p0 + 2*(1-t)*t * p1 + t**2 * p2

    def get_bezier_tangent(t):
        # Derivative of Quadratic Bezier: 2(1-t)(P1-P0) + 2t(P2-P1)
        return (2*(1-t)*(p1 - p0) + 2*t*(p2 - p1)).normalized()

    arm_rings = []
    for i in range(arm_segments + 1):
        t = i / arm_segments
        center = get_bezier_point(t)
        tangent = get_bezier_tangent(t)
        
        # Taper the radius and rib amplitude along the arm length
        r = arm_radius_start + t * (arm_radius_end - arm_radius_start)
        amp = rib_amplitude * 0.85 * (1.0 - t * 0.3)
        
        ring_verts_pos = create_lobed_profile(center, tangent, r, amp, rib_count, resolution)
        current_ring = [bm.verts.new(v) for v in ring_verts_pos]
        arm_rings.append(current_ring)

    # Connect arm rings with faces
    for i in range(arm_segments):
        r1 = arm_rings[i]
        r2 = arm_rings[i+1]
        for j in range(resolution):
            v1 = r1[j]
            v2 = r1[(j + 1) % resolution]
            v3 = r2[(j + 1) % resolution]
            v4 = r2[j]
            bm.faces.new((v1, v2, v3, v4))

    # Cap the tops of both the main stem and the arm to make them solid manifolds
    def cap_ring(ring):
        if not ring: return
        center_pos = sum((v.co for v in ring), Vector((0, 0, 0))) / len(ring)
        cv = bm.verts.new(center_pos)
        for j in range(len(ring)):
            bm.faces.new((cv, ring[j], ring[(j + 1) % len(ring)]))

    cap_ring(main_rings[-1])
    cap_ring(arm_rings[-1])

    # --- Finalize Mesh and Object Creation ---
    # Correct way to transfer bmesh data to a Blender mesh object in API 5.0
    cactus_mesh = bpy.data.meshes.new("CactusMesh")
    bm.to_mesh(cactus_mesh)
    bm.free()

    obj = bpy.data.objects.new("ColumnarCactus", cactus_mesh)
    bpy.context.collection.objects.link(obj)

    # Set smooth shading for a high-fidelity look
    for poly in obj.data.polygons:
        poly.use_smooth = True

    # Assign plain white material as requested
    mat = bpy.data.materials.new(name="CactusWhite")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Base Color (RGBA)
        bsdf.inputs['Base Color'].default_value = (1, 1, 1, 1)
        # Higher roughness for a matte "base mesh" appearance
        bsdf.inputs['Roughness'].default_value = 0.7
    obj.data.materials.append(mat)

    # Add Subdivision Surface modifier to further smooth the lobed geometry
    subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 1
    subdiv.render_levels = 2

if __name__ == "__main__":
    build_cactus()
