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
    # Muted olive-brown: (R=0.32, G=0.35, B=0.2) provides a natural earthy tone.
    node_bsdf.inputs['Base Color'].default_value = (0.32, 0.35, 0.2, 1.0)
    node_bsdf.inputs['Roughness'].default_value = 0.95
    node_bsdf.inputs['Specular IOR Level'].default_value = 0.05
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_moss_fragment():
    """Constructs the moss fragment as a rounded, organic curved wedge."""
    # Dimensions for the crescent shape
    outer_radius = 1.2
    inner_radius = 0.6
    max_height = 0.4
    segments = 64
    arc_angle = math.pi * 1.3  # Wide arc
    
    mesh_data = bpy.data.meshes.new("MossMesh")
    bm = bmesh.new()
    
    # Create a flat base crescent
    outer_verts = []
    inner_verts = []
    
    for i in range(segments + 1):
        angle = (i / segments) * arc_angle - (arc_angle / 2)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        ov = bm.verts.new(Vector((cos_a * outer_radius, sin_a * outer_radius, 0)))
        outer_verts.append(ov)
        iv = bm.verts.new(Vector((cos_a * inner_radius, sin_a * inner_radius, 0)))
        inner_verts.append(iv)
    
    # Fill base faces
    for i in range(segments):
        bm.faces.new((outer_verts[i], outer_verts[i+1], inner_verts[i+1], inner_verts[i]))
    
    # Extrude to create height (forming the wedge volume)
    res = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    extruded_geom = res['geom']
    top_verts = [v for v in extruded_geom if isinstance(v, bmesh.types.BMVert)]
    
    # Apply organic shaping to the top surface
    for v in top_verts:
        # Distance from center of the arc (roughly)
        angle = math.atan2(v.co.y, v.co.x)
        if angle > math.pi/2: angle -= 2*math.pi
        if angle < -math.pi/2: angle += 2*math.pi
        
        # Wedge taper: highest in the middle, tapering to ends
        taper = max(0.1, 1.0 - abs(angle / (arc_angle/2)))
        
        # Add organic noise for "subtle surface variation"
        # Using random offsets that aren't as spikey as face extrusions
        noise = random.uniform(-0.08, 0.08)
        
        v.co.z = (max_height * taper) + noise
    
    bm.to_mesh(mesh_data)
    bm.free()
    
    obj = bpy.data.objects.new("MossFragment", mesh_data)
    bpy.context.collection.objects.link(obj)
    
    # Use Subdivision Surface to round the top edge and smooth out noise
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 3
    subsurf.render_levels = 3
    
    # Set shading to smooth
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
