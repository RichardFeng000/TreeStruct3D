import bpy
import bmesh
import math

def clear_scene():
    """Clears default Blender scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_spatula_material():
    """Creates a dark blue-gray material that is visible in renders."""
    mat = bpy.data.materials.new(name="SpatulaMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Dark blue-gray (deep slate), slightly lifted for visibility
        bsdf.inputs['Base Color'].default_value = (0.2, 0.28, 0.35, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.4
        bsdf.inputs['Metallic'].default_value = 0.2
    return mat

def build_spatula():
    # Dimensions to emphasize a "broad rectangular head" and a balanced handle
    head_w = 6.0      # Width (X)
    head_l = 10.0     # Length of blade (Y)
    head_t = 0.3      # Thickness (Z)
    handle_len = 14.0 # Shorter than before to make the head look broad
    handle_r = 0.6    # Radius of handle shaft
    transition_h = 2.5 # Height of the transition area

    mesh = bpy.data.meshes.new("SpatulaMesh")
    obj = bpy.data.objects.new("Spatula", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # 1. Create the broad rectangular blade
    # Verts for a box: +/- head_w/2, +/- head_l/2, +/- head_t/2
    verts = []
    for x in [-head_w/2, head_w/2]:
        for y in [-head_l/2, head_l/2]:
            for z in [-head_t/2, head_t/2]:
                verts.append(bm.verts.new((x, y, z)))

    # Define faces for the blade cube
    # Indices: 0:(-,-), 1:(-,+), 2:(+,-), 3:(+,+) ... for Z=-T/2 then Z=T/2
    # Let's simplify face creation by using a standard layout
    # Verts are created in order: X-,Y-,Z- | X-,Y+,Z- | X+,Y-,Z- | X+,Y+,Z- | X-,Y-,Z+ | ...
    bm.faces.new([verts[0], verts[1], verts[3], verts[2]]) # Bottom face (z < 0)
    bm.faces.new([verts[4], verts[6], verts[7], verts[5]]) # Top face (z > 0)
    bm.faces.new([verts[0], verts[4], verts[5], verts[1]]) # Side 1
    bm.faces.new([verts[1], verts[5], verts[7], verts[3]]) # Side 2
    bm.faces.new([verts[3], verts[7], verts[6], verts[2]]) # Side 3
    bm.faces.new([verts[2], verts[6], verts[4], verts[0]]) # Side 4

    # Slightly curve the top working surface (parabolic crown)
    for v in bm.verts:
        if v.co.z > 0:
            dist_x = abs(v.co.x) / (head_w / 2)
            v.co.z += 0.4 * (1.0 - dist_x**2)

    # 2. Create the handle transition
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    # Identify bottom face to extrude the handle from it
    bottom_face = None
    for f in bm.faces:
        if all(v.co.z < 0 for v in f.verts):
            bottom_face = f
            break

    # Extrude down
    res = bmesh.ops.extrude_face_region(bm, geom=[bottom_face])
    transition_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in transition_verts:
        v.co.z -= transition_h

    # Morph the rectangle to a circular handle profile
    # We use a simple mapping from rectangular coordinates to circle
    for v in transition_verts:
        angle = math.atan2(v.co.y, v.co.x)
        v.co.x = math.cos(angle) * handle_r
        v.co.y = math.sin(angle) * handle_r

    # Find the face that is now circular (the extruded bottom face)
    bm.faces.ensure_lookup_table()
    handle_base_face = None
    for f in bm.faces:
        if all(v in transition_verts for v in f.verts):
            handle_base_face = f
            break

    # Extrude the handle shaft
    res_handle = bmesh.ops.extrude_face_region(bm, geom=[handle_base_face])
    shaft_verts = [v for v in res_handle['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in shaft_verts:
        v.co.z -= handle_len

    # Finalize BMesh
    bm.to_mesh(mesh)
    bm.free()

    # Bevel for "clean squared-off edge" - minimal width to avoid rounding into a pill
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.1
    bevel.segments = 2
    
    # Avoid Subsurf as it ruins the rectangular silhouette requested

    # Shading
    for poly in mesh.polygons:
        poly.use_smooth = True

    # Material
    mat = create_spatula_material()
    obj.data.materials.append(mat)

    return obj

def main():
    clear_scene()
    spatula_obj = build_spatula()
    
    # Center the object globally
    total_h = 14.0 + 2.5 + 0.3
    spatula_obj.location.z = total_h / 2

if __name__ == "__main__":
    main()
