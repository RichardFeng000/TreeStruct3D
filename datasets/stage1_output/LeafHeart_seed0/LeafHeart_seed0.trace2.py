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
        bsdf.inputs['Base Color'].default_value = (0.5, 0.8, 0.4, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.6
    return mat

def generate_heart_leaf():
    """Generates a heart-shaped leaf using parametric mapping and organic deformation."""
    # Heart Parametric: x = 16 sin^3(t), y = 13 cos(t) - 5 cos(2t) - 2 cos(3t) - cos(4t)
    res_t = 80  # Angular resolution
    res_r = 20  # Radial resolution (from center to edge)

    mesh = bpy.data.meshes.new("HeartLeaf")
    obj = bpy.data.objects.new("HeartLeaf", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # Create vertices in concentric rings
    rings = [] # List of lists: [ring_index][vertex_index]
    
    # Center vertex (the very bottom point/origin of the leaf mapping)
    center_v = bm.verts.new(Vector((0, 0, 0)))
    rings.append([center_v])

    for r in range(1, res_r + 1):
        ring = []
        ratio = r / res_r
        for t_idx in range(res_t):
            t = (t_idx / res_t) * 2 * math.pi
            # Heart Equation
            hx = 16 * (math.sin(t)**3)
            hy = 13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t)
            
            # Scale to reasonable size and map based on radial ratio
            # We multiply by a factor (0.1) to keep it within a manageable scale
            pos = Vector((hx * 0.1 * ratio, hy * 0.1 * ratio, 0))
            ring.append(bm.verts.new(pos))
        rings.append(ring)

    # Create faces
    # First ring (Triangles connecting center to the first concentric loop)
    first_ring = rings[1]
    for i in range(res_t):
        v1 = first_ring[i]
        v2 = first_ring[(i + 1) % res_t]
        bm.faces.new((center_v, v1, v2))

    # Subsequent rings (Quads connecting concentric loops)
    for r in range(1, res_r):
        curr_ring = rings[r]
        next_ring = rings[r+1]
        for i in range(res_t):
            v_curr1 = curr_ring[i]
            v_curr2 = curr_ring[(i + 1) % res_t]
            v_next1 = next_ring[i]
            v_next2 = next_ring[(i + 1) % res_t]
            bm.faces.new((v_curr1, v_curr2, v_next2, v_next1))

    # Organic deformation for midrib and veins
    for v in bm.verts:
        x, y, z = v.co
        dist_from_center = math.sqrt(x*x + y*y)
        
        # 1. Central Midrib Crease (Central valley/ridge)
        # The midrib runs along the Y axis in our parametric setup
        # We create a dip centered at x=0, but extending from center to tip
        midrib_influence = math.exp(-(x**2) / 0.01)
        # Make it slightly concave (dip) and then convex towards the bottom point
        v.co.z -= midrib_influence * 0.05 * (1.0 - dist_from_center * 0.5)

        # 2. Overall Curvature (Gentle bowl shape)
        v.co.z += (x**2 + y**2) * 0.15

        # 3. Lateral Veins (Faint lines branching out)
        # Use radial patterns for veins
        angle = math.atan2(x, y if y != 0 else 0.001)
        vein_pattern = math.sin(angle * 6) * 0.03 
        fade = (dist_from_center * 2.0) / 2.5 # veins stronger towards edges
        v.co.z += vein_pattern * max(0, min(1, fade))

    bm.to_mesh(mesh)
    bm.free()

    # Add Thickness (Solidify)
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.005
    solid.offset = 0
    
    # Smooth out the organic shape
    subdiv = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subdiv.levels = 2

    # Set shading to smooth
    for poly in mesh.polygons:
        poly.use_smooth = True

    return obj

def main():
    clear_scene()
    
    leaf_mat = create_leaf_material()
    leaf_obj = generate_heart_leaf()
    
    # Assign material
    if not leaf_obj.data.materials:
        leaf_obj.data.materials.append(leaf_mat)
    else:
        leaf_obj.data.materials[0] = leaf_mat

    # Elevated perspective orientation
    # Rotate so it's viewed from an angle (not flat on ground)
    leaf_obj.rotation_euler[0] = math.radians(-60)
    leaf_obj.rotation_euler[2] = math.radians(45)

if __name__ == "__main__":
    main()
