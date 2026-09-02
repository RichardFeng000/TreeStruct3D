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
        bsdf.inputs['Base Color'].default_value = (0.08, 0.12, 0.18, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.3
        bsdf.inputs['Metallic'].default_value = 0.6
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
    blade_thickness = 0.1
    segments = 32

    mesh = bpy.data.meshes.new("Knife")
    obj = bpy.data.objects.new("Knife", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # --- Handle Generation ---
    # Initial profile (ellipse)
    verts = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        x = math.cos(angle) * handle_width * 0.5
        z = math.sin(angle) * handle_thickness * 0.5
        verts.append(bm.verts.new((x, 0, z)))
    
    # Create base face
    face = bm.faces.new(verts)

    # Extrude handle
    handle_steps = 10
    for s in range(handle_steps):
        current_face = [f for f in bm.faces if f.normal.y > 0.9]
        res = bmesh.ops.extrude_face_region(bm, geom=current_face)
        verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
        for v in verts_extruded:
            v.co.y += handle_length / handle_steps

    # --- Transition Generation (Handle to Blade) ---
    current_face = [f for f in bm.faces if f.normal.y > 0.9]
    res = bmesh.ops.extrude_face_region(bm, geom=current_face)
    verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    
    for v in verts_extruded:
        v.co.y += transition_length
        # Interpolate handle ellipse to blade rectangle profile
        # We map the circle points to a flatter wide rectangle
        old_x = v.co.x / (handle_width * 0.5) if handle_width != 0 else 0
        old_z = v.co.z / (handle_thickness * 0.5) if handle_thickness != 0 else 0
        
        # Blend logic: widen X and flatten Z
        v.co.x = old_x * (blade_base_width * 0.5)
        v.co.z = old_z * (blade_thickness * 0.5)

    # --- Blade Generation ---
    blade_steps = 20
    for s in range(blade_steps):
        current_face = [f for f in bm.faces if f.normal.y > 0.9]
        res = bmesh.ops.extrude_face_region(bm, geom=current_face)
        verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
        
        progress = (s + 1) / blade_steps
        step_y = blade_length / blade_steps
        
        for v in verts_extruded:
            v.co.y += step_y
            # Taper the width to a point linearly
            taper = 1.0 - progress
            v.co.x *= taper
            # Keep thickness very thin, but can taper slightly as well
            v.co.z *= (0.5 + 0.5 * taper)

    # --- Closing the Tip ---
    # Instead of bmesh.ops.collapse, we move all vertices to a single point and merge them
    max_y = max(v.co.y for v in bm.verts)
    tip_verts = [v for v in bm.verts if v.co.y >= max_y - 0.01]
    if tip_verts:
        # Center the tip vertices at a single coordinate
        center_pt = Vector((0, max_y, 0))
        for v in tip_verts:
            v.co = center_pt
        # Merge them into one vertex to create a clean point
        bmesh.ops.merge_verts(bm, verts=tip_verts)

    bm.to_mesh(mesh)
    bm.free()

    # Center the object at origin
    bbox_min = Vector((min(v.co.x for v in mesh.vertices), 
                      min(v.co.y for v in mesh.vertices), 
                      min(v.co.z for v in mesh.vertices)))
    bbox_max = Vector((max(v.co.x for v in mesh.vertices), 
                      max(v.co.y for v in mesh.vertices), 
                      max(v.co.z for v in mesh.vertices)))
    center = (bbox_min + bbox_max) / 2
    obj.location = -center

    # Smooth the geometry
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
