import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_lavender_material():
    """Creates a soft, muted lavender fabric material."""
    mat = bpy.data.materials.new(name="LavenderFabric")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Light lavender color
    node_bsdf.inputs['Base Color'].default_value = (0.7, 0.62, 0.85, 1.0)
    node_bsdf.inputs['Roughness'].default_value = 0.9
    if 'Specular' in node_bsdf.inputs:
        node_bsdf.inputs['Specular'].default_value = 0.1
    
    links = mat.node_tree.links
    links.new(node_bsdf.outputs[0], node_output.inputs[0])
    return mat

def create_pillow():
    """Generates a plump, organically wrinkled pillow."""
    # Dimensions
    w_dim = 1.2  # Width
    d_dim = 0.8  # Depth
    h_dim = 0.3  # Height (initial)
    
    # Start with a cube and apply initial scale to be the base volume
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "Pillow"
    obj.scale = (w_dim * 0.5, d_dim * 0.5, h_dim * 0.5)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Use a lower subdivision count to prevent timeouts while maintaining shape
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    for _ in range(4): 
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1)
    
    half_w = w_dim * 0.5
    half_d = d_dim * 0.5
    half_h = h_dim * 0.5

    # Seed for reproducible organic shapes
    random.seed(42)
    wrinkle_layers = []
    for _ in range(4):
        wrinkle_layers.append({
            'freq': random.uniform(1.5, 3.0),
            'amp': random.uniform(0.01, 0.025),
            'angle': random.uniform(0, math.pi * 2),
            'offset': random.uniform(0, math.pi)
        })

    # Iterate through vertices and apply deformations
    for v in bm.verts:
        x, y, z = v.co
        nx = x / half_w
        ny = y / half_d
        nz = z / half_h
        
        dist_sq = nx*nx + ny*ny
        edge_mask = 1.0 - math.exp(-dist_sq * 1.5)

        # Plumpness: bulging elliptical profile
        bulge_factor = math.exp(-dist_sq * 0.7)
        bulge_z = bulge_factor * 0.12
        bulge_xy = bulge_factor * 0.08

        # Natural Creases using sine combinations for pseudo-noise
        total_crease = 0
        for layer in wrinkle_layers:
            rx = x * math.cos(layer['angle']) - y * math.sin(layer['angle'])
            ry = x * math.sin(layer['angle']) + y * math.cos(layer['angle'])
            val = math.sin(rx * layer['freq'] + layer['offset']) 
            total_crease += (abs(val) ** 1.5) * layer['amp']
        
        # Emphasize creases near the edges/seams
        total_crease *= (1.0 + edge_mask * 2.0)

        if z > 0: # Top surface
            v.co.z += bulge_z + total_crease
            v.co.x += nx * bulge_xy
            v.co.y += ny * bulge_xy
        elif z < 0: # Bottom surface
            v.co.z -= (bulge_z * 0.4) - total_crease * 0.6
            v.co.x += nx * bulge_xy * 0.9
            v.co.y += ny * bulge_xy * 0.9
        else: # Sides/Edges
            v.co.x += nx * (bulge_xy * 1.1)
            v.co.y += ny * (bulge_xy * 1.1)

        # Slight irregularity to avoid perfect rectangularity
        if abs(nx) > 0.8 or abs(ny) > 0.8:
            jitter = 0.015 * math.sin(x * 5 + y * 5)
            v.co.x += (nx * jitter)
            v.co.y += (ny * jitter)

    bm.to_mesh(obj.data)
    bm.free()
    
    # Smooth shading and subdivision for high fidelity surface
    for poly in obj.data.polygons:
        poly.use_smooth = True

    subdiv = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 3
    
    # Add material
    mat = create_lavender_material()
    obj.data.materials.append(mat)
    
    return obj

def main():
    clear_scene()
    pillow = create_pillow()
    pillow.location = (0, 0, 0)
    pillow.rotation_euler = (0, 0, 0)

if __name__ == "__main__":
    main()
