import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    # Clear data blocks to avoid duplication/clutter
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
    
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    # Muted olive-brown: Olive-greenish brown (low saturation)
    node_bsdf.inputs['Base Color'].default_value = (0.28, 0.32, 0.18, 1.0)
    node_bsdf.inputs['Roughness'].default_value = 0.95
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_moss_fragment():
    """Constructs the moss fragment geometry procedurally."""
    # Parameters for the crescent wedge
    outer_radius = 1.0
    inner_radius = 0.5
    base_height = 0.2
    segments = 64
    arc_angle = math.pi * 1.3 # Slightly more than semi-circle
    
    # Create mesh data block first (required for bm.to_mesh)
    mesh_data = bpy.data.meshes.new("MossMesh")
    bm = bmesh.new()
    
    # 1. Build the bottom crescent base
    outer_verts = []
    inner_verts = []
    
    for i in range(segments + 1):
        angle = (i / segments) * arc_angle - (arc_angle / 2)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        
        # Outer Arc
        ov = bm.verts.new(Vector((cos_a * outer_radius, sin_a * outer_radius, 0)))
        outer_verts.append(ov)
        
        # Inner Arc
        iv = bm.verts.new(Vector((cos_a * inner_radius, sin_a * inner_radius, 0)))
        inner_verts.append(iv)
    
    # Create base faces
    for i in range(segments):
        bm.faces.new((outer_verts[i], outer_verts[i+1], inner_verts[i+1], inner_verts[i]))
    
    # 2. Extrude upwards to create the volume
    bottom_faces = bm.faces[:]
    res = bmesh.ops.extrude_face_region(bm, geom=bottom_faces)
    extruded_geom = res['geom']
    extruded_verts = [v for v in extruded_geom if isinstance(v, bmesh.types.BMVert)]
    
    # Offset top vertices and add organic variation
    for v in extruded_verts:
        jitter = random.uniform(-0.08, 0.1)
        v.co.z += (base_height + jitter)
        
    # 3. Add "clumps" to the top surface for texture/detail
    bm.faces.ensure_lookup_table()
    top_faces = [f for f in bm.faces if f.normal.z > 0.8]
    
    # We pick a few faces to create small organic protrusions
    num_clumps = int(len(top_faces) * 0.3)
    target_faces = random.sample(top_faces, num_clumps)
    
    for f in target_faces:
        res_bump = bmesh.ops.extrude_face_region(bm, geom=[f])
        bump_verts = [v for v in res_bump['geom'] if isinstance(v, bmesh.types.BMVert)]
        
        center = f.calc_center_median()
        bump_h = random.uniform(0.05, 0.15)
        scale_f = random.uniform(0.3, 0.7)
        
        for v in bump_verts:
            v.co.z += bump_h
            # Pinch towards center to make it a blob rather than a pillar
            v.co.x = center.x + (v.co.x - center.x) * scale_f
            v.co.y = center.y + (v.co.y - center.y) * scale_f

    # 4. Transfer BMesh to Mesh data block
    bm.to_mesh(mesh_data)
    bm.free()
    
    # Create object and link it to the scene
    obj = bpy.data.objects.new("MossFragment", mesh_data)
    bpy.context.collection.objects.link(obj)
    
    # 5. Refine visual quality
    # Add Subdivision Surface for organic smoothness
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    # Smooth shading
    for poly in obj.data.polygons:
        poly.use_smooth = True

    return obj

def main():
    clear_scene()
    
    # Setup material
    moss_mat = create_moss_material()
    
    # Construct geometry
    fragment = create_moss_fragment()
    
    # Assign material to object
    fragment.data.materials.append(moss_mat)

if __name__ == "__main__":
    main()
