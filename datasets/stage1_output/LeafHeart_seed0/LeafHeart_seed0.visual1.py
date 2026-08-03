import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_leaf_material():
    """Creates a pale soft green material for the leaf."""
    mat = bpy.data.materials.new(name="LeafMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Pale soft green color (R, G, B, A)
        bsdf.inputs['Base Color'].default_value = (0.55, 0.85, 0.45, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.4
    return mat

def generate_heart_leaf():
    """Generates a heart-shaped leaf with proper orientation and detailed ribbing."""
    res_t = 128  # Higher resolution for smoother curves
    res_r = 32   # Radial resolution

    mesh = bpy.data.meshes.new("HeartLeaf")
    obj = bpy.data.objects.new("HeartLeaf", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # Use a parametric heart shape but invert Y so lobes are top, point is bottom
    # Heart Equation: x = 16 sin^3(t), y = 13 cos(t) - 5 cos(2t) - 2 cos(3t) - cos(4t)
    # To put the tip at the bottom and lobes at top, we use -y.
    rings = []
    center_v = bm.verts.new(Vector((0, 0, 0)))
    rings.append([center_v])

    for r in range(1, res_r + 1):
        ring = []
        ratio = r / res_r
        for t_idx in range(res_t):
            t = (t_idx / res_t) * 2 * math.pi
            hx = 16 * (math.sin(t)**3)
            hy = 13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t)
            
            # Scale and invert Y to ensure Point is at bottom, Lobes are at top
            pos = Vector((hx * 0.1 * ratio, -hy * 0.1 * ratio, 0))
            ring.append(bm.verts.new(pos))
        rings.append(ring)

    # Create faces
    first_ring = rings[1]
    for i in range(res_t):
        v1 = first_ring[i]
        v2 = first_ring[(i + 1) % res_t]
        bm.faces.new((center_v, v1, v2))

    for r in range(1, res_r):
        curr_ring = rings[r]
        next_ring = rings[r+1]
        for i in range(res_t):
            v_curr1 = curr_ring[i]
            v_curr2 = curr_ring[(i + 1) % res_t]
            v_next1 = next_ring[i]
            v_next2 = next_ring[(i + 1) % res_t]
            bm.faces.new((v_curr1, v_curr2, v_next2, v_next1))

    # Organic deformation
    for v in bm.verts:
        x, y, z = v.co
        dist_from_center = math.sqrt(x*x + y*y)
        
        # 1. Prominent Midrib Crease (Central ridge/valley along the Y axis)
        # Use a sharper function for the crease: abs(x)^power
        midrib_strength = 0.2 * math.exp(-abs(x)*5.0) 
        v.co.z += midrib_strength * (1.0 - dist_from_center * 0.4)

        # 2. Overall gentle curvature/fold
        # Give the leaf a slight 'V' fold along the midrib
        v.co.z += abs(x) * 0.3 
        # Add a general bow to the whole leaf
        v.co.z -= (dist_from_center**2) * 0.1

        # 3. Lateral Veins (Faint lines branching out from center)
        angle = math.atan2(x, y if y != 0 else 0.001)
        vein_freq = 8
        # Veins should be subtle dips/ridges radiating outwards
        vein_pattern = math.sin(angle * vein_freq) * 0.025
        fade = (dist_from_center * 3.0) / 4.0
        v.co.z += vein_pattern * max(0, min(1, fade))

    bm.to_mesh(mesh)
    bm.free()

    # Add thickness for a physical leaf feel
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.002
    solid.offset = 0
    
    subdiv = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subdiv.levels = 2

    for poly in mesh.polygons:
        poly.use_smooth = True

    return obj

def main():
    clear_scene()
    leaf_mat = create_leaf_material()
    leaf_obj = generate_heart_leaf()
    
    if not leaf_obj.data.materials:
        leaf_obj.data.materials.append(leaf_mat)
    else:
        leaf_obj.data.materials[0] = leaf_mat

    # Elevated perspective orientation (rotated for better viewing angle)
    leaf_obj.rotation_euler[0] = math.radians(-45)
    leaf_obj.rotation_euler[2] = math.radians(30)

if __name__ == "__main__":
    main()
