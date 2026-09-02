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
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Base Color'].default_value = color
    # Set some basic glass/plastic properties if needed, but Base Color is priority
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_bottle():
    # --- Parameters ---
    base_radius = 0.6
    shoulder_radius = 0.45
    neck_radius = 0.18
    body_height = 2.0
    shoulder_height = 0.4
    neck_height = 0.7
    cap_height = 0.3
    cap_radius = 0.21
    label_z_start = 0.6
    label_height = 0.6
    label_offset = 0.02

    # --- Bottle Body and Neck ---
    bm = bmesh.new()
    
    # Create base disk
    res = bmesh.ops.create_circle(bm, radius=base_radius, segments=32)
    verts_base = res['verts']
    bm.faces.new(verts_base) # Manual cap
    
    # 1. Body (Frustum: base -> shoulder)
    face_base = bm.faces[0]
    res_ext = bmesh.ops.extrude_face_region(bm, geom=[face_base])
    verts_shoulder_start = [v for v in res_ext['geom'] if isinstance(v, bmesh.types.Vert)]
    for v in verts_shoulder_start:
        v.co.z = body_height
        scale = shoulder_radius / base_radius
        v.co.x *= scale
        v.co.y *= scale

    # 2. Shoulder (Frustum: shoulder -> neck)
    face_shoulder = bm.faces[-1]
    res_ext = bmesh.ops.extrude_face_region(bm, geom=[face_shoulder])
    verts_neck_start = [v for v in res_ext['geom'] if isinstance(v, bmesh.types.Vert)]
    for v in verts_neck_start:
        v.co.z += shoulder_height
        scale = neck_radius / shoulder_radius
        v.co.x *= scale
        v.co.y *= scale

    # 3. Neck (Cylinder)
    face_neck = bm.faces[-1]
    res_ext = bmesh.ops.extrude_face_region(bm, geom=[face_neck])
    verts_top = [v for v in res_ext['geom'] if isinstance(v, bmesh.types.Vert)]
    for v in verts_top:
        v.co.z += neck_height

    # Create the mesh object
    bottle_mesh = bpy.data.meshes.new("BottleMesh")
    bm.to_mesh(bottle_mesh)
    obj_body = bpy.data.objects.new("BottleBody", bottle_mesh)
    bpy.context.collection.objects.link(obj_body)
    bm.free()

    # --- Cap ---
    cap_bm = bmesh.new()
    res_c = bmesh.ops.create_circle(cap_bm, radius=cap_radius, segments=32)
    verts_c = res_c['verts']
    cap_bm.faces.new(verts_c)
    
    face_c = cap_bm.faces[0]
    res_ext_c = bmesh.ops.extrude_face_region(cap_bm, geom=[face_c])
    verts_top_c = [v for v in res_ext_c['geom'] if isinstance(v, bmesh.types.Vert)]
    for v in verts_top_c:
        v.co.z = cap_height

    # Bevel the top edge to round it
    top_face = cap_bm.faces[-1]
    bmesh.ops.bevel(cap_bm, geom=top_face.edges, width=0.1, segments=8, affect='EDGES')
    
    cap_mesh = bpy.data.meshes.new("CapMesh")
    cap_bm.to_mesh(cap_mesh)
    obj_cap = bpy.data.objects.new("BottleCap", cap_mesh)
    bpy.context.collection.objects.link(obj_cap)
    # Position cap at the top of the neck
    obj_cap.location.z = body_height + shoulder_height + neck_height
    cap_bm.free()

    # --- Label Band ---
    label_bm = bmesh.new()
    
    # Calculate radii for label band based on bottle's conical shape
    def get_radius_at(z):
        if z <= body_height:
            return base_radius - (base_radius - shoulder_radius) * (z / body_height)
        else:
            return shoulder_radius - (shoulder_radius - neck_radius) * ((z - body_height) / shoulder_height)

    r1 = get_radius_at(label_z_start) + label_offset
    res_l = bmesh.ops.create_circle(label_bm, radius=r1, segments=32)
    verts_l1 = res_l['verts']
    edges_l1 = res_l['edges']
    
    # Extrude the band (no cap for label, just a sleeve)
    res_ext_l = bmesh.ops.extrude_edge_region(label_bm, geom=edges_l1)
    verts_l2 = [v for v in res_ext_l['geom'] if isinstance(v, bmesh.types.Vert)]
    
    z2 = label_z_start + label_height
    r2 = get_radius_at(z2) + label_offset
    for v in verts_l2:
        v.co.z = label_height # local height relative to object origin
        scale = r2 / r1
        v.co.x *= scale
        v.co.y *= scale

    # Create faces for the band (bridge between circles)
    # The extrude_edge_region creates the quad faces automatically
    label_mesh = bpy.data.meshes.new("LabelMesh")
    label_bm.to_mesh(label_mesh)
    obj_label = bpy.data.objects.new("BottleLabel", label_mesh)
    bpy.context.collection.objects.link(obj_label)
    obj_label.location.z = label_z_start
    label_bm.free()

    # --- Materials and Colors ---
    glass_mat = create_material("Glass", (0.2, 0.7, 0.9, 1.0))
    cap_mat = create_material("CapPlastic", (0.8, 0.1, 0.1, 1.0))
    
    obj_body.data.materials.append(glass_mat)
    obj_cap.data.materials.append(cap_mat)

    # Colorful Label Pattern: assign different materials to face strips
    num_strips = 6
    label_mats = []
    for i in range(num_strips):
        color = (random.random(), random.random(), random.random(), 1.0)
        mat = create_material(f"LabelColor_{i}", color)
        label_mats.append(mat)
        obj_label.data.materials.append(mat)

    faces = obj_label.data.polygons
    if len(faces) > 0:
        for idx, face in enumerate(faces):
            # Distribute colors around the cylinder
            strip_idx = (idx // (len(faces)//num_strips)) % num_strips
            face.material_index = strip_idx

    # Final Smoothing and cleanup
    for obj in [obj_body, obj_cap]:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth()

def main():
    clear_scene()
    create_bottle()

if __name__ == "__main__":
    main()
