import bpy
import bmesh

def clear_scene():
    """Removes all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_cabinet_door():
    """Creates a tall, narrow IKEA-style cabinet door panel."""
    # Dimensions in meters
    height = 2.1  # Typical tall cabinet height
    width = 0.4   # Narrow width
    thickness = 0.018 # Standard 18mm furniture board thickness

    # Create a mesh and object
    mesh = bpy.data.meshes.new("CabinetDoorMesh")
    obj = bpy.data.objects.new("CabinetDoor", mesh)
    bpy.context.collection.objects.link(obj)

    # Use BMesh to construct the geometry for precision
    bm = bmesh.new()
    
    # Create a cube scaled to door dimensions
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale the vertices to match target dimensions
    # Center is already 0,0,0
    for v in bm.verts:
        v.co.x *= (width / 2.0)
        v.co.y *= (thickness / 2.0)
        v.co.z *= (height / 2.0)

    # Finalize BMesh and write to mesh
    bm.to_mesh(mesh)
    bm.free()

    # Ensure edges are sharp by setting the shading to flat (default)
    # and making sure there's no smoothing group applied.
    obj.data.polygons.foreach_set("use_smooth", [False] * len(obj.data.polygons))

    return obj

def apply_material(obj):
    """Applies a pale cream-beige material to the object."""
    mat = bpy.data.materials.new(name="CreamBeigeGloss")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    
    # Clear default nodes
    nodes.clear()
    
    # Create Principled BSDF
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    
    # Pale cream-beige color (R, G, B, A)
    # Creamy beige: roughly hex #F5F5DC or similar light warm grey/yellow
    bsdf.inputs['Base Color'].default_value = (0.96, 0.94, 0.88, 1.0)
    
    # Glossy finish: Low roughness, high specular
    bsdf.inputs['Roughness'].default_value = 0.1
    
    # Output node
    output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Link them
    links = mat.node_tree.links
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

def main():
    # 1. Setup environment
    clear_scene()
    
    # 2. Create the geometry
    door = create_cabinet_door()
    
    # 3. Apply the visual properties described (Cream-beige glossy finish)
    apply_material(door)

if __name__ == "__main__":
    main()
