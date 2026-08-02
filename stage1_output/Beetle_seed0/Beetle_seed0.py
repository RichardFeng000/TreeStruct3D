import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, color, roughness=0.1, metallic=0.0):
    """Creates a simple Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['Metallic'].default_value = metallic
    return mat

def create_beetle():
    # Materials
    mat_elytra = create_material("Mat_Elytra", (0.2, 0.01, 0.05, 1.0), roughness=0.1) # Burgundy
    mat_pattern = create_material("Mat_Pattern", (0.8, 0.0, 0.4, 1.0), roughness=0.2) # Magenta-pink
    mat_body = create_material("Mat_Body", (0.05, 0.03, 0.02, 1.0), roughness=0.3) # Dark brown
    mat_horns = create_material("Mat_Horns", (0.25, 0.08, 0.05, 1.0), roughness=0.1) # Glossy reddish-brown

    # --- BODY / ELYTRA ---
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0))
    body_obj = bpy.context.active_object
    body_obj.name = "Beetle_Body"
    body_obj.scale = (0.8, 1.5, 0.3)
    bpy.ops.object.transform_apply(scale=True)

    # Assign materials based on geometry logic
    body_obj.data.materials.append(mat_body)    # index 0: Thorax
    body_obj.data.materials.append(mat_elytra)  # index 1: Elytra base
    body_obj.data.materials.append(mat_pattern) # index 2: Patterns

    bm = bmesh.new()
    bm.from_mesh(body_obj.data)
    for face in bm.faces:
        center = face.calc_center_median()
        # Divide body into thorax (front) and elytra (back)
        if center.y < 0.3:
            face.material_index = 0 # Thorax
        else:
            # Organic swirling patterns on the elytra using math noise
            pattern_val = math.sin(center.x * 8 + center.y * 4) * math.cos(center.x * 3 - center.y * 7)
            if pattern_val > 0.5:
                face.material_index = 2 # Magenta patterns
            else:
                face.material_index = 1 # Burgundy elytra
    bm.to_mesh(body_obj.data)
    bm.free()

    # --- HEAD ---
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(0, -1.6, 0.1))
    head = bpy.context.active_object
    head.name = "Beetle_Head"
    head.scale = (0.8, 1.1, 0.7)
    bpy.ops.object.transform_apply(scale=True)
    head.data.materials.append(mat_body)

    # --- HORNS / MANDIBLES ---
    def create_horn(side):
        mesh = bpy.data.meshes.new(name=f"HornMesh_{side}")
        obj = bpy.data.objects.new(name=f"Horn_{side}", object_data=mesh)
        bpy.context.collection.objects.link(obj)
        
        bm = bmesh.new()
        segments = 15
        rings = []
        radius_start = 0.07
        radius_end = 0.02
        
        # Define path for the horn (curved projecting forward)
        for i in range(segments):
            t = i / (segments - 1)
            # Position: slightly out, then far forward, then curving back/up
            x = side * (0.15 + t * 0.3 * math.sin(t * math.pi))
            y = -1.7 - t * 0.8
            z = 0.1 + t * 0.4 * math.sin(t * math.pi)
            
            pos = Vector((x, y, z))
            radius = radius_start * (1.0 - t * 0.7)
            
            # Create ring of vertices
            ring = []
            res = 8
            # Calculate local orientation for the ring
            forward = Vector((0, -1, 0)) # simplified tangent
            right = Vector((side, 0, 0))
            up = right.cross(forward).normalized()
            
            for j in range(res):
                angle = (2 * math.pi / res) * j
                offset = (right * math.cos(angle) + up * math.sin(angle)) * radius
                ring.append(bm.verts.new(pos + offset))
            rings.append(ring)

        # Bridge rings into faces
        for i in range(segments - 1):
            r1 = rings[i]
            r2 = rings[i+1]
            for j in range(res):
                bm.faces.new((r1[j], r1[(j+1)%res], r2[(j+1)%res], r2[j]))

        # Cap the ends
        bm.faces.new(rings[0]) # Base (though usually hidden by head)
        bm.faces.new(rings[-1]) # Tip
        
        bm.to_mesh(mesh)
        bm.free()
        obj.data.materials.append(mat_horns)
        return obj

    create_horn(1)
    create_horn(-1)

    # --- LEGS ---
    def create_leg(side, index):
        # side: 1 or -1, index: 0 (front), 1 (mid), 2 (back)
        mesh = bpy.data.meshes.new(name=f"LegMesh_{side}_{index}")
        obj = bpy.data.objects.new(name=f"Leg_{side}_{index}", object_data=mesh)
        bpy.context.collection.objects.link(obj)

        bm = bmesh.new()
        # Joint positions relative to beetle center
        # Leg start: x is wide, y depends on index, z near bottom of body
        start_x = side * 0.65
        start_y = -0.6 + (index * 0.7)
        start_z = 0.1
        
        joints = [
            Vector((start_x, start_y, start_z)),
            Vector((side * 1.0, start_y - 0.2 if index==0 else start_y + 0.1, -0.1)), # Coxa -> Femur
            Vector((side * 1.2, start_y + (index-1)*0.4, -0.4)),                   # Femur -> Tibia
            Vector((side * 1.1, start_y + (index-1)*0.4 + 0.3, -0.8))              # Tibia -> Tarsus/Tip
        ]

        res = 8
        prev_ring = None
        
        for i in range(len(joints) - 1):
            p1 = joints[i]
            p2 = joints[i+1]
            radius1 = 0.08 * (1.0 - i * 0.2)
            radius2 = 0.06 * (1.0 - (i + 1) * 0.2) if i < 2 else 0.01 # Taper to point
            
            # Direction for the cylinder segment
            dir_vec = (p2 - p1).normalized()
            ortho_x = Vector((1, 0, 0)) if abs(dir_vec.x) < 0.9 else Vector((0, 1, 0))
            right = dir_vec.cross(ortho_x).normalized()
            up = dir_vec.cross(right).normalized()

            # Create ring at p1 and p2
            r1 = []
            for j in range(res):
                angle = (2 * math.pi / res) * j
                off = (right * math.cos(angle) + up * math.sin(angle)) * radius1
                r1.append(bm.verts.new(p1 + off))
            
            r2 = []
            for j in range(res):
                angle = (2 * math.pi / res) * j
                off = (right * math.cos(angle) + up * math.sin(angle)) * radius2
                r2.append(bm.verts.new(p2 + off))

            # Connect rings
            for j in range(res):
                bm.faces.new((r1[j], r1[(j+1)%res], r2[(j+1)%res], r2[j]))
            
            prev_ring = r2

        # Cap the tip
        if prev_ring:
            bm.faces.new(prev_ring)

        bm.to_mesh(mesh)
        bm.free()
        obj.data.materials.append(mat_body)

    for s in [-1, 1]:
        for idx in range(3):
            create_leg(s, idx)

clear_scene()
create_beetle()
