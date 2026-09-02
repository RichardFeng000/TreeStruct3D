import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)

def create_material(name, color):
    """Creates a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_mushroom(name, position, scale=1.0, height_mult=1.0, cap_width_mult=1.0):
    """Procedurally creates a mushroom."""
    # Materials
    mat_stem = create_material(f"MatStem_{name}", (0.92, 0.88, 0.78, 1.0)) # Pale stem
    mat_cap = create_material(f"MatCap_{name}", (0.75, 0.55, 0.35, 1.0))   # Tan cap

    radius = 0.2 * scale
    height = 1.4 * scale * height_mult
    cap_radius = 0.6 * scale * cap_width_mult

    # --- STEM ---
    stem_mesh = bpy.data.meshes.new(f"StemMesh_{name}")
    stem_obj = bpy.data.objects.new(f"Stem_{name}", stem_mesh)
    bpy.context.collection.objects.link(stem_obj)

    bm_stem = bmesh.new()
    # Create cone centered at 0, then shift it up so base is at Z=0
    bmesh.ops.create_cone(bm_stem, cap_ends=True, segments=12, radius1=radius * 1.2, radius2=radius, depth=height)
    
    # Shift all vertices so the bottom of the stem starts at Z=0
    for v in bm_stem.verts:
        v.co.z += height / 2

    # Give stem more organic "texture" and bulge
    for v in bm_stem.verts:
        # General jitter
        v.co.x += random.uniform(-0.03, 0.03) * scale
        v.co.y += random.uniform(-0.03, 0.03) * scale
        # Organic bulge in middle
        z_norm = v.co.z / height
        bulge = math.sin(z_norm * math.pi) * 0.12 * scale
        v.co.x += bulge * (v.co.x / radius if radius != 0 else 1)
        v.co.y += bulge * (v.co.y / radius if radius != 0 else 1)

    bm_stem.to_mesh(stem_mesh)
    bm_stem.free()
    
    stem_obj.location = position
    stem_obj.active_material = mat_stem

    # --- CAP ---
    cap_mesh = bpy.data.meshes.new(f"CapMesh_{name}")
    cap_obj = bpy.data.objects.new(f"Cap_{name}", cap_mesh)
    bpy.context.collection.objects.link(cap_obj)

    bm_cap = bmesh.new()
    # Create a UV sphere for the cap (half)
    bmesh.ops.create_uvsphere(bm_cap, u_segments=32, v_segments=16, radius=cap_radius)
    
    # Flatten and remove bottom to make it a dome
    bottom_verts = [v for v in bm_cap.verts if v.co.z < -0.05]
    bmesh.ops.delete(bm_cap, geom=bottom_verts, context='VERTS')
    
    # Deform the cap to be broad and slightly wavy
    for v in bm_cap.verts:
        v.co.z *= 0.6 # Flatten Z for a "broad" look
        if abs(v.co.z) < 0.1: # Edge waviness
            angle = math.atan2(v.co.y, v.co.x)
            wave = 0.06 * scale * math.sin(angle * 7)
            v.co.x += wave * (v.co.x / cap_radius)
            v.co.y += wave * (v.co.y / cap_radius)

    bm_cap.to_mesh(cap_mesh)
    bm_cap.free()
    
    # Position cap exactly at the top of the stem
    cap_obj.location = (position[0], position[1], height + position[2])
    cap_obj.active_material = mat_cap

    # --- GILLS ---
    gills_mesh = bpy.data.meshes.new(f"GillsMesh_{name}")
    gills_obj = bpy.data.objects.new(f"Gills_{name}", gills_mesh)
    bpy.context.collection.objects.link(gills_obj)

    bm_gills = bmesh.new()
    gill_count = 24
    for i in range(gill_count):
        angle = (i / gill_count) * 2 * math.pi
        x1, y1 = math.cos(angle) * radius, math.sin(angle) * radius
        x2, y2 = math.cos(angle) * cap_radius, math.sin(angle) * cap_radius
        
        v1 = bm_gills.verts.new((x1, y1, 0))
        v2 = bm_gills.verts.new((x2, y2, 0))
        v3 = bm_gills.verts.new((x2, y2, -0.05 * scale))
        v4 = bm_gills.verts.new((x1, y1, -0.05 * scale))
        bm_gills.faces.new((v1, v2, v3, v4))

    bm_gills.to_mesh(gills_mesh)
    bm_gills.free()
    
    # Align gills under the cap and on top of stem
    gills_obj.location = (position[0], position[1], height + position[2])
    gills_obj.active_material = mat_stem

    return [stem_obj, cap_obj, gills_obj]

def create_shared_base():
    """Creates a small organic mound at the base."""
    base_mesh = bpy.data.meshes.new("BaseMesh")
    base_obj = bpy.data.objects.new("Base", base_mesh)
    bpy.context.collection.objects.link(base_obj)

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=1.0)
    
    # Flatten and roughen the mound
    for v in bm.verts:
        v.co.z *= 0.25
        v.co.x += random.uniform(-0.15, 0.15)
        v.co.y += random.uniform(-0.15, 0.15)

    bm.to_mesh(base_mesh)
    bm.free()
    
    mat_base = create_material("MatBase", (0.35, 0.25, 0.15, 1.0)) # Earthy brown
    base_obj.active_material = mat_base
    return base_obj

def main():
    clear_scene()

    # Shared Base
    create_shared_base()

    # Main large mushroom (dominant)
    create_mushroom(
        name="Main", 
        position=(0, 0, 0), 
        scale=1.2, 
        height_mult=1.0, 
        cap_width_mult=1.5
    )

    # Small companion 1 (medium height)
    create_mushroom(
        name="Companion1", 
        position=(0.6, 0.4, 0), 
        scale=0.7, 
        height_mult=0.8, 
        cap_width_mult=1.2
    )

    # Small companion 2 (short height)
    create_mushroom(
        name="Companion2", 
        position=(-0.5, -0.4, 0), 
        scale=0.5, 
        height_mult=0.6, 
        cap_width_mult=1.0
    )

if __name__ == "__main__":
    main()
