import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.7
    return mat

def generate_durian():
    clear_scene()

    # --- Parameters ---
    body_radius = 1.0
    body_stretch_z = 1.2  # Ovoid shape (slightly elongated)
    num_spines = 1800
    spine_base_rad = 0.035
    spine_height = 0.14
    spine_sides = 6
    stem_radius = 0.07
    stem_height = 0.35

    # --- Materials ---
    mat_body = create_material("DurianBody", (0.6, 0.7, 0.2, 1.0)) # Pale yellow-green
    mat_stem = create_material("DurianStem", (0.4, 0.3, 0.2, 1.0))  # Tan-brown

    # --- Body Construction ---
    bpy.ops.mesh.primitive_uv_sphere_add(radius=body_radius, segments=64, ring_count=32)
    body_obj = bpy.context.active_object
    body_obj.name = "Durian_Body"
    body_obj.scale = (1.0, 1.0, body_stretch_z)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    body_obj.data.materials.append(mat_body)

    # --- Spines Construction ---
    spines_bm = bmesh.new()
    
    for i in range(num_spines):
        # Fibonacci Spiral for uniform distribution on unit sphere
        phi = math.acos(1 - 2 * (i + 0.5) / num_spines)
        theta = math.pi * (1 + 5**0.5) * (i + 0.5)
        
        # Unit sphere point
        ux = math.cos(theta) * math.sin(phi)
        uy = math.sin(theta) * math.sin(phi)
        uz = math.cos(phi)
        
        # Scale to match body ellipsoid (x, y, z*S_z)
        pos = Vector((ux, uy, uz * body_stretch_z))
        
        # Ellipsoid Normal: gradient of f(x,y,z) = x^2 + y^2 + (z/S)^2 - 1
        # Grad = (2x, 2y, 2z/S^2)
        normal = Vector((ux, uy, uz / (body_stretch_z**2))).normalized()
        
        # Create a local orthonormal basis for the spine base
        # Find an arbitrary vector not parallel to normal
        temp_vec = Vector((0, 0, 1)) if abs(normal.z) < 0.9 else Vector((1, 0, 0))
        tangent = normal.cross(temp_vec).normalized()
        bitangent = normal.cross(tangent).normalized()
        
        # Create pyramid base vertices
        spine_verts = []
        for s in range(spine_sides):
            angle = (2 * math.pi * s) / spine_sides
            vx = pos + (math.cos(angle) * tangent + math.sin(angle) * bitangent) * spine_base_rad
            spine_verts.append(spines_bm.verts.new(vx))
        
        # Create pyramid tip vertex
        tip_pos = pos + normal * spine_height
        tip_v = spines_bm.verts.new(tip_pos)
        
        # Create faces for the pyramid sides
        for s in range(spine_sides):
            v1 = spine_verts[s]
            v2 = spine_verts[(s + 1) % spine_sides]
            spines_bm.faces.new((v1, v2, tip_v))
            
        # Create base face (to seal the geometry)
        try:
            spines_bm.faces.new(spine_verts)
        except ValueError:
            pass # BMesh might complain if face already exists or vertices are collinear

    # Finalize spines mesh
    spine_mesh = bpy.data.meshes.new("SpinesMesh")
    spines_bm.to_mesh(spine_mesh)
    spines_bm.free()
    spine_obj = bpy.data.objects.new("Durian_Spines", spine_mesh)
    bpy.context.collection.objects.link(spine_obj)
    spine_obj.data.materials.append(mat_body)

    # --- Stem Construction ---
    stem_bm = bmesh.new()
    segments = 12
    base_verts = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        v = stem_bm.verts.new((math.cos(angle) * stem_radius, math.sin(angle) * stem_radius, 0))
        base_verts.append(v)
    
    top_verts = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        # Slightly taper and add organic jitter
        r_tip = stem_radius * 0.6 + random.uniform(-0.01, 0.01)
        off_x = random.uniform(-0.02, 0.02)
        off_y = random.uniform(-0.02, 0.02)
        v = stem_bm.verts.new((math.cos(angle) * r_tip + off_x, math.sin(angle) * r_tip + off_y, stem_height))
        top_verts.append(v)
    
    for i in range(segments):
        v1 = base_verts[i]
        v2 = base_verts[(i + 1) % segments]
        v3 = top_verts[(i + 1) % segments]
        v4 = top_verts[i]
        stem_bm.faces.new((v1, v2, v3, v4))
    
    # Caps
    stem_bm.faces.new(base_verts)
    stem_bm.faces.new(reversed(top_verts))

    stem_mesh = bpy.data.meshes.new("StemMesh")
    stem_bm.to_mesh(stem_mesh)
    stem_bm.free()
    stem_obj = bpy.data.objects.new("Durian_Stem", stem_mesh)
    bpy.context.collection.objects.link(stem_obj)
    stem_obj.data.materials.append(mat_stem)
    
    # Position stem at the top of the body ovoid
    # The sphere is radius 1, scaled by stretch_z on Z axis. Center is origin.
    # Top point is (0, 0, body_radius * body_stretch_z)
    stem_obj.location = (0, 0, body_radius * body_stretch_z)

if __name__ == "__main__":
    generate_durian()
