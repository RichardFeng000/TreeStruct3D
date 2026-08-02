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
    # Create a single petal geometry using BMesh
    mesh = bpy.data.meshes.new("PetalMesh")
    bm = bmesh.new()
    
    length = 3.0
    width = 0.4
    thickness = 0.02
    segments = 12
    
    # Generate the flat petal shape (tapered)
    verts = []
    for i in range(segments + 1):
        t = i / segments
        x = t * length
        w = math.sin(t * math.pi) * width
        verts.append(bm.verts.new((x, -w/2, 0)))
        verts.append(bm.verts.new((x, w/2, 0)))

    # Create faces for the surface
    for i in range(segments):
        v1 = verts[i*2]
        v2 = verts[i*2 + 1]
        v3 = verts[(i+1)*2 + 1]
        v4 = verts[(i+1)*2]
        bm.faces.new((v1, v2, v3, v4))

    # Extrude for thickness
    # bmesh.ops.extrude_face_region requires the geom to be a list of faces
    faces_to_extrude = bm.faces[:]
    res = bmesh.ops.extrude_face_region(bm, geom=faces_to_extrude)
    
    # Shift extruded vertices up by thickness
    verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in verts_extruded:
        v.co.z += thickness

    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Petal", mesh)
    obj.data.materials.append(material)
    return obj

def create_central_assembly(mat_tan):
    # Create the dome disk and all florets in one object for efficiency
    mesh = bpy.data.meshes.new("CentralDisk")
    bm = bmesh.new()
    
    # 1. The Dome Disk
    disk_radius = 1.0
    dome_height = 0.4
    
    # Create a semi-sphere (dome) using BMesh primitive
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=disk_radius)
    
    # Remove bottom half of the sphere to make it a dome
    verts_to_del = [v for v in bm.verts if v.co.z < -0.01]
    bmesh.ops.delete(bm, geom=verts_to_del, context='VERTS')
    
    # Scale the Z axis to flatten the dome
    for v in bm.verts:
        v.co.z *= dome_height

    # 2. The Florets (small cylinders on surface)
    num_florets = 500
    floret_radius = 0.04
    floret_height = 0.1
    
    phi = math.pi * (3.0 - 1.0) # Golden angle approx
    for i in range(num_florets):
        # Distribution on a hemisphere
        y_norm = 1.0 - (i / float(num_florets - 1)) * 2.0 # map to [1, -1]
        # We want just the top half of the sphere coords
        # So we use i from 0 to num_florets mapping to z from dome_height down to 0
        t = i / float(num_florets)
        z_coord = dome_height * (1.0 - t)
        radius_at_z = disk_radius * math.sqrt(1.0 - (z_coord/dome_height)**2)
        theta = phi * i
        
        x_coord = math.cos(theta) * radius_at_z
        y_coord = math.sin(theta) * radius_at_z
        
        pos = Vector((x_coord, y_coord, z_coord))
        normal = Vector((x_coord, y_coord, z_coord * 2.5)).normalized() # roughly normal to dome surface
        
        # Create a small cylinder for the floret
        # Since creating hundreds of cylinders via ops is slow, we manually add vertices/faces
        # Or use bmesh.ops.create_cylinder if available (available in Blender)
        matrix = Vector((0, 0, 1)).rotation_difference(normal)
        
        # Local offsets for a simple cylinder approximation (6 sides)
        sides = 6
        local_verts = []
        for s in range(sides):
            angle = (2 * math.pi / sides) * s
            vx = math.cos(angle) * floret_radius
            vy = math.sin(angle) * floret_radius
            # Base vertex
            v_base = bm.verts.new((0, 0, 0)) # Temporary pos
            # Top vertex
            v_top = bm.verts.new((0, 0, 0))  # Temporary pos
            local_verts.append((v_base, v_top))

        # Position the floret vertices relative to normal and surface position
        for s in range(sides):
            angle = (2 * math.pi / sides) * s
            vx = math.cos(angle) * floret_radius
            vy = math.sin(angle) * floret_radius
            
            # Local to Global rotation transformation
            v_base_local = Vector((vx, vy, 0))
            v_top_local = Vector((vx, vy, floret_height))
            
            # Rotate local coords by the normal-based rotation
            rot_mat = matrix.to_matrix()
            
            # Set final coordinates (shifting base to surface)
            local_verts[s][0].co = pos + rot_mat @ v_base_local
            local_verts[s][1].co = pos + rot_mat @ v_top_local

        # Create faces for the floret cylinder
        for s in range(sides):
            v1b = local_verts[s][0]
            v1t = local_verts[s][1]
            v2b = local_verts[(s+1)%sides][0]
            v2t = local_verts[(s+1)%sides][1]
            bm.faces.new((v1b, v2b, v2t, v1t))
        
        # Caps for the floret
        base_face_verts = [lv[0] for lv in local_verts]
        top_face_verts = [lv[1] for lv in local_verts]
        bm.faces.new(base_face_verts)
        bm.faces.new(top_face_verts)

    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("CentralDisk", mesh)
    obj.data.materials.append(mat_tan)
    return obj

def main():
    clear_scene()
    
    # Materials
    mat_white = create_material("WhitePetal", (1.0, 1.0, 1.0, 1.0))
    mat_tan = create_material("TanFloret", (0.8, 0.6, 0.4, 1.0))
    
    # Create Central Assembly
    disk_obj = create_central_assembly(mat_tan)
    bpy.context.collection.objects.link(disk_obj)
    
    # Create Petals
    num_petals = 42
    petal_proto_obj = create_petal_mesh(mat_white)
    
    # We use the proto to get a copy of the mesh data for each petal
    for i in range(num_petals):
        angle = (2 * math.pi / num_petals) * i
        
        new_petal = bpy.data.objects.new(f"Petal_{i}", petal_proto_obj.data)
        bpy.context.collection.objects.link(new_petal)
        
        # Rotate and translate to radiate from the center disk
        new_petal.rotation_euler[2] = angle
        
        # Start petal at the edge of the disk (radius 1.0)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        new_petal.location = (cos_a * 1.0, sin_a * 1.0, 0)
    
    # Cleanup the prototype object if it was linked or just remove mesh if needed
    # We didn't link petal_proto_obj to the collection, but we should clear it from data if unused
    bpy.data.objects.remove(petal_proto_obj, do_unlink=True)

if __name__ == "__main__":
    main()
