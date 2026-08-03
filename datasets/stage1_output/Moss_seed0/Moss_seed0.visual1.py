import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)

def create_moss_material():
    """Creates a muted olive-brown material."""
    mat = bpy.data.materials.new(name="MossMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Principled BSDF for realistic interaction
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    # Muted olive-brown: Darker, brownish-green. 
    # (R=0.32, G=0.30, B=0.18) provides a muddy, organic earth tone.
    node_bsdf.inputs['Base Color'].default_value = (0.32, 0.30, 0.18, 1.0)
    node_bsdf.inputs['Roughness'].default_value = 0.9
    node_bsdf.inputs['Specular IOR Level'].default_value = 0.1 # Low reflectivity for moss
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_moss_fragment():
    """Constructs the moss fragment geometry as a tapered curved wedge."""
    # Parameters for the crescent wedge
    outer_radius = 1.2
    inner_radius = 0.7
    max_height = 0.35
    segments = 64
    arc_angle = math.pi * 1.2 # Broad arc
    
    mesh_data = bpy.data.meshes.new("MossMesh")
    bm = bmesh.new()
    
    # 1. Build the bottom crescent base (Flat)
    outer_verts = []
    inner_verts = []
    
    for i in range(segments + 1):
        angle = (i / segments) * arc_angle - (arc_angle / 2)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        
        ov = bm.verts.new(Vector((cos_a * outer_radius, sin_a * outer_radius, 0)))
        outer_verts.append(ov)
        iv = bm.verts.new(Vector((cos_a * inner_radius, sin_a * inner_radius, 0)))
        inner_verts.append(iv)
    
    for i in range(segments):
        bm.faces.new((outer_verts[i], outer_verts[i+1], inner_verts[i+1], inner_verts[i]))
    
    # 2. Extrude and Taper height for "Wedge" shape
    bottom_faces = bm.faces[:]
    res = bmesh.ops.extrude_face_region(bm, geom=bottom_faces)
    extruded_geom = res['geom']
    extruded_verts = [v for v in extruded_geom if isinstance(v, bmesh.types.BMVert)]
    
    # Taper height based on position along the arc (highest in center, lowest at ends)
    for v in extruded_verts:
        # Calculate angle of the vertex relative to origin to determine its place in the crescent
        angle = math.atan2(v.co.y, v.co.x)
        # Normalize angle from -arc_angle/2 to arc_angle/2
        dist_from_center = abs(angle if abs(angle) < math.pi else (angle - 2*math.pi if angle > 0 else angle + 2*math.pi))
        
        # Weight is 1.0 at center, 0.3 at edges
        taper = max(0.3, 1.0 - (dist_from_center / (arc_angle/2)) * 0.7)
        jitter = random.uniform(-0.05, 0.05)
        v.co.z += (max_height * taper) + jitter
        
    # 3. Add organic clumps to top surface
    bm.faces.ensure_lookup_table()
    top_faces = [f for f in bm.faces if f.normal.z > 0.7]
    
    num_clumps = int(len(top_faces) * 0.4)
    target_faces = random.sample(top_faces, num_clumps)
    
    for f in target_faces:
        res_bump = bmesh.ops.extrude_face_region(bm, geom=[f])
        bump_verts = [v for v in res_bump['geom'] if isinstance(v, bmesh.types.BMVert)]
        
        center = f.calc_center_median()
        bump_h = random.uniform(0.08, 0.2)
        scale_f = random.uniform(0.4, 0.6)
        
        for v in bump_verts:
            v.co.z += bump_h
            # Pinch into a soft organic blob
            v.co.x = center.x + (v.co.x - center.x) * scale_f
            v.co.y = center.y + (v.co.y - center.y) * scale_f

    bm.to_mesh(mesh_data)
    bm.free()
    
    obj = bpy.data.objects.new("MossFragment", mesh_data)
    bpy.context.collection.objects.link(obj)
    
    # Smooth out the organic form
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    for poly in obj.data.polygons:
        poly.use_smooth = True

    return obj

def main():
    clear_scene()
    moss_mat = create_moss_material()
    fragment = create_moss_fragment()
    fragment.data.materials.append(moss_mat)

if __name__ == "__main__":
    main()
