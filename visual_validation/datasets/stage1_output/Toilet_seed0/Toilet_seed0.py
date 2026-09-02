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
    # Profile for a more realistic toilet bowl: (radius, height)
    # Base -> Pedestal -> Basin Curve -> Rim
    outer_profile = [
        (0.20, 0.0),   # Floor contact
        (0.18, 0.1),   # Taper in slightly
        (0.22, 0.3),   # Pedestal widen
        (0.35, 0.5),   # Basin curve outward
        (0.36, 0.7),   # Rim height
    ]
    inner_profile = [
        (0.15, 0.2),   # Bottom of basin
        (0.30, 0.4),   # Inner walls
        (0.33, 0.7),   # Inner rim
    ]

    bm = bmesh.new()
    segments = 32
    
    def revolve_profile(profile):
        rings = []
        for px, pz in profile:
            ring = []
            for i in range(segments):
                angle = (2 * math.pi * i) / segments
                ring.append(bm.verts.new(Vector((px * math.cos(angle), px * math.sin(angle), pz))))
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
    
    # Make it oval (standard toilet shape)
    obj.scale[1] = 1.3
    
    subdiv = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 2
    return obj

def create_tank():
    bm = bmesh.new()
    # Tank size: Width=0.45, Depth=0.3, Height=0.5
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 0.225 # half width
        v.co.y *= 0.15  # half depth
        v.co.z *= 0.25  # half height
        v.co.y -= 0.3   # push behind bowl center
        v.co.z += 0.6   # lift up (roughly floor to rim height)

    mesh = bpy.data.meshes.new("TankMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("ToiletTank", mesh)
    bpy.context.collection.objects.link(obj)
    
    bev = obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.02
    bev.segments = 3
    return obj

def create_seat_ring():
    bm = bmesh.new()
    segments = 32
    outer_r, inner_r = 0.38, 0.32
    thickness = 0.04
    z_start = 0.7

    v_out_bottom = [bm.verts.new(Vector((outer_r * math.cos(a), outer_r * math.sin(a), z_start))) for a in [2*math.pi*i/segments for i in range(segments)]]
    v_in_bottom = [bm.verts.new(Vector((inner_r * math.cos(a), inner_r * math.sin(a), z_start))) for a in [2*math.pi*i/segments for i in range(segments)]]

    for i in range(segments):
        next_i = (i + 1) % segments
        bm.faces.new([v_out_bottom[i], v_out_bottom[next_i], v_in_bottom[next_i], v_in_bottom[i]])

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
    radius, thickness = 0.39, 0.04
    z_start = 0.7 + 0.04

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

    # Hinge point: Back of the bowl (Y offset ~ -0.35 to -0.4)
    pivot_y = -0.38
    for v in obj.data.vertices:
        v.co.y -= pivot_y
        v.co.z -= z_start
    
    obj.location = (0, pivot_y, z_start)
    obj.rotation_euler[0] = math.radians(-75) # tilted upright
    return obj

def create_handle():
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 0.02  # thin
        v.co.y *= 0.04  # depth
        v.co.z *= 0.03  # height
    
    mesh = bpy.data.meshes.new("HandleMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("FlushHandle", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Place exactly on the side of the enlarged tank (Tank x range is -0.225 to 0.225)
    obj.location = (0.23, -0.3, 0.8)
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
