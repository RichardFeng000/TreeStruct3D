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
    
    # Muted lavender to avoid overexposure: slightly deeper purple-grey hue
    node_bsdf.inputs['Base Color'].default_value = (0.72, 0.65, 0.85, 1.0)
    node_bsdf.inputs['Roughness'].default_value = 0.95
    if 'Specular' in node_bsdf.inputs:
        node_bsdf.inputs['Specular'].default_value = 0.1
    
    links = mat.node_tree.links
    links.new(node_bsdf.outputs[0], node_output.inputs[0])
    return mat

def create_pillow():
    """Generates a plump, wrinkled pillow with realistic fabric creases."""
    # Dimensions
    w_dim = 0.8
    d_dim = 0.6
    h_dim = 0.15
    
    # Start with a cube and apply initial scale
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "Pillow"
    obj.scale = (w_dim * 0.5, d_dim * 0.5, h_dim * 0.5)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Increase vertex density for organic deformation
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    for _ in range(5): 
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1)
    
    # Pre-calculate constants for normalized coordinates
    half_w = w_dim * 0.5
    half_d = d_dim * 0.5
    half_h = h_dim * 0.5

    for v in bm.verts:
        x, y, z = v.co
        nx = x / half_w
        ny = y / half_d
        nz = z / half_h
        
        # Distance from center for bulge and wrinkle masking
        dist_sq = nx*nx + ny*ny
        mask = 1.0 - math.exp(-dist_sq * 0.5) # Stronger at edges

        # --- Plumpness (Overall shape) ---
        bulge = math.exp(-dist_sq * 0.8) * (h_dim * 0.35)
        
        # --- Natural Creases (Low-frequency folds) ---
        # We use absolute sine waves to create "valleys" and "ridges" rather than ripples
        fold = 0
        folds_config = [
            (2.5, 0.015, 0.4), # freq, amp, angle offset
            (3.1, 0.012, -0.7),
            (1.8, 0.010, 0.1)
        ]
        for f, a, rot in folds_config:
            # Rotate coordinate system for each fold to avoid grid alignment
            rx = x * math.cos(rot) - y * math.sin(rot)
            ry = x * math.sin(rot) + y * math.cos(rot)
            fold += abs(math.sin(rx * f))**2 * a
        
        # Combine fold with mask so creases are more prominent near edges/corners
        total_crease = fold * (1.0 + mask * 2.0)

        # Apply displacement based on Z surface
        if z > 0: # Top surface
            v.co.z += bulge + total_crease
            # Expand sides for plumpness
            v.co.x += nx * bulge * 0.5
            v.co.y += ny * bulge * 0.5
        elif z < 0: # Bottom surface
            # Slight flatten/dip in middle
            v.co.z -= (bulge * 0.1) + total_crease * 0.3
        else: # Middle ring
            v.co.x += nx * bulge * 0.7
            v.co.y += ny * bulge * 0.7

        # Organic edge irregularity (Low-frequency noise instead of high-freq jitter)
        if abs(nx) > 0.95 or abs(ny) > 0.95:
            edge_noise = 0.015 * math.sin(x * 4 + y * 4)
            v.co.x += (nx * edge_noise)
            v.co.y += (ny * edge_noise)

    bm.to_mesh(obj.data)
    bm.free()
    
    # Shading and refinement
    for poly in obj.data.polygons:
        poly.use_smooth = True

    subdiv = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 3
    
    # Material assignment
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
