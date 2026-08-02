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
    
    # Light lavender color - slightly adjusted for better visibility in various renderers
    node_bsdf.inputs['Base Color'].default_value = (0.65, 0.58, 0.82, 1.0)
    node_bsdf.inputs['Roughness'].default_value = 0.9
    if 'Specular' in node_bsdf.inputs:
        node_bsdf.inputs['Specular'].default_value = 0.05
    
    links = mat.node_tree.links
    links.new(node_bsdf.outputs[0], node_output.inputs[0])
    return mat

def create_pillow():
    """Generates a plump, organically wrinkled pillow."""
    # Dimensions
    w_dim = 1.0  # Width
    d_dim = 0.7  # Depth
    h_dim = 0.2  # Height (initial)
    
    # Start with a cube and apply initial scale to be the base volume
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "Pillow"
    obj.scale = (w_dim * 0.5, d_dim * 0.5, h_dim * 0.5)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # High resolution for organic displacement
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    for _ in range(6): 
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1)
    
    half_w = w_dim * 0.5
    half_d = d_dim * 0.5
    half_h = h_dim * 0.5

    # Seeds for pseudo-random wrinkles to avoid grid patterns
    random.seed(42)
    wrinkle_layers = []
    for _ in range(6):
        wrinkle_layers.append({
            'freq': random.uniform(1.5, 4.0),
            'amp': random.uniform(0.01, 0.03),
            'angle': random.uniform(0, math.pi * 2),
            'offset': random.uniform(0, math.pi)
        })

    for v in bm.verts:
        x, y, z = v.co
        nx = x / half_w
        ny = y / half_d
        nz = z / half_h
        
        dist_sq = nx*nx + ny*ny
        # Mask that preserves the center and emphasizes edges/corners for wrinkles
        edge_mask = 1.0 - math.exp(-dist_sq * 2.0)

        # --- Plumpness (Overall shape) ---
        # Use a more rounded, bulging elliptical profile
        bulge_factor = math.exp(-dist_sq * 0.6)
        bulge_z = bulge_factor * 0.15
        bulge_xy = bulge_factor * 0.12

        # --- Natural Creases (Layered pseudo-random noise) ---
        total_crease = 0
        for layer in wrinkle_layers:
            # Rotate coordinate for this specific ripple layer
            rx = x * math.cos(layer['angle']) - y * math.sin(layer['angle'])
            ry = x * math.sin(layer['angle']) + y * math.cos(layer['angle'])
            # Use sin and abs-sin to create both valleys and ridges
            val = math.sin(rx * layer['freq'] + layer['offset']) 
            total_crease += (abs(val) ** 2) * layer['amp']
        
        # Apply creases more strongly towards the edges than the center
        total_crease *= (1.0 + edge_mask * 3.0)

        if z > 0: # Top surface
            v.co.z += bulge_z + total_crease
            v.co.x += nx * bulge_xy
            v.co.y += ny * bulge_xy
        elif z < 0: # Bottom surface
            v.co.z -= (bulge_z * 0.3) - total_crease * 0.5
            v.co.x += nx * bulge_xy * 0.8
            v.co.y += ny * bulge_xy * 0.8
        else: # Sides
            v.co.x += nx * (bulge_xy * 1.2)
            v.co.y += ny * (bulge_xy * 1.2)

        # Organic edge irregularity - perturb vertices near the boundary
        if abs(nx) > 0.85 or abs(ny) > 0.85:
            jitter = 0.02 * math.sin(x * 6 + y * 6)
            v.co.x += (nx * jitter)
            v.co.y += (ny * jitter)

    bm.to_mesh(obj.data)
    bm.free()
    
    # Smooth shading and subdivision for a "soft" look
    for poly in obj.data.polygons:
        poly.use_smooth = True

    subdiv = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 3
    
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
