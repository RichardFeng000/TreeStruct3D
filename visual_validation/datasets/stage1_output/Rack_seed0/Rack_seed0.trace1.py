import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the scene of all existing mesh objects, lights, and cameras."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a basic metallic material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.3
    output = nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def create_perforated_upright(name, pos, height, material):
    """Creates an L-profile upright with perforated slots."""
    # Dimensions
    w = 0.06  # Flange width
    t = 0.015 # Thickness
    slot_h = 0.03
    slot_gap = 0.04
    num_slots = int(height / (slot_h + slot_gap))

    # Create L-profile mesh
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Profile vertices for L-shape in XY plane
    verts_l = [
        (0, 0, 0), (w, 0, 0), (w, t, 0), 
        (t, t, 0), (t, w, 0), (0, w, 0)
    ]
    bm_verts = [bm.verts.new(v) for v in verts_l]
    face = bm.faces.new(bm_verts)
    
    # Extrude along Z
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    extruded_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=extruded_verts, vec=(0, 0, height))

    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = pos
    obj.data.materials.append(material)
    
    # Create the Slot Tool (Cutter)
    slot_mesh = bpy.data.meshes.new("SlotToolMesh")
    slot_tool = bpy.data.objects.new("SlotTool", slot_mesh)
    bpy.context.collection.objects.link(slot_tool)
    
    bm_s = bmesh.new()
    # Create a small box for the hole
    bmesh.ops.create_cube(bm_s, size=1.0)
    # Scale to slot dimensions: (Width * 2 for overlap, Thickness/2, height)
    # We use scale on the object instead of BMesh for simplicity here
    bm_s.to_mesh(slot_mesh)
    bm_s.free()
    
    slot_tool.scale = (w * 1.5, t * 1.2, slot_h)
    # Position first slot relative to world pos
    slot_tool.location = (pos[0] + w/2, pos[1] + t/2, (slot_h / 2) + 0.1)

    # Array modifier for repeating slots
    arr = slot_tool.modifiers.new(name="Array", type='ARRAY')
    arr.use_relative_offset = False
    arr.constant_offset_displace = (0, 0, slot_h + slot_gap)
    arr.count = num_slots
    
    # Boolean modifier on upright to cut holes
    bool_mod = obj.modifiers.new(name="Slots", type='BOOLEAN')
    bool_mod.object = slot_tool
    bool_mod.operation = 'DIFFERENCE'
    
    # Bake the boolean (apply it)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Slots")
    
    # Remove temporary cutter tool
    bpy.data.objects.remove(slot_tool, do_unlink=True)
    
    return obj

def create_beam(name, p1, p2, material):
    """Creates a sturdy horizontal C-channel beam between two points."""
    p1 = Vector(p1)
    p2 = Vector(p2)
    dist = (p2 - p1).length
    mid = (p1 + p2) / 2
    
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # C-channel profile in YZ plane (width=0.08, height=0.12)
    tw = 0.015 # thickness
    bw = 0.06  # beam width (flange)
    bh = 0.12  # beam height (back wall)
    
    # Profile points in YZ plane: X is the extrusion direction
    # Start at -bw/2, -bh/2 for centering
    verts_p = [
        (0, -bw/2, -bh/2), (0, bw/2, -bh/2), (0, bw/2, -bh/2 + tw),
        (0, tw, -bh/2 + tw), (0, tw, bh/2 - tw), (0, bw/2, bh/2 - tw),
        (0, bw/2, bh/2), (0, -bw/2, bh/2), (0, -bw/2, bh/2 - tw),
        (0, -tw, bh/2 - tw), (0, -tw, -bh/2 + tw), (0, -bw/2, -bh/2 + tw)
    ]
    bm_verts = [bm.verts.new(v) for v in verts_p]
    face = bm.faces.new(bm_verts)
    
    # Critical fix: ensure lookup table is updated before indexing faces
    bm.faces.ensure_lookup_table()
    
    # Extrude along X to create length
    res = bmesh.ops.extrude_face_region(bm, geom=[bm.faces[0]])
    extruded_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=extruded_verts, vec=(dist, 0, 0))
    
    bm.to_mesh(mesh)
    bm.free()
    
    # Center the geometry by shifting it back half distance on X
    # so that rotation is around the center of the beam
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    
    direction = p2 - p1
    rot_quat = direction.to_track_quat('X', 'Z')
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = rot_quat
    obj.location = mid
    
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Rack Parameters
    W, D, H = 3.5, 1.2, 6.0 # Width, Depth, Height
    LEVELS = 4
    STEEL_COLOR = (0.1, 0.1, 0.12, 1.0) # Dark steel / charcoal
    mat = create_material("IndustrialSteel", STEEL_COLOR)
    
    # Corner positions for the uprights
    corners = [
        (-W/2, -D/2, 0), (W/2, -D/2, 0),
        (-W/2, D/2, 0), (W/2, D/2, 0)
    ]
    
    # Create the vertical uprights
    uprights = []
    for i in range(4):
        uprights.append(create_perforated_upright(f"Upright_{i}", corners[i], H, mat))
        
    # Create horizontal beams at multiple levels
    level_step = H / (LEVELS + 1)
    for lvl in range(1, LEVELS + 1):
        z = lvl * level_step
        # Define points for this level's cross-beams
        p0 = (corners[0][0], corners[0][1], z)
        p1 = (corners[1][0], corners[1][1], z)
        p2 = (corners[2][0], corners[2][1], z)
        p3 = (corners[3][0], corners[3][1], z)
        
        # Front span
        create_beam(f"Beam_F_{lvl}", p0, p1, mat)
        # Back span
        create_beam(f"Beam_B_{lvl}", p2, p3, mat)
        # Left side spans
        create_beam(f"Beam_L_{lvl}", p0, p2, mat)
        # Right side spans
        create_beam(f"Beam_R_{lvl}", p1, p3, mat)

if __name__ == "__main__":
    main()
