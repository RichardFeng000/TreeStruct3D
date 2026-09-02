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
    """Creates an L-profile upright with clearly visible perforated slots."""
    # Dimensions - slightly increased for visual clarity
    w = 0.08  # Flange width
    t = 0.02  # Thickness
    slot_h = 0.15 # Slot height (made larger to be visible)
    slot_gap = 0.10 # Gap between slots
    num_slots = int(height / (slot_h + slot_gap))

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # L-profile cross section
    verts_l = [
        (0, 0, 0), (w, 0, 0), (w, t, 0), 
        (t, t, 0), (t, w, 0), (0, w, 0)
    ]
    bm_verts = [bm.verts.new(v) for v in verts_l]
    face = bm.faces.new(bm_verts)
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    extruded_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=extruded_verts, vec=(0, 0, height))
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = pos
    obj.data.materials.append(material)
    
    # Create Cutter for slots
    slot_mesh = bpy.data.meshes.new("SlotCutter")
    slot_tool = bpy.data.objects.new("SlotTool", slot_mesh)
    bpy.context.collection.objects.link(slot_tool)
    bm_s = bmesh.new()
    bmesh.ops.create_cube(bm_s, size=1.0)
    bm_s.to_mesh(slot_mesh)
    bm_s.free()
    
    # Cutter size: cuts through the flange
    slot_tool.scale = (w * 2.0, t * 1.5, slot_h)
    # Offset cutter to hit only one face of the L-profile
    slot_tool.location = (pos[0] + w/2, pos[1] + t/2, (slot_h / 2) + 0.2)

    arr = slot_tool.modifiers.new(name="Array", type='ARRAY')
    arr.use_relative_offset = False
    arr.constant_offset_displace = (0, 0, slot_h + slot_gap)
    arr.count = num_slots
    
    bool_mod = obj.modifiers.new(name="Slots", type='BOOLEAN')
    bool_mod.object = slot_tool
    bool_mod.operation = 'DIFFERENCE'
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Slots")
    bpy.data.objects.remove(slot_tool, do_unlink=True)
    
    return obj

def create_beam(name, p1, p2, material):
    """Creates a horizontal C-channel beam."""
    p1 = Vector(p1)
    p2 = Vector(p2)
    dist = (p2 - p1).length
    mid = (p1 + p2) / 2
    
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    tw, bw, bh = 0.015, 0.06, 0.12 # thickness, width, height
    
    verts_p = [
        (0, -bw/2, -bh/2), (0, bw/2, -bh/2), (0, bw/2, -bh/2 + tw),
        (0, tw, -bh/2 + tw), (0, tw, bh/2 - tw), (0, bw/2, bh/2 - tw),
        (0, bw/2, bh/2), (0, -bw/2, bh/2), (0, -bw/2, bh/2 - tw),
        (0, -tw, bh/2 - tw), (0, -tw, -bh/2 + tw), (0, -bw/2, -bh/2 + tw)
    ]
    bm_verts = [bm.verts.new(v) for v in verts_p]
    face = bm.faces.new(bm_verts)
    bm.faces.ensure_lookup_table()
    res = bmesh.ops.extrude_face_region(bm, geom=[bm.faces[0]])
    extruded_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=extruded_verts, vec=(dist, 0, 0))
    bm.to_mesh(mesh)
    bm.free()
    
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
    W, D, H = 3.5, 1.2, 6.0
    LEVELS = 4
    STEEL_COLOR = (0.08, 0.08, 0.1, 1.0)
    mat = create_material("IndustrialSteel", STEEL_COLOR)
    corners = [(-W/2, -D/2, 0), (W/2, -D/2, 0), (-W/2, D/2, 0), (W/2, D/2, 0)]
    
    for i in range(4):
        create_perforated_upright(f"Upright_{i}", corners[i], H, mat)
        
    level_step = H / (LEVELS + 1)
    for lvl in range(1, LEVELS + 1):
        z = lvl * level_step
        p0, p1, p2, p3 = [(corners[i][0], corners[i][1], z) for i in range(4)]
        create_beam(f"Beam_F_{lvl}", p0, p1, mat)
        create_beam(f"Beam_B_{lvl}", p2, p3, mat)
        create_beam(f"Beam_L_{lvl}", p0, p2, mat)
        create_beam(f"Beam_R_{lvl}", p1, p3, mat)

if __name__ == "__main__":
    main()
