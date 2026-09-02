import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene of all objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material():
    """Creates a deep navy blue-gray material."""
    mat = bpy.data.materials.new(name="KnifeMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Deep navy blue-gray color (RGBA)
        bsdf.inputs['Base Color'].default_value = (0.05, 0.08, 0.15, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.3
        bsdf.inputs['Metallic'].default_value = 0.7
    return mat

def create_knife():
    """Procedurally generates the knife geometry with a seamless blend."""
    # Parameters
    handle_length = 5.0
    blade_length = 12.0
    transition_length = 1.5
    handle_width = 1.2
    handle_thickness = 0.8
    blade_base_width = 2.4
    blade_thickness = 0.12
    segments = 32

    mesh = bpy.data.meshes.new("Knife")
    obj = bpy.data.objects.new("Knife", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # --- Handle Generation ---
    verts = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        x = math.cos(angle) * handle_width * 0.5
        z = math.sin(angle) * handle_thickness * 0.5
        verts.append(bm.verts.new((x, 0, z)))
    
    # Create base face (the back of the handle)
    face = bm.faces.new(verts)

    # Extrude handle in Y direction
    handle_steps = 10
    last_face = face
    for s in range(handle_steps):
        res = bmesh.ops.extrude_face_region(bm, geom=[last_face])
        verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
        faces_extruded = [f for f in res['geom'] if isinstance(f, bmesh.types.BMFace)]
        for v in verts_extruded:
            v.co.y += handle_length / handle_steps
        last_face = faces_extruded[0]

    # --- Transition Generation (Handle to Blade) ---
    res = bmesh.ops.extrude_face_region(bm, geom=[last_face])
    verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    faces_extruded = [f for f in res['geom'] if isinstance(f, bmesh.types.BMFace)]
    
    for v in verts_extruded:
        v.co.y += transition_length
        # Calculate relative position in original ellipse to map to rectangle
        # Use a simple approximation for the blend
        # Find angle from center
        angle = math.atan2(v.co.z, v.co.x)
        # Map elliptical shape to a flatter wide rectangular shape
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        v.co.x = cos_a * (blade_base_width * 0.5)
        v.co.z = sin_a * (blade_thickness * 0.5)

    last_face = faces_extruded[0]

    # --- Blade Generation ---
    blade_steps = 24
    for s in range(blade_steps):
        res = bmesh.ops.extrude_face_region(bm, geom=[last_face])
        verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
        faces_extruded = [f for f in res['geom'] if isinstance(f, bmesh.types.BMFace)]
        
        progress = (s + 1) / blade_steps
        step_y = blade_length / blade_steps
        
        for v in verts_extruded:
            v.co.y += step_y
            # Taper width linearly to point
            taper = 1.0 - progress
            v.co.x *= taper
            # Slightly thin the thickness as well
            v.co.z *= (0.8 + 0.2 * taper)
        
        last_face = faces_extruded[0]

    # --- Closing the Tip ---
    # Merge all vertices at the end of the blade into one point
    tip_verts = [v for v in bm.verts if v.co.y >= (handle_length + transition_length + blade_length - 0.1)]
    if tip_verts:
        center_pt = Vector((0, max(v.co.y for v in tip_verts), 0))
        for v in tip_verts:
            v.co = center_pt
        # Use remove_doubles as the correct BMesh operator to merge vertices at same location
        bmesh.ops.remove_doubles(bm, verts=tip_verts, dist=0.01)

    bm.to_mesh(mesh)
    bm.free()

    # Center object at origin
    bbox_min = Vector((min(v.co.x for v in mesh.vertices), 
                      min(v.co.y for v in mesh.vertices), 
                      min(v.co.z for v in mesh.vertices)))
    bbox_max = Vector((max(v.co.x for v in mesh.vertices), 
                      max(v.co.y for v in mesh.vertices), 
                      max(v.co.z for v in mesh.vertices)))
    center = (bbox_min + bbox_max) / 2
    obj.location = -center

    # Smooth the geometry with subdivision
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    
    for poly in mesh.polygons:
        poly.use_smooth = True

    return obj

if __name__ == "__main__":
    clear_scene()
    knife_obj = create_knife()
    knife_mat = create_material()
    if knife_obj.data.materials:
        knife_obj.data.materials[0] = knife_mat
    else:
        knife_obj.data.materials.append(knife_mat)
