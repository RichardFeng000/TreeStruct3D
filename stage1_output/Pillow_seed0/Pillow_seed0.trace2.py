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
    """Creates a soft fabric-like lavender material."""
    mat = bpy.data.materials.new(name="LavenderFabric")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Lavender: soft purple/blue hue
    node_bsdf.inputs['Base Color'].default_value = (0.82, 0.76, 0.91, 1.0)
    node_bsdf.inputs['Roughness'].default_value = 0.9
    if 'Specular' in node_bsdf.inputs:
        node_bsdf.inputs['Specular'].default_value = 0.2
    
    links = mat.node_tree.links
    links.new(node_bsdf.outputs[0], node_output.inputs[0])
    return mat

def create_pillow():
    """Generates a plump, wrinkled pillow using procedural geometry."""
    # Dimensions
    width = 0.7
    depth = 0.5
    height = 0.12
    
    # Start with a basic cube and subdivide it to get high resolution for deformation
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "Pillow"
    
    # Scale the cube to pillow dimensions
    obj.scale = (width * 0.5, depth * 0.5, height * 0.5)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Enter edit mode and subdivide heavily for organic shapes
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    # Subdivide the cube faces to create a dense grid
    # Using a simple loop of subdivision since we need enough vertices for wrinkles
    for _ in range(4): 
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1)
    
    # Apply procedural deformation on vertices
    # We calculate normalized coordinates to drive the "plumpness" and "wrinkles"
    for v in bm.verts:
        x, y, z = v.co
        nx = x / (width * 0.5)
        ny = y / (depth * 0.5)
        nz = z / (height * 0.5)
        
        # Distance from center for the Gaussian bulge effect
        dist_sq = nx*nx + ny*ny
        
        # Plumpness: Center swell
        bulge = math.exp(-dist_sq * 1.2) * (height * 0.4)
        
        # Wrinkles: Sum of sine waves to simulate fabric folds
        wrinkle = 0
        octaves = [
            (5.0, 0.015),  # frequency, amplitude
            (10.0, 0.008),
            (20.0, 0.004)
        ]
        for freq, amp in octaves:
            wrinkle += math.sin(x * freq + y * freq * 0.6) * amp
            wrinkle += math.cos(y * freq - x * freq * 0.3) * amp

        # Apply deformation based on Z position (top vs bottom)
        if z > 0:
            # Top surface pushes up and slightly out
            v.co.z += bulge + wrinkle
            v.co.x += nx * bulge * 0.4
            v.co.y += ny * bulge * 0.4
        elif z < 0:
            # Bottom surface is flatter, slight dip in middle
            v.co.z -= (bulge * 0.2) + abs(wrinkle) * 0.3
        else:
            # Middle section expands slightly outward for plumpness
            v.co.x += nx * bulge * 0.6
            v.co.y += ny * bulge * 0.6

        # Irregularity on edges (jitter boundary vertices)
        if abs(nx) > 0.9 or abs(ny) > 0.9:
            jitter = 0.012
            v.co.x += (random.random() - 0.5) * jitter
            v.co.y += (random.random() - 0.5) * jitter
            v.co.z += (random.random() - 0.5) * jitter

    # Update mesh and return to object mode
    bm.to_mesh(obj.data)
    bm.free()
    
    # Smooth shading
    for poly in obj.data.polygons:
        poly.use_smooth = True

    # Modifiers for organic fidelity
    subdiv = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 3
    
    # To ensure the pillow looks soft, add a slight bevel to edges via subdivision
    # but since we already subdivided and moved verts, Subsurf handles this well.

    # Material assignment
    mat = create_lavender_material()
    obj.data.materials.append(mat)
    
    return obj

def main():
    clear_scene()
    pillow = create_pillow()
    
    # Center the pillow at origin
    pillow.location = (0, 0, 0)
    pillow.rotation_euler = (0, 0, 0)

if __name__ == "__main__":
    main()
