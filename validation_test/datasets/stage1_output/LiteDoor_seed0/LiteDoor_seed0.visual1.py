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
    
    # Dark Navy Color (RGBA) - Deep blue
    node_bsdf.inputs['Base Color'].default_value = (0.02, 0.05, 0.15, 1.0)
    node_bsdf.inputs['Roughness'].default_value = 0.4
    
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
    
    lite_w = 0.3
    lite_h = 0.5
    lite_z_center = (height_spring + radius) * 0.7  # Position in upper-center
    
    mesh = bpy.data.meshes.new("ArchedDoor")
    obj = bpy.data.objects.new("ArchedDoor", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # 1. Create the 2D Profile
    segments = 32
    coords = []
    # Bottom edge
    coords.append((-width/2, 0))
    coords.append((width/2, 0))
    # Right side up to spring line
    coords.append((width/2, height_spring))
    # Semi-circle arch from right (pi/2) to left (3pi/2)
    for i in range(segments + 1):
        angle = (math.pi / 2) - (math.pi * i / segments)
        coords.append((radius * math.cos(angle), height_spring + radius * math.sin(angle)))
    # Left side down to bottom
    coords.append((-width/2, height_spring))
    
    # Create vertices for front and back faces
    f_verts = [bm.verts.new((x, -thickness/2, z)) for x, z in coords]
    b_verts = [bm.verts.new((x, thickness/2, z)) for x, z in coords]
    
    # Create the front and back faces
    # Use BMesh face creation; we'll triangulate them later to avoid Boolean issues
    bm.faces.new(f_verts)
    bm.faces.new(reversed(b_verts))
    
    # Bridge the two faces with quads (the edges of the door)
    for i in range(len(f_verts)):
        v1 = f_verts[i]
        v2 = f_verts[(i + 1) % len(f_verts)]
        v3 = b_verts[(i + 1) % len(b_verts)]
        v4 = b_verts[i]
        bm.faces.new((v1, v2, v3, v4))
    
    # Triangulate the large N-gon faces to ensure Boolean robustness
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    
    bm.to_mesh(mesh)
    bm.free()

    # --- LITE CUTOUT (The hole) ---
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cutter = bpy.context.active_object
    cutter.scale = (lite_w, thickness * 2.5, lite_h) # Slightly thicker than door to ensure clean cut
    cutter.location = (0, 0, lite_z_center)
    
    bool_mod = obj.modifiers.new(name="LiteCut", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = cutter
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="LiteCut")
    bpy.data.objects.remove(cutter, do_unlink=True)

    # --- INSET FRAME (The recessed area around the hole) ---
    inset_depth = 0.01 # Depth of recess
    frame_w = lite_w + 0.06
    frame_h = lite_h + 0.06
    
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    inset_cutter = bpy.context.active_object
    # The frame is a slightly larger box that only cuts shallowly into the front surface
    inset_cutter.scale = (frame_w, inset_depth * 2.0, frame_h)
    # Position it on the front face (-thickness/2) but shifted so it sinks in
    inset_cutter.location = (0, -thickness/2 + (inset_depth / 2), lite_z_center)
    
    bool_mod_inset = obj.modifiers.new(name="InsetCut", type='BOOLEAN')
    bool_mod_inset.operation = 'DIFFERENCE'
    bool_mod_inset.object = inset_cutter
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="InsetCut")
    bpy.data.objects.remove(inset_cutter, do_unlink=True)

    # --- FINAL DETAIL: Bevel the edges ---
    bev = obj.modifiers.new(name="DetailBevel", type='BEVEL')
    bev.width = 0.005
    bev.segments = 2
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
