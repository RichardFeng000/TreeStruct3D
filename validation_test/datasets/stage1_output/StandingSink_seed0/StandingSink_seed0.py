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
    # Basin Dimensions
    w, d, h = 0.75, 0.55, 0.22
    wall_thickness = 0.04
    corner_radius = 0.12
    
    bm = bmesh.new()
    # Create the main box
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale to basic dimensions
    for v in bm.verts:
        v.co.x *= (w / 2)
        v.co.y *= (d / 2)
        v.co.z *= (h / 2)
        
    # Flare the top edges slightly
    top_verts = [v for v in bm.verts if v.co.z > 0]
    for v in top_verts:
        v.co.x *= 1.08
        v.co.y *= 1.08

    # Round the vertical corners (the edges running along Z)
    vertical_edges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.1]
    bmesh.ops.bevel(bm, geom=vertical_edges, offset=corner_radius, segments=8, affect='EDGES')

    # Create the hollow bowl interior
    top_face = None
    for f in bm.faces:
        if f.normal.z > 0.9:
            top_face = f
            break
            
    if top_face:
        # Inset to create wall thickness
        res = bmesh.ops.inset_individual(bm, faces=[top_face], thickness=wall_thickness)
        inner_face = res['faces'][0]
        # Extrude down to form the bowl cavity
        bmesh.ops.translate(bm, verts=inner_face.verts, vec=(0, 0, -h + wall_thickness))
        
        # Bevel the inner bottom edges for a rounded bowl interior
        bottom_verts = [v for v in inner_face.verts]
        # Find edges at the bottom of the basin cavity
        inner_bottom_edges = [e for e in bm.edges if any(v in bottom_verts for v in e.verts)]
        bmesh.ops.bevel(bm, geom=inner_bottom_edges, offset=0.05, segments=4, affect='EDGES')

    mesh = bpy.data.meshes.new("BasinMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("Basin", mesh)
    bpy.context.collection.objects.link(obj)
    bm.free()
    
    # Position basin so the bottom is at Z=0 (roughly) and move it up to sit on pedestal
    obj.location.z = h / 2
    return obj

def create_pedestal():
    p_h = 0.85
    base_w = 0.45
    top_w = 0.22
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Initial scale for the column block
    for v in bm.verts:
        v.co.z *= (p_h / 2)
        v.co.x *= (base_w / 2)
        v.co.y *= (base_w / 2)

    # Taper the top inward
    top_verts = [v for v in bm.verts if v.co.z > 0]
    for v in top_verts:
        v.co.x *= (top_w / base_w)
        v.co.y *= (top_w / base_w)

    # Bevel the bottom edges for a cleaner transition to floor
    bottom_edges = [e for e in bm.edges if abs(e.verts[0].co.z - (-p_h/2)) < 0.01]
    bmesh.ops.bevel(bm, geom=bottom_edges, offset=0.02, segments=3, affect='EDGES')

    mesh = bpy.data.meshes.new("PedestalMesh")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new("Pedestal", mesh)
    bpy.context.collection.objects.link(obj)
    bm.free()
    
    # Place pedestal so top meets the bottom of the basin (which is at Z=0 relative to its local origin)
    # Basin height is 0.22, shifted by +0.11. Pedestal should be below it.
    obj.location.z = -p_h / 2
    return obj

def create_faucet():
    chrome_mat = create_material("Chrome", (0.85, 0.85, 0.9, 1), metallic=1.0, roughness=0.1)
    
    # Base Plate of the faucet
    bm_base = bmesh.new()
    bmesh.ops.create_cube(bm_base, size=1.0)
    for v in bm_base.verts:
        v.co.x *= 0.12; v.co.y *= 0.06; v.co.z *= 0.02
    mesh_b = bpy.data.meshes.new("FaucetBaseMesh")
    bm_base.to_mesh(mesh_b)
    obj_base = bpy.data.objects.new("FaucetBase", mesh_b)
    bpy.context.collection.objects.link(obj_base)
    # Position on the back edge of the basin (basin depth is 0.55, so y approx 0.27)
    obj_base.location = Vector((0, 0.23, 0.22)) 
    obj_base.data.materials.append(chrome_mat)
    bm_base.free()

    # Gooseneck pipe - created using a series of cylinders (via bmesh.ops.create_cone)
    segments = 12
    radius = 0.018
    segment_height = 0.04
    arc_radius = 0.12
    
    for i in range(segments):
        bm_seg = bmesh.new()
        # In BMesh, a cylinder is a cone with equal radius1 and radius2
        bmesh.ops.create_cone(bm_seg, cap_ends=True, segments=16, 
                              radius1=radius, radius2=radius, depth=segment_height)
        
        # Create mesh and object
        mesh_s = bpy.data.meshes.new(f"FaucetSegMesh_{i}")
        bm_seg.to_mesh(mesh_s)
        obj_s = bpy.data.objects.new(f"FaucetSeg_{i}", mesh_s)
        bpy.context.collection.objects.link(obj_s)
        
        # Calculate position and rotation for the arc
        angle = (i / segments) * (math.pi / 2)
        # Arc moves from vertical to horizontal, then slightly down? 
        # Let's do a simple gooseneck: Up -> Forward -> Down
        
        if i < segments // 2:
            # Vertical part
            offset_y = 0.0
            offset_z = (i * segment_height) + 0.25
            rot_x = 0
        else:
            # Curved/Forward part
            curve_idx = i - segments // 2
            curve_angle = (curve_idx / (segments // 2)) * (math.pi / 2)
            offset_y = math.sin(curve_angle) * arc_radius
            offset_z = (segments // 2 * segment_height) + 0.25 - (1 - math.cos(curve_angle)) * arc_radius
            rot_x = curve_angle

        obj_s.location = Vector((0, 0.23 + offset_y, offset_z))
        obj_s.rotation_euler[0] = rot_x
        obj_s.data.materials.append(chrome_mat)
        bm_seg.free()

    # Handles
    for side in [-1, 1]:
        bm_h = bmesh.new()
        bmesh.ops.create_cone(bm_h, cap_ends=True, segments=16, radius1=0.02, radius2=0.02, depth=0.08)
        mesh_h = bpy.data.meshes.new(f"HandleMesh_{side}")
        bm_h.to_mesh(mesh_h)
        obj_h = bpy.data.objects.new(f"Handle_{side}", mesh_h)
        bpy.context.collection.objects.link(obj_h)
        # Place handles on either side of the faucet base
        obj_h.location = Vector((side * 0.08, 0.23, 0.24))
        obj_h.data.materials.append(chrome_mat)
        bm_h.free()

def main():
    clear_scene()

    # Dark Forest Green glossy ceramic material
    # Very dark green with slight blue/black tint for depth
    ceramic_mat = create_material("ForestGreen", (0.01, 0.06, 0.03, 1), metallic=0.0, roughness=0.05)

    basin = create_basin()
    pedestal = create_pedestal()
    create_faucet()

    # Assign materials
    basin.data.materials.append(ceramic_mat)
    pedestal.data.materials.append(ceramic_mat)

    # Final Polish: Smooth shading and Subdivision Surface for the ceramic parts
    for obj in [basin, pedestal]:
        # Apply subdivision to make it look high-end and organic
        mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
        mod.levels = 2
        mod.render_levels = 3
        obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))

if __name__ == "__main__":
    main()
