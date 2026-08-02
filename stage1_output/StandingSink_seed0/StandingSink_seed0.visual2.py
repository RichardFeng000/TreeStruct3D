import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.1):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_basin():
    # Dimensions
    w, d, h = 0.7, 0.55, 0.2
    wall = 0.03
    radius = 0.1
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale to basic dimensions
    for v in bm.verts:
        v.co.x *= (w / 2)
        v.co.y *= (d / 2)
        v.co.z *= (h / 2)
        
    # Flare top vertices slightly
    top_verts = [v for v in bm.verts if v.co.z > 0]
    for v in top_verts:
        v.co.x *= 1.05
        v.co.y *= 1.05

    # Round the four vertical corners
    vertical_edges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.1]
    bmesh.ops.bevel(bm, geom=vertical_edges, offset=radius, segments=5, affect='EDGES')

    # Create the hollow bowl
    top_face = None
    for f in bm.faces:
        if f.normal.z > 0.9:
            top_face = f
            break
            
    if top_face:
        res = bmesh.ops.inset_individual(bm, faces=[top_face], thickness=wall)
        inner_face = res['faces'][0]
        # Extrude down to create the bowl interior
        bmesh.ops.translate(bm, verts=inner_face.verts, vec=(0, 0, -h + wall))
        
    mesh = bpy.data.meshes.new("BasinMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("Basin", mesh)
    bpy.context.collection.objects.link(obj)
    bm.free()
    # Shift object so the bottom is at Z=0
    obj.location.z = h / 2
    return obj

def create_pedestal():
    p_h = 0.8
    base_w = 0.45
    top_w = 0.2
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale Z for height and X/Y for base width
    for v in bm.verts:
        v.co.z *= (p_h / 2)
        v.co.x *= (base_w / 2)
        v.co.y *= (base_w / 2)

    # Taper the top vertices inward
    top_verts = [v for v in bm.verts if v.co.z > 0]
    for v in top_verts:
        v.co.x *= (top_w / base_w)
        v.co.y *= (top_w / base_w)

    mesh = bpy.data.meshes.new("PedestalMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("Pedestal", mesh)
    bpy.context.collection.objects.link(obj)
    bm.free()
    # Place pedestal so its top (Z=p_h/2) meets basin bottom (Z=0 relative to shifted origin)
    obj.location.z = -p_h / 2
    return obj

def create_faucet():
    chrome_mat = create_material("Chrome", (0.8, 0.8, 0.8, 1), metallic=1.0, roughness=0.05)
    
    # Base Plate
    bm_base = bmesh.new()
    bmesh.ops.create_cube(bm_base, size=1.0)
    for v in bm_base.verts:
        v.co.x *= 0.12; v.co.y *= 0.06; v.co.z *= 0.02
    mesh_b = bpy.data.meshes.new("FaucetBaseMesh")
    bm_base.to_mesh(mesh_b)
    obj_base = bpy.data.objects.new("FaucetBase", mesh_b)
    bpy.context.collection.objects.link(obj_base)
    obj_base.location = Vector((0, 0.2, 0.2)) # Top of basin height is 0.2
    obj_base.data.materials.append(chrome_mat)
    bm_base.free()

    # Gooseneck pipe (series of cylinders for a curve)
    segments = 8
    radius = 0.015
    current_pos = Vector((0, 0.2, 0.2))
    
    for i in range(segments):
        bm_seg = bmesh.new()
        bmesh.ops.create_cylinder(bm_seg, cap_ends=True, segments=16, radius=radius, depth=0.05)
        
        # Rotate and place segment to form an arc
        angle = (i / segments) * (math.pi / 2)
        mesh_s = bpy.data.meshes.new(f"SegMesh_{i}")
        bm_seg.to_mesh(mesh_s)
        obj_s = bpy.data.objects.new(f"FaucetSeg_{i}", mesh_s)
        bpy.context.collection.objects.link(obj_s)
        
        # Positioning logic for the arc
        offset_y = math.sin(angle) * 0.1
        offset_z = (i * 0.04) + 0.2
        obj_s.location = Vector((0, 0.2 + offset_y, offset_z))
        obj_s.rotation_euler[0] = angle # Tilt segment
        obj_s.data.materials.append(chrome_mat)
        bm_seg.free()

    # Handles
    for side in [-1, 1]:
        bm_h = bmesh.new()
        bmesh.ops.create_cube(bm_h, size=1.0)
        for v in bm_h.verts:
            v.co.x *= 0.04; v.co.y *= 0.04; v.co.z *= 0.08
        mesh_h = bpy.data.meshes.new(f"HandleMesh_{side}")
        bm_h.to_mesh(mesh_h)
        obj_h = bpy.data.objects.new(f"Handle_{side}", mesh_h)
        bpy.context.collection.objects.link(obj_h)
        obj_h.location = Vector((side * 0.08, 0.2, 0.24))
        obj_h.data.materials.append(chrome_mat)
        bm_h.free()

def main():
    clear_scene()

    # Dark Forest Green glossy ceramic
    ceramic_mat = create_material("ForestGreen", (0.01, 0.08, 0.03, 1), metallic=0.0, roughness=0.05)

    basin = create_basin()
    pedestal = create_pedestal()
    create_faucet()

    basin.data.materials.append(ceramic_mat)
    pedestal.data.materials.append(ceramic_mat)

    # Smoothing and Subdivision for a professional look
    for obj in [basin, pedestal]:
        mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
        mod.levels = 2
        mod.render_levels = 3
        obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))

if __name__ == "__main__":
    main()
