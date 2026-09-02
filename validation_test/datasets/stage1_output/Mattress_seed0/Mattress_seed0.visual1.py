import bpy
import bmesh
import math

def clear_scene():
    """Clears all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_mint_material():
    """Creates a light mint-green material."""
    mat = bpy.data.materials.new(name="MintGreen")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    # Light Mint Green: R=0.7, G=1.0, B=0.8
    bsdf.inputs['Base Color'].default_value = (0.75, 1.0, 0.85, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.9
    return mat

def create_mattress():
    # Dimensions
    L = 2.0  # Length (X)
    W = 1.4  # Width (Y)
    H = 0.3  # Height (Z)
    
    # Create a base cube
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, H/2))
    obj = bpy.context.active_object
    obj.scale = (L, W, H)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Use BMesh to add resolution and tufting
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    # We need high density on the top surface for quilting/tufting
    # Subdivide everything a few times first to get base geometry
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=4)
    
    # Find the top face vertices
    top_verts = [v for v in bm.verts if v.co.z > (H/2 - 0.01)]
    
    # Tufting parameters
    tuft_spacing_x = 0.4
    tuft_spacing_y = 0.4
    depth = 0.03
    influence_radius = 0.25
    
    # Generate tuft center points in a grid
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

    # Apply dimples for the quilted look
    for v in top_verts:
        for tx, ty in tufts:
            dist = math.sqrt((v.co.x - tx)**2 + (v.co.y - ty)**2)
            if dist < influence_radius:
                # Smooth bell curve for the dip
                factor = (1.0 - (dist / influence_radius)**2)**2
                v.co.z -= factor * depth

    bm.to_mesh(obj.data)
    bm.free()
    
    # Add Bevel modifier to round edges
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.1
    bevel.segments = 5
    
    # Add Subdivision Surface for the "padded" soft look
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3

    # Set smooth shading
    for poly in obj.data.polygons:
        poly.use_smooth = True

    return obj

def main():
    clear_scene()
    
    # Create mattress
    mattress_obj = create_mattress()
    
    # Apply material
    mat = create_mint_material()
    if not mattress_obj.data.materials:
        mattress_obj.data.materials.append(mat)
    else:
        mattress_obj.data.materials[0] = mat

if __name__ == "__main__":
    main()
