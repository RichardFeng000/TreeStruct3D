import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color=(1, 1, 1, 1)):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Roughness'].default_value = 0.05
    if 'IOR' in node_principled.inputs:
        node_principled.inputs['IOR'].default_value = 1.5
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_bowl():
    # Profile for the toilet bowl and base: (radius, height)
    profile = [
        (0.0, 0.0),          # Center bottom
        (0.18, 0.0),         # Bottom edge radius
        (0.16, 0.2),         # Pedestal neck
        (0.22, 0.3),         # Transition to basin
        (0.32, 0.45),        # Widest part of bowl bottom
        (0.35, 0.7),         # Rim top height
    ]
    
    bm = bmesh.new()
    segments = 32
    rings = []
    
    for px, pz in profile:
        ring = []
        if px == 0:
            v = bm.verts.new(Vector((0, 0, pz)))
            ring.append(v)
        else:
            for i in range(segments):
                angle = (2 * math.pi * i) / segments
                ring.append(bm.verts.new(Vector((px * math.cos(angle), px * math.sin(angle), pz))))
        rings.append(ring)

    for r in range(len(rings) - 1):
        curr_r = rings[r]
        next_r = rings[r+1]
        
        if len(curr_r) == 1: # Center point (bottom)
            for i in range(segments):
                next_i = (i + 1) % segments
                bm.faces.new([curr_r[0], next_r[next_i], next_r[i]])
        elif len(next_r) == 1: # Collapsing to center point (top - not likely here but for safety)
            for i in range(segments):
                prev_i = (i - 1) % segments
                bm.faces.new([curr_r[i], curr_r[prev_i], next_r[0]])
        else: # Ring to ring
            for i in range(segments):
                next_i = (i + 1) % segments
                bm.faces.new([curr_r[i], curr_r[next_i], next_r[next_i], next_r[i]])

    # Create a rim thickness by extruding the top face slightly or using modifiers
    bm.to_mesh(bpy.data.meshes.new("BowlMesh"))
    obj = bpy.data.objects.new("ToiletBowl", bpy.data.meshes.get("BowlMesh"))
    bpy.context.collection.objects.link(obj)
    
    # Smooth out the form
    subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 2
    
    return obj

def create_tank():
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale and position: Width ~ 0.5, Depth ~ 0.3, Height ~ 0.5
    for v in bm.verts:
        v.co.x *= 0.25 # Half width
        v.co.y *= 0.15 # Half depth
        v.co.z *= 0.25 # Half height
        v.co.z += 0.8   # Lift it up
        v.co.y -= 0.3   # Shift behind the bowl

    bm.to_mesh(bpy.data.meshes.new("TankMesh"))
    obj = bpy.data.objects.new("ToiletTank", bpy.data.meshes.get("TankMesh"))
    bpy.context.collection.objects.link(obj)
    
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.04
    bevel.segments = 5
    
    subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 1
    
    return obj

def create_seat():
    bm = bmesh.new()
    segments = 32
    outer_r = 0.36
    inner_r = 0.24
    height = 0.7
    thickness = 0.04

    # Outer ring vertices
    v_outer = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        v_outer.append(bm.verts.new(Vector((outer_r * math.cos(angle), outer_r * math.sin(angle), height))))

    # Inner ring vertices
    v_inner = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        v_inner.append(bm.verts.new(Vector((inner_r * math.cos(angle), inner_r * math.sin(angle), height))))

    # Create top surface faces
    for i in range(segments):
        next_i = (i + 1) % segments
        bm.faces.new([v_outer[i], v_outer[next_i], v_inner[next_i], v_inner[i]])

    # Extrude for thickness - FIX: only iterate over BMVerts in the result geom
    bm.verts.ensure_lookup_table()
    faces = list(bm.faces)
    res = bmesh.ops.extrude_face_region(bm, geom=faces)
    for v in res['geom']:
        if isinstance(v, bmesh.types.BMVert):
            v.co.z += thickness

    bm.to_mesh(bpy.data.meshes.new("SeatMesh"))
    obj = bpy.data.objects.new("ToiletSeat", bpy.data.meshes.get("SeatMesh"))
    bpy.context.collection.objects.link(obj)
    
    # Make the seat oval along Y
    obj.scale[1] = 1.3
    
    bev = obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.01
    
    return obj

def create_lid():
    bm = bmesh.new()
    # A simple cylinder as the lid base
    bmesh.ops.create_cylinder(bm, segments=32, radius=0.37, depth=0.04)
    
    # Scale to oval shape in BMesh before converting
    for v in bm.verts:
        v.co.y *= 1.3

    bm.to_mesh(bpy.data.meshes.new("LidMesh"))
    obj = bpy.data.objects.new("ToiletLid", bpy.data.meshes.get("LidMesh"))
    bpy.context.collection.objects.link(obj)
    
    # Pivot point is at the back of the seat: Y ~ -0.2, Z ~ 0.7
    # Move geometry so origin is at the pivot (back edge of oval lid)
    for v in obj.data.vertices:
        v.co.y += 0.3 # offset based on radius * scale
        v.co.z -= 0.7

    obj.location = (0, -0.2, 0.7)
    # Tilt upright (approximately 85 degrees)
    obj.rotation_euler[0] = math.radians(-85)
    
    subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 1
    
    return obj

def create_handle():
    bm = bmesh.new()
    # Handle is a small elongated cylinder/cube
    bmesh.ops.create_cube(bm, size=0.05)
    for v in bm.verts:
        v.co.x *= 1.5 # length of handle lever
        v.co.y *= 0.4
        v.co.z *= 0.2
        
    bm.to_mesh(bpy.data.meshes.new("HandleMesh"))
    obj = bpy.data.objects.new("FlushHandle", bpy.data.meshes.get("HandleMesh"))
    bpy.context.collection.objects.link(obj)
    
    # Position on the right side of the tank (X=0.25, Y=-0.3, Z=1.0)
    obj.location = (0.27, -0.3, 1.0)
    
    return obj

def main():
    clear_scene()
    
    ceramic_mat = create_material("CeramicWhite")
    
    bowl = create_bowl()
    tank = create_tank()
    seat = create_seat()
    lid = create_lid()
    handle = create_handle()
    
    parts = [bowl, tank, seat, lid, handle]
    for p in parts:
        if not p.data.materials:
            p.data.materials.append(ceramic_mat)
        else:
            p.data.materials[0] = ceramic_mat

if __name__ == "__main__":
    main()
