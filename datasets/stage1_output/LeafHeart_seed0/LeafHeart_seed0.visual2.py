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
        bsdf.inputs['Base Color'].default_value = (0.58, 0.88, 0.48, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.3
    return mat

def generate_heart_leaf():
    """Generates a heart-shaped leaf with a linear midrib and organic veins."""
    # Parametric Heart Formula: x = 16 sin^3(t), y = 13 cos(t) - 5 cos(2t) - 2 cos(3t) - cos(4t)
    # t from 0 to 2*pi. Tip is at t=pi, lobes at t=0/2*pi.
    
    res_len = 64  # resolution along the midrib (Y-axis essentially)
    res_wid = 32  # resolution across the leaf width

    mesh = bpy.data.meshes.new("HeartLeaf")
    obj = bpy.data.objects.new("HeartLeaf", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    # Create a grid of vertices mapped to the heart shape
    # v from 0 (tip at t=pi) to 1 (top center dip at t=0/2*pi)
    verts_grid = []
    for i in range(res_len + 1):
        v_param = i / res_len
        # Map v_param [0, 1] to t [pi, 0]
        t = math.pi * (1 - v_param)
        
        # Boundary point at this t
        bx = 16 * (math.sin(t)**3)
        by = 13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t)
        
        # Midrib point is (0, by)
        row = []
        for j in range(res_wid + 1):
            u = (j / res_wid) * 2 - 1  # u from -1 to 1
            # Interpolate between boundary x and center (0)
            # For a full heart, we use the symmetry: left side is -bx, right side is +bx
            x_pos = u * bx * 0.1
            y_pos = by * 0.1
            z_pos = 0.0
            row.append(bm.verts.new(Vector((x_pos, y_pos, z_pos))))
        verts_grid.append(row)

    # Create faces for the grid
    for i in range(res_len):
        for j in range(res_wid):
            v1 = verts_grid[i][j]
            v2 = verts_grid[i+1][j]
            v3 = verts_grid[i+1][j+1]
            v4 = verts_grid[i][j+1]
            bm.faces.new((v1, v2, v3, v4))

    # Organic deformation for midrib and veins
    for i in range(res_len + 1):
        v_param = i / res_len
        for j in range(res_wid + 1):
            u = (j / res_wid) * 2 - 1
            v = verts_grid[i][j]
            x, y, z = v.co

            # 1. Central Midrib Ridge: a sharp line along the center axis (x=0)
            # The ridge should be strongest at the base and fade slightly towards top/bottom
            midrib_strength = 0.15 * math.exp(-abs(u)*8.0)
            v.co.z += midrib_strength

            # 2. Leaf "V" fold: sides curve upwards from the center
            v.co.z += abs(u) * 0.25

            # 3. Lateral Veins: periodic ridges branching off the midrib
            # They start at x=0 and move outwards, fading as they reach edges
            vein_freq = 7
            # Use sine wave along length, multiplied by a decay based on width u
            vein_val = math.sin(v_param * vein_freq * math.pi) * 0.04
            # Veins are more visible further from the absolute center but fade at edges
            dist_from_center = abs(u)
            vein_mask = math.exp(-abs(u)*3.0) - math.exp(-abs(u)*1.5) # creates a slight gap or peak
            # Simpler: just a ridge that fades out
            v.co.z += vein_val * (1.0 - abs(u)) * math.exp(-abs(u)*2.0)

            # 4. Overall gentle bow/curve to make it look organic
            v.co.z -= (v_param**2) * 0.1
            v.co.z += (1-v_param)**2 * 0.05

    bm.to_mesh(mesh)
    bm.free()

    # Add thickness and smoothing
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.003
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

    # Elevated perspective orientation
    leaf_obj.rotation_euler[0] = math.radians(-45)
    leaf_obj.rotation_euler[2] = math.radians(30)

if __name__ == "__main__":
    main()
