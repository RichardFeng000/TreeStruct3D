import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_fern_material():
    mat = bpy.data.materials.new(name="FernGreen")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    # Muted natural green
    bsdf.inputs['Base Color'].default_value = (0.15, 0.28, 0.06, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.7
    return mat

def create_cylinder(bm, start, end, radius=0.01):
    """Creates a simple cylinder between two points."""
    segments = 5
    dir_vec = (end - start).normalized()
    # Create local coordinate system for the circle
    up = Vector((0, 0, 1)) if abs(dir_vec.z) < 0.9 else Vector((0, 1, 0))
    right = dir_vec.cross(up).normalized()
    top = dir_vec.cross(right).normalized()

    verts_start = []
    verts_end = []

    for i in range(segments):
        angle = (2 * math.pi / segments) * i
        offset = (right * math.cos(angle) + top * math.sin(angle)) * radius
        verts_start.append(bm.verts.new(start + offset))
        verts_end.append(bm.verts.new(end + offset))

    for i in range(segments):
        v1 = verts_start[i]
        v2 = verts_start[(i + 1) % segments]
        v3 = verts_end[(i + 1) % segments]
        v4 = verts_end[i]
        bm.faces.new((v1, v2, v3, v4))

def create_blade(bm, start, end, width=0.05):
    """Creates an elongated leaf blade."""
    mid = (start + end) * 0.5
    # Perpendicular to the blade direction for thickness
    perp = Vector((0, 0, 1)).cross(end - start).normalized() * (width * 0.5)
    
    v1 = bm.verts.new(start)
    v2 = bm.verts.new(mid + perp)
    v3 = bm.verts.new(end)
    v4 = bm.verts.new(mid - perp)
    bm.faces.new((v1, v2, v3, v4))

def create_frond(bm, origin, direction, length=4.0, arch_height=1.8):
    """Creates a structured fern frond."""
    segments = 15
    stem_points = []
    for i in range(segments + 1):
        t = i / segments
        # Parabolic arc for the main stem
        pos = origin + direction * (length * t)
        pos.z += arch_height * (math.sin(t * math.pi))
        stem_points.append(pos)

    # 1. Main Stem Geometry
    for i in range(segments):
        create_cylinder(bm, stem_points[i], stem_points[i+1], radius=0.02 * (1.0 - (i/segments)*0.5))

    # 2. Pinnae (Secondary stems)
    num_pinnae = 18
    for i in range(1, num_pinnae):
        t = i / num_pinnae
        idx = int(t * segments)
        if idx >= len(stem_points): continue
        p_start = stem_points[idx]

        # Tangent and right vector for branching
        tangent = (stem_points[min(idx+1, segments)] - stem_points[max(idx-1, 0)]).normalized()
        right = tangent.cross(Vector((0, 0, 1))).normalized()
        if right.length < 0.1: right = Vector((1, 0, 0))

        pinna_len = (length * 0.3) * (1.0 - t**0.6)
        if pinna_len < 0.1: continue

        for side in [-1, 1]:
            p_end = p_start + (right * side * pinna_len)
            # Create the secondary stem
            create_cylinder(bm, p_start, p_end, radius=0.008)

            # 3. Pinnules (The actual leaflets)
            num_pinnules = 8
            for j in range(1, num_pinnules):
                u = j / num_pinnules
                leaf_start = p_start.lerp(p_end, u)
                
                # Direction for the leaflet: outwards from pinna stem
                # Mix of right vector and slightly 'down' relative to frond arch
                leaf_dir = (right * side).cross(tangent).normalized()
                # Adjust direction based on where we are in the frond to look more natural
                leaf_dir += tangent * -0.2 
                leaf_dir = leaf_dir.normalized()

                pinnule_len = pinna_len * 0.7 * (1.0 - u)
                if pinnule_len < 0.05: continue
                
                leaf_end = leaf_start + leaf_dir * pinnule_len
                create_blade(bm, leaf_start, leaf_end, width=0.06 * (1.0 - t))

def build_fern():
    clear_scene()
    mat = create_fern_material()
    
    mesh = bpy.data.meshes.new("FernPlant")
    obj = bpy.data.objects.new("Fern", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    
    bm = bmesh.new()
    num_fronds = 8
    origin = Vector((0, 0, 0))
    
    for i in range(num_fronds):
        angle = (2 * math.pi / num_fronds) * i + random.uniform(-0.3, 0.3)
        dir_vec = Vector((math.cos(angle), math.sin(angle), 0))
        length = 4.0 + random.uniform(-0.8, 0.8)
        arch = 1.5 + random.uniform(-0.3, 0.7)
        create_frond(bm, origin, dir_vec, length=length, arch_height=arch)

    bm.to_mesh(mesh)
    bm.free()
    obj.rotation_euler = (math.radians(5), 0, 0)

if __name__ == "__main__":
    build_fern()
