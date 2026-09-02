import bpy
import bmesh
import math

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Creates a Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def build_arched_door():
    # Dimensions
    width = 0.9
    height_rect = 1.65
    arch_radius = width / 2
    thickness = 0.05
    panel_margin = 0.1
    handle_width = 0.3
    handle_radius = 0.015

    # Materials
    wood_mat = create_material("EspressoWood", (0.06, 0.04, 0.02, 1.0), metallic=0.0, roughness=0.7)
    metal_mat = create_material("MetallicBar", (0.7, 0.7, 0.7, 1.0), metallic=1.0, roughness=0.2)

    # --- Build Door Slab ---
    bm = bmesh.new()
    w2, t2, hr = width/2, thickness/2, height_rect

    # Rectangular base vertices
    v0 = bm.verts.new((-w2, -t2, 0)) # BL front
    v1 = bm.verts.new((w2, -t2, 0))  # BR front
    v2 = bm.verts.new((w2, t2, 0))   # BR back
    v3 = bm.verts.new((-w2, t2, 0))  # BL back
    v4 = bm.verts.new((-w2, -t2, hr)) # TL front
    v5 = bm.verts.new((w2, -t2, hr))  # TR front
    v6 = bm.verts.new((w2, t2, hr))   # TR back
    v7 = bm.verts.new((-w2, t2, hr))  # TL back

    # Base faces
    bm.faces.new((v0, v1, v5, v4)) # Front face (bottom part)
    bm.faces.new((v2, v3, v7, v6)) # Back face (bottom part)
    bm.faces.new((v0, v4, v7, v3)) # Left side
    bm.faces.new((v1, v5, v6, v2)) # Right side
    bm.faces.new((v0, v1, v2, v3)) # Bottom

    # Arch Cap Construction
    res = 32
    arc_f = []
    arc_b = []
    for i in range(res + 1):
        theta = math.pi * (i / res)
        x = math.cos(theta) * arch_radius
        z = hr + math.sin(theta) * arch_radius
        arc_f.append(bm.verts.new((x, -t2, z)))
        arc_b.append(bm.verts.new((x, t2, z)))

    # Fill the rim of the arch (connecting front and back arcs)
    for i in range(res):
        bm.faces.new((arc_f[i], arc_f[i+1], arc_b[i+1], arc_b[i]))

    # Fill the semi-circle caps using fans
    cf = bm.verts.new((0, -t2, hr)) # front center of arch
    cb = bm.verts.new((0, t2, hr))  # back center of arch
    for i in range(res):
        bm.faces.new((cf, arc_f[i+1], arc_f[i]))
        bm.faces.new((cb, arc_b[i], arc_b[i+1]))

    # Convert BMesh to Object
    mesh = bpy.data.meshes.new("DoorMesh")
    bm.to_mesh(mesh)
    bm.free()
    slab = bpy.data.objects.new("DoorSlab", mesh)
    bpy.context.collection.objects.link(slab)
    slab.data.materials.append(wood_mat)

    # --- Build 6 Panels (2x3 grid) ---
    p_w = (width - 3 * panel_margin) / 2
    p_h = (height_rect - 4 * panel_margin) / 3
    
    col_x = [-width/2 + panel_margin + p_w/2, width/2 - panel_margin - p_w/2]
    row_z = [panel_margin + p_h/2, height_rect/2, height_rect - (panel_margin + p_h/2)]

    for cx in col_x:
        for cz in row_z:
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            panel = bpy.context.active_object
            # Make panel slightly protrude from the front face (-t2)
            p_thick = 0.02 
            panel.scale = (p_w, p_thick, p_h)
            panel.location = (cx, -t2 - p_thick/2, cz)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            panel.data.materials.append(wood_mat)
            # Small bevel for traditional look
            mod = panel.modifiers.new(name="Bevel", type='BEVEL')
            mod.width = 0.01
            mod.segments = 2

    # --- Build Handle ---
    # Horizontal bar across the middle, slightly offset from center to one side
    bpy.ops.mesh.primitive_cylinder_add(radius=handle_radius, depth=handle_width)
    handle = bpy.context.active_object
    handle.rotation_euler = (0, math.radians(90), 0) # Rotate so Z-axis is World X
    # Position: offset from center slightly to the right side of door, and centered vertically
    handle.location = (width/4, -t2 - handle_radius, height_rect * 0.5)
    handle.data.materials.append(metal_mat)

if __name__ == "__main__":
    clear_scene()
    build_arched_door()
