import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clear default Blender objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.1, specular=1.0):
    """Create a principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_bsdf.inputs['Base Color'].default_value = color
    node_bsdf.inputs['Roughness'].default_value = roughness
    # Specular IOR Level for Blender 4.0+
    if 'Specular IOR Level' in node_bsdf.inputs:
        node_bsdf.inputs['Specular IOR Level'].default_value = specular
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_sphere(name, position, radius, material):
    """Create a sphere mesh."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, 
        location=position, 
        segments=12, 
        ring_count=6
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    # Smooth shading for glossy look
    bpy.ops.object.shade_smooth()
    return obj

def create_stem(material):
    """Create a tapered, slightly curved stem."""
    mesh = bpy.data.meshes.new("Stem")
    obj = bpy.data.objects.new("Stem", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    segments = 8
    rings = 12
    radius_bottom = 0.07
    radius_top = 0.04
    height = 0.5
    
    for i in range(rings + 1):
        t = i / rings
        z = t * height
        r = radius_bottom - (radius_bottom - radius_top) * t
        # Organic curve
        offset_x = 0.08 * math.sin(t * math.pi)
        offset_y = 0.05 * math.cos(t * math.pi)
        
        for j in range(segments):
            angle = (j / segments) * 2 * math.pi
            x = offset_x + r * math.cos(angle)
            y = offset_y + r * math.sin(angle)
            bm.verts.new((x, y, z))
    
    bm.verts.ensure_lookup_table()
    for i in range(rings):
        for j in range(segments):
            v1 = bm.verts[i * segments + j]
            v2 = bm.verts[i * segments + (j + 1) % segments]
            v3 = bm.verts[(i + 1) * segments + (j + 1) % segments]
            v4 = bm.verts[(i + 1) * segments + j]
            bm.faces.new((v1, v2, v3, v4))
    
    top_verts = [bm.verts[rings * segments + j] for j in range(segments)]
    bm.faces.new(top_verts)
    
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return obj

def generate_blackberry():
    clear_scene()
    
    # Materials: Deep dark purple-black, high gloss
    berry_mat = create_material("BerryMat", (0.03, 0.01, 0.06, 1.0), roughness=0.08, specular=1.0)
    stem_mat = create_material("StemMat", (0.35, 0.5, 0.15, 1.0), roughness=0.4, specular=0.2)
    
    # Overall Shape Parameters
    width = 1.0
    depth = 1.0
    height = 1.6
    
    # 1. CREATE A CORE: To hide the hollow center and create deep shadows in crevices
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.7, location=(0,0,0), segments=32, ring_count=16)
    core = bpy.context.active_object
    core.scale = (width * 0.8, depth * 0.8, height * 0.8)
    core.data.materials.append(berry_mat)
    bpy.ops.object.shade_smooth()

    # 2. MAIN DRUPLETS: Higher count and slightly larger to ensure overlap/tight packing
    num_main = 180
    main_radius = 0.17
    for i in range(num_main):
        phi = math.acos(1 - 2 * (i + 0.5) / num_main)
        theta = math.pi * (1 + 5**0.5) * (i + 0.5)
        
        sx, sy, sz = math.sin(phi)*math.cos(theta), math.sin(phi)*math.sin(theta), math.cos(phi)
        
        # Jitter for organic feel, but keep it tight to the ellipsoid surface
        jitter = 0.04
        px = sx * width + (random.random() - 0.5) * jitter
        py = sy * depth + (random.random() - 0.5) * jitter
        pz = sz * height + (random.random() - 0.5) * jitter
        
        create_sphere(f"Main_{i}", Vector((px, py, pz)), main_radius, berry_mat)

    # 3. FINE DRUPLETS: Fill the gaps between larger spheres to create that "textured" look
    num_fine = 120
    fine_radius = 0.08
    for i in range(num_fine):
        phi = math.acos(1 - 2 * (i + 0.5) / num_fine)
        theta = math.pi * (1 + 5**0.5) * (i + 0.5)
        
        sx, sy, sz = math.sin(phi)*math.cos(theta), math.sin(phi)*math.sin(theta), math.cos(phi)
        
        # Place slightly offset to fit in the interstices of the main spheres
        px = sx * (width + 0.05)
        py = sy * (depth + 0.05)
        pz = sz * (height + 0.05)
        
        create_sphere(f"Fine_{i}", Vector((px, py, pz)), fine_radius, berry_mat)

    # Stem positioning
    stem = create_stem(stem_mat)
    stem.location = (0, 0, height / 2)
    stem.rotation_euler = (0.15, 0.1, 0)

if __name__ == "__main__":
    generate_blackberry()
