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
    node_principled.inputs['Roughness'].default_value = 0.1
    if 'IOR' in node_principled.inputs:
        node_principled.inputs['IOR'].default_value = 1.5
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_bowl():
    # Outer profile: (radius, height)
    outer_profile = [
        (0.15, 0.0), (0.2, 0.0), # Base bottom
        (0.18, 0.2),             # Pedestal neck
        (0.3, 0.4),              # Transition to basin
        (0.35, 0.6),             # Bowl widest point
        (0.35, 0.7),             # Rim height
    ]
    # Inner profile to create the hollow basin
    inner_profile = [
        (0.12, 0.2), (0.28, 0.4), (0.32, 0.65), (0.32, 0.7)
    ]

    bm = bmesh.new()
    segments = 32
    
    def revolve_profile(profile, offset_z=0):
        rings = []
        for px, pz in profile:
            ring = []
            for i in range(segments):
                angle = (2 * math.pi * i) / segments
                ring.append(bm.verts.new(Vector((px * math.cos(angle), px * math.sin(angle), pz + offset_z))))
            rings.append(ring)
        
        for r in range(len(rings)-1):
            for i in range(segments):
                next_i = (i + 1) % segments
                bm.faces.new([rings[r][i], rings[r][next_i], rings[r+1][next_i], rings[r+1][i]])
        return rings

    out_rings = revolve_profile(outer_profile)
    in_rings = revolve_profile(inner_profile)
    
    # Bridge the top rim
    for i in range(segments):
        next_i = (i + 1) % segments
        bm.faces.new([out_rings[-1][i], out_rings[-1][next_i], in_rings[-1][next_i], in_rings[-1][i]])

    mesh = bpy.data.meshes.new("BowlMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("ToiletBowl", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Oval shape for toilet
    obj.scale[1] = 1.3
    
    subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 2
    return obj

def create_tank():
    bm = bmesh.new()
    # Tank size: Width=0.5, Depth=0.3, Height=0.6
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 0.25 # half width
        v.co.y *= 0.15 # half depth
        v.co.z *= 0.3  # half height
        v.co.y -= 0.4  # position behind bowl
        v.co.z += 0.85 # lift to top of bowl area

    mesh = bpy.data.meshes.new("TankMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("ToiletTank", mesh)
    bpy.context.collection.objects.link(obj)
    
    bev = obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.03
    bev.segments = 3
    return obj

def create_seat_ring():
    # The "open seat ring" - a torus-like shape on top of the bowl
    bm = bmesh.new()
    segments = 32
    outer_r, inner_r = 0.37, 0.31
    thickness = 0.04
    z_start = 0.7

    v_out_bottom = [bm.verts.new(Vector((outer_r * math.cos(a), outer_r * math.sin(a), z_start))) for a in [2*math.pi*i/segments for i in range(segments)]]
    v_in_bottom = [bm.verts.new(Vector((inner_r * math.cos(a), inner_r * math.sin(a), z_start))) for a in [2*math.pi*i/segments for i in range(segments)]]

    for i in range(segments):
        next_i = (i + 1) % segments
        bm.faces.new([v_out_bottom[i], v_out_bottom[next_i], v_in_bottom[next_i], v_in_bottom[i]])

    # Extrude up
    res = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
    for v in res['geom']:
        if isinstance(v, bmesh.types.BMVert):
            v.co.z += thickness

    mesh = bpy.data.meshes.new("SeatRingMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("ToiletSeatRing", mesh)
    bpy.context.collection.objects.link(obj)
    obj.scale[1] = 1.3
    return obj

def create_lid():
    bm = bmesh.new()
    segments = 32
    radius, thickness = 0.38, 0.04
    z_start = 0.7 + 0.04 # Sit on top of ring

    # Flat disk
    v_out = [bm.verts.new(Vector((radius * math.cos(a), radius * math.sin(a), z_start))) for a in [2*math.pi*i/segments for i in range(segments)]]
    center_v = bm.verts.new(Vector((0, 0, z_start)))
    for i in range(segments):
        next_i = (i + 1) % segments
        bm.faces.new([center_v, v_out[next_i], v_out[i]])

    res = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
    for v in res['geom']:
        if isinstance(v, bmesh.types.BMVert):
            v.co.z += thickness

    mesh = bpy.data.meshes.new("LidMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("ToiletLid", mesh)
    bpy.context.collection.objects.link(obj)
    obj.scale[1] = 1.3

    # Pivot at the back (around Y = -0.4)
    pivot_y = -0.45
    for v in obj.data.vertices:
        v.co.y -= pivot_y
        v.co.z -= z_start
    
    obj.location = (0, pivot_y, z_start)
    obj.rotation_euler[0] = math.radians(-80)
    return obj

def create_handle():
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 0.02  # Thinness
        v.co.y *= 0.05  # Length
        v.co.z *= 0.03  # Height
    
    mesh = bpy.data.meshes.new("HandleMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("FlushHandle", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Place firmly on the side of the tank (tank x range is -0.25 to 0.25, y center -0.4)
    obj.location = (0.26, -0.4, 1.0)
    return obj

def main():
    clear_scene()
    ceramic_mat = create_material("CeramicWhite")
    
    bowl = create_bowl()
    tank = create_tank()
    ring = create_seat_ring()
    lid = create_lid()
    handle = create_handle()
    
    for p in [bowl, tank, ring, lid, handle]:
        if not p.data.materials:
            p.data.materials.append(ceramic_mat)
        else:
            p.data.materials[0] = ceramic_mat

if __name__ == "__main__":
    main()
