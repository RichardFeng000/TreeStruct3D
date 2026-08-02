import bpy
import bmesh

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    # Clean up orphan data
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, color):
    """Creates a simple Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Roughness'].default_value = 0.2
    
    links = mat.node_tree.links
    links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_countertop():
    """Constructs the countertop assembly ensuring segments intersect and connect."""
    thickness = 0.04
    width = 0.65  # Standard depth
    
    # Define slabs: (x, y, dx, dy) - center coordinates and dimensions
    # We ensure these overlap to form a connected L/Cross structure.
    segments = [
        (0, 0, 3.0, width),            # Main horizontal axis
        (0, 0, width, 2.5),            # Vertical axis crossing at center (forming cross)
        (-1.0, -width/2, width, 1.2),  # L-extension extending downwards from left side
        (1.5, 0, 1.0, width * 1.5),    # Irregular protrusion on the right
    ]
    
    bm = bmesh.new()
    
    for cx, cy, sx, sy in segments:
        half_sx = sx / 2
        half_sy = sy / 2
        half_tz = thickness / 2
        
        # Box vertices
        verts = [
            (cx - half_sx, cy - half_sy, -half_tz), (cx + half_sx, cy - half_sy, -half_tz),
            (cx + half_sx, cy + half_sy, -half_tz), (cx - half_sx, cy + half_sy, -half_tz),
            (cx - half_sx, cy - half_sy,  half_tz), (cx + half_sx, cy - half_sy,  half_tz),
            (cx + half_sx, cy + half_sy,  half_tz), (cx - half_sx, cy + half_sy,  half_tz)
        ]
        
        bm_verts = [bm.verts.new(v) for v in verts]
        
        # Define faces
        faces = [
            [0, 1, 2, 3], # Bottom
            [4, 7, 6, 5], # Top
            [0, 1, 5, 4], # Front
            [1, 2, 6, 5], # Right
            [2, 3, 7, 6], # Back
            [3, 0, 4, 7]  # Left
        ]
        for f in faces:
            bm.faces.new([bm_verts[i] for i in f])

    # Remove doubles to merge vertices where segments overlap perfectly
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    
    mesh = bpy.data.meshes.new("CountertopMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("KitchenCountertop", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Set sharp edges for a clean architectural look
    obj.data.polygons.foreach_set("use_smooth", [False] * len(obj.data.polygons))
    
    return obj

def main():
    clear_scene()
    
    # Pale gray/off-white stone color
    pale_gray = (0.9, 0.9, 0.88, 1.0)
    mat = create_material("CountertopMaterial", pale_gray)
    
    countertop = create_countertop()
    
    if not countertop.data.materials:
        countertop.data.materials.append(mat)
    else:
        countertop.data.materials[0] = mat

if __name__ == "__main__":
    main()
