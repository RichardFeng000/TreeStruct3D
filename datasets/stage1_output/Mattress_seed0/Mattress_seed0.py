import bpy
import bmesh
import math

def clear_scene():
    """Clears all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_mint_material():
    """Creates a distinct light mint-green material."""
    mat = bpy.data.materials.new(name="MintGreen")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    # Light Mint Green: R=0.6, G=0.95, B=0.8 (More saturated than previous version)
    bsdf.inputs['Base Color'].default_value = (0.6, 0.95, 0.8, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.8
    return mat

def create_mattress():
    # Dimensions
    L = 2.0  # Length (X)
    W = 1.4  # Width (Y)
    H = 0.3  # Height (Z)
    
    # Create a base cube and scale it to be the mattress slab
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, H/2))
    obj = bpy.context.active_object
    obj.scale = (L, W, H)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Use BMesh for detailed tufting geometry
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    # Subdivide the edges heavily to get enough resolution for quilting patterns
    # We subdivide multiple times to create a dense grid on all faces
    for _ in range(4):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1)

    # Find the top face vertices (z is approx H/2)
    top_verts = [v for v in bm.verts if v.co.z > (H/2 - 0.01)]
    
    # Tufting parameters: grid of dimples
    tuft_spacing_x = 0.4
    tuft_spacing_y = 0.4
    depth = 0.08  # Increased depth for visibility in render
    influence_radius = 0.25
    
    # Define tuft center points
    tufts = []
    start_x, end_x = -L/2 + 0.2, L/2 - 0.2
    start_y, end_y = -W/2 + 0.2, W/2 - 0.2
    
    curr_x = start_x
    while curr_x <= end_x:
        curr_y = start_y
        while curr_y <= end_y:
            tufts.append((curr_x, curr_y))
            curr_y += tuft_spacing_y
        curr_x += tuft_spacing_x

    # Apply dimples for the quilted look by displacing vertices downwards
    for v in top_verts:
        for tx, ty in tufts:
            dist = math.sqrt((v.co.x - tx)**2 + (v.co.y - ty)**2)
            if dist < influence_radius:
                # Gaussian-like dip for soft quilting
                factor = math.exp(-(dist**2) / (2 * (influence_radius/2)**2))
                v.co.z -= factor * depth

    bm.to_mesh(obj.data)
    bm.free()
    
    # Add Bevel modifier to round the outer edges of the slab
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.12
    bevel.segments = 8
    
    # Add Subdivision Surface for a padded, organic feel
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3

    # Smooth shading across the whole object
    for poly in obj.data.polygons:
        poly.use_smooth = True

    return obj

def main():
    clear_scene()
    
    # Create mattress geometry
    mattress_obj = create_mattress()
    
    # Apply mint-green material
    mat = create_mint_material()
    if not mattress_obj.data.materials:
        mattress_obj.data.materials.append(mat)
    else:
        mattress_obj.data.materials[0] = mat

if __name__ == "__main__":
    main()
