import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_dark_navy_material():
    """Creates a dark navy material."""
    mat = bpy.data.materials.new(name="DarkNavy")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Dark Navy Color (RGBA) - very dark blue/black
    node_bsdf.inputs['Base Color'].default_value = (0.01, 0.03, 0.12, 1.0)
    node_bsdf.inputs['Roughness'].default_value = 0.35
    
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    
    return mat

def create_arched_door():
    # Parameters
    width = 0.9
    height_spring = 1.8  # Height where the arch begins
    thickness = 0.06
    radius = width / 2
    total_height = height_spring + radius
    
    lite_w = 0.35
    lite_h = 0.6
    lite_z_center = (height_spring + radius) * 0.7  # Upper-center position
    
    mesh = bpy.data.meshes.new("ArchedDoor")
    obj = bpy.data.objects.new("ArchedDoor", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Define the 2D profile of the arch
    segments = 32
    profile_coords = []
    
    # Bottom edge
    profile_coords.append((-width/2, 0))
    profile_coords.append((width/2, 0))
    
    # Right side up to spring line
    profile_coords.append((width/2, height_spring))
    
    # Arch (top half circle) from right to left
    for i in range(segments + 1):
        angle = (math.pi / 2) - (math.pi * i / segments)
        tx = radius * math.cos(angle)
        tz = height_spring + radius * math.sin(angle)
        profile_coords.append((tx, tz))
    
    # Left side down to bottom
    profile_coords.append((-width/2, height_spring))
    # We already have (-width/2, 0) as the first point, but for clarity we can add it or handle loop
    
    # Create vertices for front and back faces
    front_verts = []
    back_verts = []
    
    for cx, cz in profile_coords:
        v_front = bm.verts.new((cx, -thickness/2, cz))
        v_back = bm.verts.new((cx, thickness/2, cz))
        front_verts.append(v_front)
        back_verts.append(v_back)
    
    # Create the front face
    bm.faces.new(front_verts)
    # Create the back face (reverse order to maintain normal direction)
    bm.faces.new(reversed(back_verts))
    
    # Bridge the two faces by creating quads between corresponding vertices
    for i in range(len(front_verts) - 1):
        v1 = front_verts[i]
        v2 = front_verts[i+1]
        v3 = back_verts[i+1]
        v4 = back_verts[i]
        bm.faces.new((v1, v2, v3, v4))
        
    # Close the loop (connect last vertex to first)
    # Only if the profile is not already closed by the sequence
    v_first_f = front_verts[0]
    v_last_f = front_verts[-1]
    v_last_b = back_verts[-1]
    v_first_b = back_verts[0]
    # The loop is actually closed because we defined the coordinates correctly. 
    # Let's check if last point == first point. 
    # In my coords list, I have (-width/2, 0) and then ended with (-width/2, height_spring).
    # Let me fix the profile logic slightly for a perfect loop.

    bm.to_mesh(mesh)
    bm.free()

    # Re-do construction more cleanly to avoid gaps
    # We'll use primitive cubes and boolean operations for the Lite since it's robust.
    # But first, let's fix the arch geometry by using a simple BMesh loop.
    
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    
    # RE-CONSTRUCTION START
    mesh = bpy.data.meshes.new("ArchedDoor")
    obj = bpy.data.objects.new("ArchedDoor", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    
    # 2D Profile loop vertices
    coords = []
    coords.append((-width/2, 0))
    coords.append((width/2, 0))
    coords.append((width/2, height_spring))
    for i in range(segments + 1):
        angle = (math.pi / 2) - (math.pi * i / segments)
        coords.append((radius * math.cos(angle), height_spring + radius * math.sin(angle)))
    coords.append((-width/2, height_spring))
    # No need to append (-width/2, 0) again for face creation if we handle the loop
    
    f_verts = [bm.verts.new((x, -thickness/2, z)) for x, z in coords]
    b_verts = [bm.verts.new((x, thickness/2, z)) for x, z in coords]
    
    # Faces
    bm.faces.new(f_verts)
    bm.faces.new(reversed(b_verts))
    
    for i in range(len(f_verts)):
        v1 = f_verts[i]
        v2 = f_verts[(i + 1) % len(f_verts)]
        v3 = b_verts[(i + 1) % len(b_verts)]
        v4 = b_verts[i]
        bm.faces.new((v1, v2, v3, v4))
    
    bm.to_mesh(mesh)
    bm.free()

    # Lite Cutout (Hole)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cutter = bpy.context.active_object
    cutter.scale = (lite_w, thickness * 3.0, lite_h)
    cutter.location = (0, 0, lite_z_center)
    
    bool_mod = obj.modifiers.new(name="LiteCut", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = cutter
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="LiteCut")
    bpy.data.objects.remove(cutter, do_unlink=True)

    # Inset Frame (Shallow recess around the hole)
    inset_depth = 0.015
    frame_w = lite_w + 0.04
    frame_h = lite_h + 0.04
    
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    inset_cutter = bpy.context.active_object
    # The frame should be slightly larger than the hole, but only cut shallowly into the surface
    inset_cutter.scale = (frame_w, inset_depth * 2.0, frame_h)
    # Position it on the front face (y is -thickness/2)
    inset_cutter.location = (0, -thickness/2 + (inset_depth / 2), lite_z_center)
    
    bool_mod_inset = obj.modifiers.new(name="InsetCut", type='BOOLEAN')
    bool_mod_inset.operation = 'DIFFERENCE'
    bool_mod_inset.object = inset_cutter
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="InsetCut")
    bpy.data.objects.remove(inset_cutter, do_unlink=True)

    # Final polish: Bevel
    bev = obj.modifiers.new(name="DetailBevel", type='BEVEL')
    bev.width = 0.005
    bev.segments = 3
    bpy.ops.object.modifier_apply(modifier="DetailBevel")

    return obj

def main():
    clear_scene()
    navy_mat = create_dark_navy_material()
    door_obj = create_arched_door()
    if not door_obj.data.materials:
        door_obj.data.materials.append(navy_mat)
    else:
        door_obj.data.materials[0] = navy_mat

if __name__ == "__main__":
    main()
