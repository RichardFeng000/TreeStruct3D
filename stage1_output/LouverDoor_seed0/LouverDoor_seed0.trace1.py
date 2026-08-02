import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    if "Cube" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
    if "Camera" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Camera"], do_unlink=True)
    if "Light" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Light"], do_unlink=True)
    # Clear everything else just in case
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.8):
    """Creates a simple Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_box(name, size, location, rotation=(0, 0, 0), material=None):
    """Helper to create a box mesh."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    return obj

def build_door():
    clear_scene()

    # --- Parameters ---
    W = 0.9           # Overall Width
    H_straight = 1.6  # Height of the straight part
    T = 0.04          # Door thickness (depth)
    FW = 0.07         # Frame width (the bezel/border)
    R = W / 2         # Radius for arch
    Slat_Spacing = 0.03
    Slat_Thickness = 0.01
    Slat_Depth = W - (FW * 2) # Internal width available for slats
    Slat_Angle = math.radians(45)

    # Colors
    charcoal_col = (0.05, 0.05, 0.06, 1.0)
    copper_col = (0.75, 0.45, 0.3, 1.0)

    mat_frame = create_material("Charcoal", charcoal_col, metallic=0.1, roughness=0.8)
    mat_slats = create_material("CopperRoseGold", copper_col, metallic=1.0, roughness=0.3)

    # --- Frame Construction ---
    # 1. Bottom Rail
    create_box("Frame_Bottom", (W, T, FW), (0, 0, FW/2), material=mat_frame)

    # 2. Mid Rail (separating the two inset sections)
    mid_z = H_straight * 0.4
    create_box("Frame_Mid", (W, T, FW), (0, 0, mid_z), material=mat_frame)

    # 3. Side Rails (vertical posts)
    side_h = H_straight
    create_box("Frame_Left", (FW, T, side_h), (-W/2 + FW/2, 0, side_h/2), material=mat_frame)
    create_box("Frame_Right", (FW, T, side_h), (W/2 - FW/2, 0, side_h/2), material=mat_frame)

    # 4. Arched Top Frame
    bm = bmesh.new()
    res = 32
    outer_r = W / 2
    inner_r = outer_r - FW
    
    v_out = []
    v_in = []
    for i in range(res + 1):
        angle = math.pi * (i / res) # Semi-circle from pi to 0 or 0 to pi
        # We want the arch to go over the top, so angle starts at 0 and goes to pi
        # x = cos(angle), z = sin(angle)
        x_o = math.cos(angle) * outer_r
        z_o = math.sin(angle) * outer_r + H_straight
        v_out.append(bm.verts.new((x_o, 0, z_o)))
        
        x_i = math.cos(angle) * inner_r
        z_i = math.sin(angle) * inner_r + H_straight
        v_in.append(bm.verts.new((x_i, 0, z_i)))

    # Create faces for the arc profile (the "front" face)
    for i in range(res):
        bm.faces.new((v_out[i], v_out[i+1], v_in[i+1], v_in[i]))
    
    # Extrude along Y axis to give the arch depth T
    # Instead of using bmesh ops which can be version-sensitive, 
    # we manually duplicate and shift.
    geom = bm.faces[:]
    extrude_res = bmesh.ops.extrude_face_region(bm, geom=geom)
    
    # The extruded vertices are in the 'verts' key of the result dictionary
    for v in extrude_res['geom']:
        if isinstance(v, bmesh.types.BMVert):
            v.co.y += T

    # Offset whole arch so it's centered on Y=0
    for v in bm.verts:
        v.co.y -= T/2

    mesh = bpy.data.meshes.new("Frame_Arch")
    bm.to_mesh(mesh)
    bm.free()
    arch_obj = bpy.data.objects.new("Frame_Arch", mesh)
    bpy.context.collection.objects.link(arch_obj)
    arch_obj.data.materials.append(mat_frame)

    # --- Louvers Construction ---
    def add_slat(z, current_w):
        # Slat is a box rotated around Y axis to create louver effect
        # size: (width, thickness-depth, slat-height)
        create_box("Slat", (current_w, T * 0.8, Slat_Thickness), (0, 0, z), (Slat_Angle, 0, 0), mat_slats)

    # Section 1: Bottom Rectangular area
    z_start_bot = FW + Slat_Spacing/2
    z_end_bot = mid_z - FW/2
    curr_z = z_start_bot
    while curr_z < z_end_bot:
        add_slat(curr_z, Slat_Depth)
        curr_z += Slat_Spacing

    # Section 2: Top area (includes the transition into the arch)
    z_start_top = mid_z + FW/2 + Slat_Spacing/2
    total_height = H_straight + R - FW
    
    curr_z = z_start_top
    while curr_z < total_height:
        rel_z = curr_z - H_straight
        if rel_z <= 0:
            # Still in the rectangular part of the top section
            current_w = Slat_Depth
        else:
            # Inside the curved part of the arch
            inner_r = (W / 2) - FW
            if rel_z < inner_r:
                # x^2 + z^2 = r^2  => x = sqrt(r^2 - z^2)
                half_w = math.sqrt(max(0, inner_r**2 - rel_z**2))
                current_w = half_w * 2
            else:
                current_w = 0
        
        if current_w > 0.03: # Skip very tiny slats at the peak
            add_slat(curr_z, current_w)
        curr_z += Slat_Spacing

if __name__ == "__main__":
    build_door()
