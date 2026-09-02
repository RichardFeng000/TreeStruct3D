import bpy
import bmesh
import math

def clear_scene():
    """Clears the default scene of all objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_mint_green_material():
    """Creates a mint-green material and returns it."""
    mat = bpy.data.materials.new(name="MintGreen")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Create a principled BSDF node
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    # Mint Green color: R=0.6, G=0.9, B=0.7 (approximate)
    bsdf.inputs['Base Color'].default_value = (0.62, 0.91, 0.78, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.3
    
    # Create output node
    output = nodes.new(type='ShaderNodeOutputMaterial')
    
    links = mat.node_tree.links
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    return mat

def create_storage_basket():
    """Procedurally generates a storage basket with sloped sides and handles."""
    # Dimensions
    base_w = 1.2
    base_l = 2.0
    top_w = 1.4
    top_l = 2.2
    height = 1.0
    thickness = 0.06
    
    # Create BMesh
    bm = bmesh.new()
    
    # 1. Create the bottom face
    # Bottom vertices
    v1 = bm.verts.new((-base_l/2, -base_w/2, 0))
    v2 = bm.verts.new((base_l/2, -base_w/2, 0))
    v3 = bm.verts.new((base_l/2, base_w/2, 0))
    v4 = bm.verts.new((-base_l/2, base_w/2, 0))
    bm.faces.new((v1, v2, v3, v4))
    
    # 2. Create the top rim vertices (sloped)
    v5 = bm.verts.new((-top_l/2, -top_w/2, height))
    v6 = bm.verts.new((top_l/2, -top_w/2, height))
    v7 = bm.verts.new((top_l/2, top_w/2, height))
    v8 = bm.verts.new((-top_l/2, top_w/2, height))
    
    # 3. Create the walls (connecting bottom to top)
    bm.faces.new((v1, v2, v6, v5)) # Front
    bm.faces.new((v2, v3, v7, v6)) # Right
    bm.faces.new((v3, v4, v8, v7)) # Back
    bm.faces.new((v4, v1, v5, v8)) # Left

    # Finalize bmesh to object
    mesh = bpy.data.meshes.new("BasketMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("StorageBasket", mesh)
    bpy.context.collection.objects.link(obj)
    
    # --- Modifiers for thickness and smoothing ---
    
    # Solidify to add wall thickness (open top is preserved because we didn't create a top face)
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = thickness
    solid.offset = 1 # Push thickness outwards
    
    # Bevel to smooth the edges
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.02
    bevel.segments = 3
    
    # --- Handle Cutouts ---
    # We will use Boolean cubes to carve out handles on the long sides (Front and Back)
    handle_w = 0.4
    handle_h = 0.15
    handle_depth = thickness * 3 # Ensure it cuts through completely
    
    for side in [-1, 1]: # -1 for front-ish, 1 for back-ish
        # Create a cube for the cutout
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        handle_cut = bpy.context.active_object
        handle_cut.name = f"HandleCutter_{side}"
        
        # Scale and position handle cutter
        # Position based on the sloped wall: Z is height/2, Y is +/- (base_w + top_w)/4
        y_pos = side * ((base_w + top_w) / 4)
        handle_cut.scale = (handle_w, handle_depth, handle_h)
        handle_cut.location = (0, y_pos, height * 0.7)
        
        # Boolean modifier on the basket
        bool_mod = obj.modifiers.new(name=f"HandleCut_{side}", type='BOOLEAN')
        bool_mod.operation = 'DIFFERENCE'
        bool_mod.object = handle_cut
        
        # Hide cutter from render and viewport for cleanliness
        handle_cut.hide_viewport = True
        handle_cut.hide_render = True

    # Set smooth shading
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()
    
    # Apply material
    mat = create_mint_green_material()
    obj.data.materials.append(mat)
    
    return obj

def main():
    clear_scene()
    create_storage_basket()
    
    # Setup the scene for a "three-quarter perspective" look 
    # (Though we only provide geometry, centering it is key).
    # The user requested "rendered from... perspective", but the prompt requires 
    # ONLY the object. We do not add cameras or lights as per constraints.

if __name__ == "__main__":
    main()
