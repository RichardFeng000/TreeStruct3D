import bpy
import bmesh
import math

def setup_scene():
    """Clears the default scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_raindrop_material():
    """Creates a translucent blue-gray glassy material."""
    mat = bpy.data.materials.new(name="RaindropGlass")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()

    # Create Principled BSDF node
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    
    # Light blue-gray color - slightly more saturation to ensure it's visible as "blue-gray"
    node_principled.inputs['Base Color'].default_value = (0.5, 0.7, 0.8, 1.0)
    
    # Glassy properties
    node_principled.inputs['Roughness'].default_value = 0.01
    node_principled.inputs['Transmission Weight'].default_value = 1.0  # Blender 4.0+ Transmission property
    node_principled.inputs['IOR'].default_value = 1.33  # Index of refraction for water
    
    # Output node
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    links = mat.node_tree.links
    links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    
    return mat

def create_raindrop():
    """Constructs a smooth hemispherical dome on a perfectly flat circular base."""
    # Create UV Sphere with high resolution for smoothness
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0), segments=64, ring_count=32)
    obj = bpy.context.active_object
    obj.name = "Raindrop"

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    # Step 1: Flatten the bottom half of the sphere to Z=0
    for v in bm.verts:
        if v.co.z < 0:
            v.co.z = 0.0

    # Step 2: Merge vertices that are now overlapping at Z=0 (the equator and poles)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)

    # Step 3: Remove all degenerate faces created by flattening the bottom half
    # A face is degenerate here if all its vertices lie on Z=0
    faces_to_delete = [f for f in bm.faces if all(abs(v.co.z) < 0.001 for v in f.verts)]
    bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')

    # Step 4: Fill the base hole with a clean triangle fan to avoid N-gon artifacts
    # Identify vertices on the Z=0 plane
    bottom_verts = [v for v in bm.verts if abs(v.co.z) < 0.001]
    
    if bottom_verts:
        # Create a center vertex at origin to act as the hub for the fan
        center_vert = bm.verts.new((0, 0, 0))
        
        # Sort vertices by angle around Z-axis to create a proper loop
        sorted_verts = sorted(bottom_verts, key=lambda v: math.atan2(v.co.y, v.co.x))
        
        for i in range(len(sorted_verts)):
            v1 = sorted_verts[i]
            v2 = sorted_verts[(i + 1) % len(sorted_verts)]
            # Create a triangle between the center and two adjacent loop vertices
            try:
                bm.faces.new((center_vert, v1, v2))
            except ValueError:
                # Face might already exist if duplication occurred
                pass

    bm.to_mesh(obj.data)
    bm.free()

    # Apply smooth shading to ensure the dome and base transition seamlessly
    bpy.ops.object.shade_smooth()

    # Add Subdivision Surface for high fidelity specular highlights
    subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 3

    return obj

def main():
    setup_scene()
    
    # Material setup
    glass_mat = create_raindrop_material()
    
    # Geometry setup
    raindrop = create_raindrop()
    
    # Assign material
    if raindrop.data.materials:
        raindrop.data.materials[0] = glass_mat
    else:
        raindrop.data.materials.append(glass_mat)

    # Position exactly at origin, base sitting on Z=0 plane
    raindrop.location = (0, 0, 0)

if __name__ == "__main__":
    main()
