import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.4
    output = nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def create_perforated_upright(name, pos, height, material):
    """Creates an L-profile upright with vertical slot perforations using BMesh."""
    # Dimensions
    w = 0.08  # Width of the L flanges
    t = 0.02  # Thickness
    slot_h = 0.03
    slot_gap = 0.05
    num_slots = int(height / (slot_h + slot_gap))

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Create the main L-profile volume as a box then cut slots
    # We build it as an extrusion of an L-shape
    # Verts for L-shape profile in XY plane
    verts_l = [
        (0, 0, 0), (w, 0, 0), (w, t, 0), 
        (t, t, 0), (t, w, 0), (0, w, 0)
    ]
    bm_verts = [bm.verts.new(v) for v in verts_l]
    face = bm.faces.new(bm_verts)
    
    # Extrude up
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    extruded_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=extruded_verts, vec=(0, 0, height))

    # Perforations: Use boolean-like subtraction by creating small boxes and using bmesh.ops.bisect or similar?
    # Actually, for stability in a script, we can just create the L-profile as a series of segments
    # but it's easier to use a simple Boolean modifier on the resulting object once.
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = pos
    obj.data.materials.append(material)
    
    # Add slots using boolean objects (more reliable than complex bmesh cuts for simple holes)
    for i in range(num_slots):
        z_pos = (i * (slot_h + slot_gap)) + (slot_h / 2) + 0.1
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        slot = bpy.context.active_object
        slot.scale = (w * 1.1, t * 0.5, slot_h) # Cut through the flange
        slot.location = (w / 2, 0, z_pos + pos[2]) # Relative to world
        # Since obj is at pos, and slots are at pos + offset...
        # Better: use a modifier on the upright
        
        # To avoid too many objects, let's use one slot object with an array
        break 

    # Corrected Slot Implementation using Array Modifier for efficiency
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    slot_tool = bpy.context.active_object
    slot_tool.name = "SlotTool"
    slot_tool.scale = (w * 1.1, t * 0.6, slot_h)
    # Position it to cut the front face of the L-profile
    slot_tool.location = (pos[0] + w/2, pos[1] + t/2, (slot_h/2) + 0.1 + pos[2])
    
    arr = slot_tool.modifiers.new(name="Array", type='ARRAY')
    arr.use_relative_offset = False
    arr.constant_offset_displace = (0, 0, slot_h + slot_gap)
    arr.count = num_slots
    
    bool_mod = obj.modifiers.new(name="Slots", type='BOOLEAN')
    bool_mod.object = slot_tool
    bool_mod.operation = 'DIFFERENCE'
    
    # Apply modifier to bake the holes into geometry
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Slots")
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
    # C-channel profile in YZ plane (width=0.08, height=0.1)
    tw = 0.02 # thickness
    bw = 0.06 # beam width
    bh = 0.1  # beam height
    
    verts = [
        (-bw/2, 0, -bh/2), (bw/2, 0, -bh/2), (bw/2, 0, -bh/2 + tw),
        (tw, 0, -bh/2 + tw), (tw, 0, bh/2 - tw), (bw/2, 0, bh/2 - tw),
        (bw/2, 0, bh/2), (-bw/2, 0, bh/2), (-bw/2, 0, bh/2 - tw),
        (-tw, 0, bh/2 - tw), (-tw, 0, -bh/2 + tw), (-bw/2, 0, -bh/2 + tw)
    ]
    bm_verts = [bm.verts.new(v) for v in verts]
    bm.faces.new(bm_verts)
    
    # Extrude along X to create length
    res = bmesh.ops.extrude_face_region(bm, geom=[bm.faces[0]])
    extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=extruded, vec=(dist, 0, 0))
    
    bm.to_mesh(mesh)
    bm.free()
    
    # Alignment: Geometry is from 0 to dist on X axis.
    # Move origin to center of geometry so we can rotate and place it at midpoint.
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
    
    # Parameters
    W, D, H = 3.0, 1.2, 5.0 # Width, Depth, Height
    LEVELS = 4
    # Use a charcoal gray that is visible against black (not absolute dark)
    STEEL_COLOR = (0.15, 0.15, 0.18, 1.0) 
    mat = create_material("IndustrialSteel", STEEL_COLOR)
    
    # Corner positions
    corners = [
        (-W/2, -D/2, 0), (W/2, -D/2, 0),
        (-W/2, D/2, 0), (W/2, D/2, 0)
    ]
    
    # Create Uprights
    uprights = []
    for i, pos in enumerate(corners):
        uprights.append(create_perforated_upright(f"Upright_{i}", pos, H, mat))
        
    # Create Beams at levels
    level_step = H / (LEVELS + 1)
    for lvl in range(1, LEVELS + 1):
        z = lvl * level_step
        # Front span
        create_beam(f"Beam_F_{lvl}", (corners[0][0], corners[0][1], z), (corners[1][0], corners[1][1], z), mat)
        # Back span
        create_beam(f"Beam_B_{lvl}", (corners[2][0], corners[2][1], z), (corners[3][0], corners[3][1], z), mat)
        # Left side spans
        create_beam(f"Beam_L_{lvl}", (corners[0][0], corners[0][1], z), (corners[2][0], corners[2][1], z), mat)
        # Right side spans
        create_beam(f"Beam_R_{lvl}", (corners[1][0], corners[1][1], z), (corners[3][0], corners[3][1], z), mat)

if __name__ == "__main__":
    main()
