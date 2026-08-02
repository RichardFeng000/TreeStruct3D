import bpy
import bmesh
import math

def clear_scene():
    """Clears default Blender scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_spatula_material():
    """Creates a dark blue-gray material."""
    mat = bpy.data.materials.new(name="SpatulaMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Dark blue-gray color (deep slate)
        bsdf.inputs['Base Color'].default_value = (0.12, 0.18, 0.25, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.3
        bsdf.inputs['Metallic'].default_value = 0.1
    return mat

def build_spatula():
    # Dimensions for a broad rectangular spatula
    head_w = 6.0
    head_d = 12.0
    head_t = 0.4
    handle_len = 25.0
    handle_r = 0.5
    transition_h = 3.0

    mesh = bpy.data.meshes.new("SpatulaMesh")
    obj = bpy.data.objects.new("Spatula", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # 1. Create the broad rectangular head (blade)
    # Start with a cube and scale it to be the blade
    bmesh.ops.create_cube(bm, size=1.0)
    # Scale: X=width, Y=depth, Z=thickness
    # Blender default cube is 2x2x2, so we use a transform or set coords manually
    # Let's just define the verts for a box to be precise
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        v.co.x *= head_w / 2
        v.co.y *= head_d / 2
        v.co.z *= head_t / 2

    # Add a slight curve/crown to the top face of the blade
    # Top face is where z > 0
    for v in bm.verts:
        if v.co.z > 0:
            # Parabolic curvature based on x (width) distance from center
            dist_x = abs(v.co.x) / (head_w / 2)
            v.co.z += 0.3 * (1.0 - dist_x**2)

    # 2. Create the handle transition and shaft
    # We find the bottom face (where z < 0)
    bm.faces.ensure_lookup_table()
    bottom_face = None
    for f in bm.faces:
        if all(v.co.z <= 0 for v in f.verts):
            bottom_face = f
            break

    # Extrude bottom face to create transition zone
    res = bmesh.ops.extrude_face_region(bm, geom=[bottom_face])
    transition_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in transition_verts:
        v.co.z -= transition_h

    # Now we need to transition from the broad rectangle to a slender handle circle
    # We'll do this by moving the vertices of the extruded face towards center
    # and then extruding again for the long shaft.
    
    # To make it look better, we can split the bottom face or just morph vertices
    # Let's create a circular cross-section at the end of the transition
    # We map the rectangular verts to a circle
    for v in transition_verts:
        # Calculate angle from center
        angle = math.atan2(v.co.y, v.co.x)
        v.co.x = math.cos(angle) * handle_r
        v.co.y = math.sin(angle) * handle_r

    # Find the new bottom face created by the transition
    bm.faces.ensure_lookup_table()
    current_face = None
    for f in bm.faces:
        if all(v in transition_verts for v in f.verts):
            current_face = f
            break

    # Extrude the circular face to create the long handle shaft
    res_handle = bmesh.ops.extrude_face_region(bm, geom=[current_face])
    shaft_verts = [v for v in res_handle['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in shaft_verts:
        v.co.z -= handle_len

    # Finalize BMesh
    bm.to_mesh(mesh)
    bm.free()

    # Bevel the edges for a "clean squared-off edge" but professional feel
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.15
    bevel.segments = 3
    
    # Subsurf to smooth out the transition and handle
    subsurf = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subsurf.levels = 2

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
    
    # Center object relative to its total size
    total_height = 25.0 + 3.0 + 0.4 # handle + transition + head
    spatula_obj.location.z = total_height / 2

if __name__ == "__main__":
    main()
