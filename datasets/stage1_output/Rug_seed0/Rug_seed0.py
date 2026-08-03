import bpy
import bmesh
import math

def create_minimalist_rug():
    # Clear existing objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Parameters for the oval rug
    major_axis = 2.0  # Half-length of the long side
    minor_axis = 1.2  # Half-length of the short side
    thickness = 0.04  # Thickness of the rug
    resolution = 128  # Number of vertices for smoothness

    # Create a new mesh and object
    mesh = bpy.data.meshes.new("OvalRug")
    obj = bpy.data.objects.new("OvalRug", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # Generate vertices for the top oval face
    verts_top = []
    for i in range(resolution):
        angle = (2 * math.pi * i) / resolution
        x = major_axis * math.cos(angle)
        y = minor_axis * math.sin(angle)
        # Offset z slightly so the rug is centered vertically around 0
        z = thickness / 2
        verts_top.append(bm.verts.new((x, y, z)))

    # Generate vertices for the bottom oval face
    verts_bottom = []
    for i in range(resolution):
        angle = (2 * math.pi * i) / resolution
        x = major_axis * math.cos(angle)
        y = minor_axis * math.sin(angle)
        z = -thickness / 2
        verts_bottom.append(bm.verts.new((x, y, z)))

    # Create the top face
    bm.faces.new(verts_top)

    # Create the bottom face (reversed order for correct normals)
    bm.faces.new(reversed(verts_bottom))

    # Create side faces to connect top and bottom
    for i in range(resolution):
        v1 = verts_top[i]
        v2 = verts_top[(i + 1) % resolution]
        v3 = verts_bottom[(i + 1) % resolution]
        v4 = verts_bottom[i]
        bm.faces.new((v1, v2, v3, v4))

    # Finalize bmesh and write to mesh
    bm.to_mesh(mesh)
    bm.free()

    # Smooth shading for the minimalist look
    for poly in mesh.polygons:
        poly.use_smooth = True

    # Add a Bevel modifier to soften the edges (crucial for 'clean/minimalist' 3D aesthetic)
    bevel_mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel_mod.width = 0.015
    bevel_mod.segments = 3
    bevel_mod.limit_method = 'ANGLE'
    bevel_mod.angle_limit = math.radians(30)

    # Add a Subdivision Surface modifier for extra smoothness
    subsurf_mod = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subsurf_mod.levels = 1
    subsurf_mod.render_levels = 2

    # Ensure the object is at the origin
    obj.location = (0, 0, 0)

if __name__ == "__main__":
    create_minimalist_rug()
