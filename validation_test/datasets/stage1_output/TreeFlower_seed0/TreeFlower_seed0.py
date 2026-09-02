import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_petal_mesh(material):
    mesh = bpy.data.meshes.new("PetalMesh")
    bm = bmesh.new()
    
    length = 3.2
    width = 0.5
    thickness = 0.03
    segments = 16
    
    verts = []
    for i in range(segments + 1):
        t = i / segments
        x = t * length
        # Tapered petal shape
        w = math.sin(t * math.pi) * width
        verts.append(bm.verts.new((x, -w/2, 0)))
        verts.append(bm.verts.new((x, w/2, 0)))

    for i in range(segments):
        v1 = verts[i*2]
        v2 = verts[i*2 + 1]
        v3 = verts[(i+1)*2 + 1]
        v4 = verts[(i+1)*2]
        bm.faces.new((v1, v2, v3, v4))

    faces_to_extrude = bm.faces[:]
    res = bmesh.ops.extrude_face_region(bm, geom=faces_to_extrude)
    verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in verts_extruded:
        v.co.z += thickness

    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Petal", mesh)
    obj.data.materials.append(material)
    return obj

def create_central_assembly(mat_tan):
    mesh = bpy.data.meshes.new("CentralDisk")
    bm = bmesh.new()
    
    disk_radius = 1.0
    dome_height = 0.5
    
    # Create the base dome
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=disk_radius)
    verts_to_del = [v for v in bm.verts if v.co.z < 0]
    bmesh.ops.delete(bm, geom=verts_to_del, context='VERTS')
    for v in bm.verts:
        v.co.z *= (dome_height / disk_radius)

    # Create florets on the surface of the dome
    num_florets = 700
    floret_radius = 0.06
    floret_height = 0.15
    golden_angle = math.pi * (3 - math.sqrt(5))
    
    for i in range(num_florets):
        # Distribution on a spherical cap
        r = math.sqrt(i / num_florets) # Radius factor for uniform distribution
        theta = r * 2 * math.pi # This isn't quite the phyllotaxis, but let's use it
        # Actually, correct Fibonacci spiral on sphere:
        phi_angle = i * golden_angle
        z_norm = 1.0 - (i / float(num_florets-1)) * 2.0 # from 1 to -1
        # We only want the top dome, so map z_norm from [1, 0]
        z_val = (1.0 - (i / float(num_florets))) * dome_height
        radius_at_z = disk_radius * math.sqrt(max(0, 1.0 - (z_val/dome_height)**2))
        x_val = math.cos(phi_angle) * radius_at_z
        y_val = math.sin(phi_angle) * radius_at_z
        
        pos = Vector((x_val, y_val, z_val))
        # Normal for the dome (since it's a scaled sphere)
        normal = Vector((x_val, y_val, z_val * (disk_radius / dome_height))).normalized()
        
        rot_quat = Vector((0, 0, 1)).rotation_difference(normal)
        rot_mat = rot_quat.to_matrix()
        
        # Create a simple cylinder for the floret
        sides = 6
        local_verts = []
        for s in range(sides):
            angle = (2 * math.pi / sides) * s
            vx, vy = math.cos(angle) * floret_radius, math.sin(angle) * floret_radius
            v_base = bm.verts.new(pos + rot_mat @ Vector((vx, vy, 0)))
            v_top = bm.verts.new(pos + rot_mat @ Vector((vx, vy, floret_height)))
            local_verts.append((v_base, v_top))

        for s in range(sides):
            v1b = local_verts[s][0]
            v1t = local_verts[s][1]
            v2b = local_verts[(s+1)%sides][0]
            v2t = local_verts[(s+1)%sides][1]
            bm.faces.new((v1b, v2b, v2t, v1t))
        
        bm.faces.new([lv[0] for lv in local_verts])
        bm.faces.new([lv[1] for lv in local_verts])

    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("CentralDisk", mesh)
    obj.data.materials.append(mat_tan)
    return obj

def main():
    clear_scene()
    
    mat_white = create_material("WhitePetal", (1.0, 1.0, 1.0, 1.0))
    mat_tan = create_material("TanFloret", (0.85, 0.65, 0.4, 1.0))
    
    disk_obj = create_central_assembly(mat_tan)
    bpy.context.collection.objects.link(disk_obj)
    
    num_petals = 48
    petal_proto_obj = create_petal_mesh(mat_white)
    
    for i in range(num_petals):
        angle = (2 * math.pi / num_petals) * i
        new_petal = bpy.data.objects.new(f"Petal_{i}", petal_proto_obj.data)
        bpy.context.collection.objects.link(new_petal)
        new_petal.rotation_euler[2] = angle
        # Offset from center to the edge of disk_radius=1.0
        new_petal.location = (math.cos(angle) * 1.0, math.sin(angle) * 1.0, 0)
    
    bpy.data.objects.remove(petal_proto_obj, do_unlink=True)

if __name__ == "__main__":
    main()
