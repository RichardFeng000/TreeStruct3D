import bpy
import bmesh
import math

def clear_scene():
    """Clears the default Blender scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_dark_navy_material():
    """Creates a dark navy material that is visible in renders."""
    mat = bpy.data.materials.new(name="DarkNavy")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Slightly lighter dark navy to ensure visibility (deep blue)
    node_bsdf.inputs['Base Color'].default_value = (0.02, 0.08, 0.25, 1.0)
    node_bsdf.inputs['Roughness'].default_value = 0.3
    node_bsdf.inputs['Metallic'].default_value = 0.1
    
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    
    return mat

def create_arched_door():
    # Dimensions
    width = 0.9
    height_spring = 1.8  # Where the arch starts
    thickness = 0.06
    radius = width / 2
    total_height = height_spring + radius
    
    lite_w = 0.3
    lite_h = 0.5
    lite_z_center = (total_height * 0.7) # Upper-center
    
    # Create Mesh and Object
    mesh = bpy.data.meshes.new("ArchedDoor")
    obj = bpy.data.objects.new("ArchedDoor", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # 1. Create the door's outer profile (2D)
    segments = 32
    coords = []
    # Bottom edge
    coords.append((-width/2, 0))
    coords.append((width/2, 0))
    # Right side up to spring line
    coords.append((width/2, height_spring))
    # Arch (quarter circle)
    for i in range(segments + 1):
        angle = (math.pi / 2) - (math.pi * i / segments)
        coords.append((radius * math.cos(angle), height_spring + radius * math.sin(angle)))
    # Left side down to bottom
    coords.append((-width/2, height_spring))
    
    # Create the front face (z=0 plane for now)
    verts = [bm.verts.new((x, 0, z)) for x, z in coords]
    face = bm.faces.new(verts)
    
    # Extrude the profile to create thickness
    # We extrude along Y axis
    extruded_geom = bmesh.ops.extrude_face_region(bm, geom=[face])
    verts_extruded = [v for v in extruded_geom['geom'] if isinstance(v, bpy.types.BMVertex)]
    
    # Move the extruded vertices back by thickness
    for v in verts_extruded:
        v.co.y += thickness

    # Finalize base mesh
    bm.to_mesh(mesh)
    bm.free()
    
    # Use Boolean for the lite cutout to ensure clean rectangular geometry
    bpy.context.view_layer.objects.active = obj
    
    # --- LITE CUTOUT ---
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cutter = bpy.context.active_object
    cutter.scale = (lite_w, thickness * 2.0, lite_h)
    cutter.location = (0, thickness / 2, lite_z_center)
    
    bool_mod = obj.modifiers.new(name="LiteCut", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = cutter
    bpy.ops.object.modifier_apply(modifier="LiteCut")
    bpy.data.objects.remove(cutter, do_unlink=True)

    # --- INSET FRAME (The recessed detail around the hole) ---
    inset_depth = 0.015
    frame_w = lite_w + 0.08
    frame_h = lite_h + 0.08
    
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    inset_cutter = bpy.context.active_object
    # This cube only cuts a thin layer into the front face (y=0)
    inset_cutter.scale = (frame_w, inset_depth * 2, frame_h)
    # Positioned so it sinks slightly into the surface at y=0
    inset_cutter.location = (0, inset_depth / 2, lite_z_center)
    
    bool_mod_inset = obj.modifiers.new(name="InsetCut", type='BOOLEAN')
    bool_mod_inset.operation = 'DIFFERENCE'
    bool_mod_inset.object = inset_cutter
    bpy.ops.object.modifier_apply(modifier="InsetCut")
    bpy.data.objects.remove(inset_cutter, do_unlink=True)

    # --- FINAL POLISH: Bevel ---
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
