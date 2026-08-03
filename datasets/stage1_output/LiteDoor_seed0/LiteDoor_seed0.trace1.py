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
    """Creates a dark navy material."""
    mat = bpy.data.materials.new(name="DarkNavy")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Dark Navy Color (deep blue)
    node_bsdf.inputs['Base Color'].default_value = (0.01, 0.04, 0.12, 1.0)
    node_bsdf.inputs['Roughness'].default_value = 0.35
    node_bsdf.inputs['Metallic'].default_value = 0.0
    
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
    lite_z_center = (total_height * 0.7) # Upper-center position
    
    # Create Mesh and Object
    mesh = bpy.data.meshes.new("ArchedDoor")
    obj = bpy.data.objects.new("ArchedDoor", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # 1. Create the door's outer profile (2D on XZ plane)
    segments = 32
    coords = []
    # Bottom edge
    coords.append((-width/2, 0))
    coords.append((width/2, 0))
    # Right side up to spring line
    coords.append((width/2, height_spring))
    # Arch (semi-circle top)
    for i in range(segments + 1):
        angle = (math.pi / 2) - (math.pi * i / segments)
        coords.append((radius * math.cos(angle), height_spring + radius * math.sin(angle)))
    # Left side down to bottom
    coords.append((-width/2, height_spring))
    
    # Create the front face (XZ plane)
    verts = [bm.verts.new((x, 0, z)) for x, z in coords]
    face = bm.faces.new(verts)
    
    # Extrude along Y to create thickness
    extruded_geom = bmesh.ops.extrude_face_region(bm, geom=[face])
    # Filter only the newly created vertices from the extrusion
    verts_extruded = [v for v in extruded_geom['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in verts_extruded:
        v.co.y += thickness

    bm.to_mesh(mesh)
    bm.free()
    
    # Ensure object is active for operators
    bpy.context.view_layer.objects.active = obj
    
    # --- LITE CUTOUT (The hole) ---
    # Create a cube to act as the cutter
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cutter = bpy.context.active_object
    cutter.scale = (lite_w, thickness * 2.0, lite_h)
    # Center it on Y and put at upper-center Z
    cutter.location = (0, thickness / 2, lite_z_center)
    
    bool_mod = obj.modifiers.new(name="LiteCut", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = cutter
    bpy.ops.object.modifier_apply(modifier="LiteCut")
    bpy.data.objects.remove(cutter, do_unlink=True)

    # --- INSET FRAME (The recessed detail around the hole) ---
    inset_depth = 0.01
    frame_w = lite_w + 0.06
    frame_h = lite_h + 0.06
    
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    inset_cutter = bpy.context.active_object
    # This cube cuts only into the front face (Y=0)
    inset_cutter.scale = (frame_w, inset_depth * 2, frame_h)
    # Shift it so it sinks slightly into the door surface
    inset_cutter.location = (0, inset_depth / 2, lite_z_center)
    
    bool_mod_inset = obj.modifiers.new(name="InsetCut", type='BOOLEAN')
    bool_mod_inset.operation = 'DIFFERENCE'
    bool_mod_inset.object = inset_cutter
    bpy.ops.object.modifier_apply(modifier="InsetCut")
    bpy.data.objects.remove(inset_cutter, do_unlink=True)

    # --- FINAL POLISH: Bevel edges for realism ---
    bev = obj.modifiers.new(name="DetailBevel", type='BEVEL')
    bev.width = 0.003
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
