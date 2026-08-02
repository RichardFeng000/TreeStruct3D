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

def create_star_coral():
    clear_scene()

    # Colors
    beige_color = (0.85, 0.78, 0.65, 1.0) # Sandy beige
    cream_color = (0.98, 0.96, 0.90, 1.0) # Pale cream

    mat_base = create_material("CoralBase", beige_color)
    mat_polyp = create_material("PolypTip", cream_color)

    # Base boulder parameters
    radius = 4.0
    res = 64
    
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=res, v_segments=res, radius=radius)
    
    # Flatten the bottom to make a base
    bottom_verts = [v for v in bm.verts if v.co.z < -0.2]
    for v in bottom_verts:
        v.co.z = -0.2

    # Organic surface irregularity (applied before polyps)
    for v in bm.verts:
        if v.co.z > -0.1:
            noise = (random.random() - 0.5) * 0.3
            v.co += v.normal * noise

    # Fill base hole logic is handled by the flattened vertices mostly, 
    # but we ensure a solid manifold object
    
    # Polyps distribution
    num_polyps = 450
    phi = math.pi * (3.0 - 1.0) # Golden angle
    
    for i in range(num_polyps):
        y = 1 - (i / float(num_polyps - 1)) * 2
        rad = math.sqrt(max(0, 1 - y * y))
        theta = phi * i
        
        x = math.cos(theta) * rad
        z = math.sin(theta) * rad
        
        # Position on dome (only upper hemisphere and slightly above base)
        pos = Vector((x * radius, z * radius, y * radius))
        if pos.z < -0.1:
            continue
        
        # Normal for the polyp orientation
        normal = pos.normalized()
        
        # --- Create Polyp Geometry ---
        # Local coordinate system
        up = Vector((0, 0, 1)) if abs(normal.z) < 0.9 else Vector((0, 1, 0))
        tangent = up.cross(normal).normalized()
        bitangent = normal.cross(tangent).normalized()
        
        # Polyp Central Mound (the 'cup')
        mound_r = 0.25
        mound_h = 0.15
        segments = 8
        center_v = bm.verts.new(pos + normal * 0.05)
        ring_vs = []
        for s in range(segments):
            angle = (2 * math.pi / segments) * s
            v_pos = pos + (tangent * math.cos(angle) + bitangent * math.sin(angle)) * mound_r
            ring_vs.append(bm.verts.new(v_pos))
        
        for s in range(segments):
            bm.faces.new((center_v, ring_vs[s], ring_vs[(s+1)%segments]))

        # Radiating Filaments (tentacles)
        tentacle_count = 12
        t_len = 0.5
        t_rad = 0.04
        for t in range(tentacle_count):
            angle = (2 * math.pi / tentacle_count) * t
            dir_vec = (tangent * math.cos(angle) + bitangent * math.sin(angle)).normalized()
            
            # Filaments curve slightly outward and upward from the dome normal
            start_p = pos + normal * 0.1
            end_p = start_p + dir_vec * t_len + normal * 0.3
            
            # Create small cone for each tentacle
            tip_v = bm.verts.new(end_p)
            t_up = dir_vec if abs(dir_vec.z) < 0.9 else Vector((0,1,0))
            t_tan = t_up.cross(normal).normalized()
            t_bitan = normal.cross(t_tan).normalized()
            
            t_ring_vs = []
            for r in range(6):
                ra = (2 * math.pi / 6) * r
                rv_pos = start_p + (t_tan * math.cos(ra) + t_bitan * math.sin(ra)) * t_rad
                t_ring_vs.append(bm.verts.new(rv_pos))
            
            for r in range(6):
                bm.faces.new((t_ring_vs[r], t_ring_vs[(r+1)%6], tip_v))

    # Finalize Mesh
    mesh = bpy.data.meshes.new("StarCoral")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("StarCoral", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Material assignment: 
    # We assign the base material to all, then polyp tips specifically if possible.
    # For simplicity in a single-mesh script, we'll apply based on Z height or use one beige base.
    obj.data.materials.append(mat_base)
    obj.data.materials.append(mat_polyp)
    
    # Assign materials to polygons (Base vs Polyp tips)
    for poly in mesh.polygons:
        # Calculate centroid of face to decide material
        centroid = Vector((sum((v.co for v in poly.vertices), Vector((0,0,0)))) / len(poly.vertices))
        if centroid.length() > radius * 0.95: # Simple heuristic for polyp tips
            poly.material_index = 1
        else:
            poly.material_index = 0

    # Smooth shading
    for poly in mesh.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    create_star_coral()
