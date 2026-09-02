import bpy
import bmesh
import math

def clear_scene():
    """Clears the default scene objects."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Creates a basic Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_square_tin():
    # Parameters
    width = 2.0
    depth = 2.0
    height = 2.5
    corner_radius = 0.2
    rim_thickness = 0.1
    recess_depth = 0.15

    # --- Body Creation ---
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale to target dimensions
    for v in bm.verts:
        v.co.x *= width
        v.co.y *= depth
        v.co.z *= height

    # Bevel vertical edges
    vertical_edges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.9 * height]
    bmesh.ops.bevel(bm, geom=vertical_edges, offset=corner_radius, segments=8, affect='EDGES')

    # Identify the top face for recessing
    top_face = None
    max_z = -float('inf')
    for f in bm.faces:
        center_z = sum(v.co.z for v in f.verts) / len(f.verts)
        if center_z > max_z:
            max_z = center_z
            top_face = f

    # Use inset_region to create the rim
    # Inset creates a new inner face
    res = bmesh.ops.inset_region(bm, faces=[top_face], thickness=rim_thickness, use_boundary=True)
    inner_face = res['faces'][0]

    # Extrude inner face downwards to create the socket
    bmesh.ops.translate(bm, verts=inner_face.verts, vec=(0, 0, -recess_depth))

    # Finalize Body Mesh
    body_mesh = bpy.data.meshes.new("TinBody")
    bm.to_mesh(body_mesh)
    body_obj = bpy.data.objects.new("TinBody", body_mesh)
    bpy.context.collection.objects.link(body_obj)
    bm.free()

    # --- Lid Creation ---
    lid_bm = bmesh.new()
    bmesh.ops.create_cube(lid_bm, size=1.0)
    
    # The lid should fit into the recess (width - 2*rim_thickness)
    l_width = width - (rim_thickness * 2)
    l_depth = depth - (rim_thickness * 2)
    l_height = recess_depth * 0.9 # Slightly thinner to avoid Z-fighting

    for v in lid_bm.verts:
        v.co.x *= l_width
        v.co.y *= l_depth
        v.co.z *= l_height

    # Bevel vertical edges of the lid to match body curvature (roughly)
    l_vertical_edges = [e for e in lid_bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.5]
    bmesh.ops.bevel(lid_bm, geom=l_vertical_edges, offset=(corner_radius * 0.7), segments=8, affect='EDGES')

    lid_mesh = bpy.data.meshes.new("TinLid")
    lid_bm.to_mesh(lid_mesh)
    lid_obj = bpy.data.objects.new("TinLid", lid_mesh)
    bpy.context.collection.objects.link(lid_obj)
    lid_bm.free()

    # Position the lid in the recess
    # Body top is at height/2. Recess bottom is at (height/2 - recess_depth).
    # Lid center should be between those two points.
    lid_obj.location.z = (height / 2) - (recess_depth / 2)

    return body_obj, lid_obj

def main():
    clear_scene()

    # Materials
    # Warm brown metallic exterior
    brown_metallic = create_material(
        "BrownMetallic", 
        (0.35, 0.18, 0.1, 1.0), 
        metallic=1.0, 
        roughness=0.3
    )
    
    # Dark metallic for the lid
    dark_metal = create_material(
        "DarkMetal", 
        (0.05, 0.05, 0.07, 1.0), 
        metallic=0.8, 
        roughness=0.4
    )

    # Geometry generation
    body, lid = create_square_tin()

    # Assign Materials
    body.data.materials.append(brown_metallic)
    lid.data.materials.append(dark_metal)

if __name__ == "__main__":
    main()
