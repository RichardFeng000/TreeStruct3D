import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple material with a specific RGBA color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        # Reduce specular for a more matte plant look
        bsdf.inputs['Roughness'].default_value = 0.8
    return mat

def create_stem(material):
    """Creates a thin low-poly cylindrical stem."""
    mesh = bpy.data.meshes.new("Stem")
    obj = bpy.data.objects.new("Stem", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    segments = 8
    radius = 0.025
    height = 1.2
    
    # Bottom circle
    verts_bottom = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        verts_bottom.append(bm.verts.new((math.cos(angle) * radius, math.sin(angle) * radius, 0)))
        
    # Top circle
    verts_top = []
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        verts_top.append(bm.verts.new((math.cos(angle) * radius, math.sin(angle) * radius, height)))
        
    # Walls
    for i in range(segments):
        bm.faces.new((verts_bottom[i], verts_bottom[(i + 1) % segments], 
                      verts_top[(i + 1) % segments], verts_top[i]))
        
    # Caps
    bm.faces.new(verts_bottom)
    bm.faces.new(verts_top)
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.data.materials.append(material)
    return obj, height

def create_leaf_mesh(name, material):
    """Creates a low-poly rounded leaflet."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Create a low-poly sphere to flatten into an oval leaf
    rings = 6
    segments = 8
    
    verts = []
    for i in range(rings):
        phi = (math.pi * i) / (rings - 1)
        ring_verts = []
        r = math.sin(phi)
        for j in range(segments):
            theta = (2 * math.pi * j) / segments
            x = math.cos(theta) * r
            y = math.sin(theta) * r
            z = math.cos(phi) 
            ring_verts.append(bm.verts.new((x, y, z)))
        verts.append(ring_verts)
        
    for i in range(rings - 1):
        for j in range(segments):
            v1 = verts[i][j]
            v2 = verts[i][(j + 1) % segments]
            v3 = verts[i+1][(j + 1) % segments]
            v4 = verts[i+1][j]
            bm.faces.new((v1, v2, v3, v4))
    
    try:
        bm.faces.new(verts[0])
        bm.faces.new(verts[-1])
    except:
        pass
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Slightly adjusted dark green for better visibility in render while remaining "dark"
    dark_green = (0.05, 0.2, 0.05, 1.0)
    mat = create_material("CloverGreen", dark_green)
    
    stem, stem_height = create_stem(mat)
    
    num_leaves = 3
    for i in range(num_leaves):
        leaf = create_leaf_mesh(f"Leaf_{i}", mat)
        
        # Flatten the sphere into an oval leaf (X: width, Y: thickness, Z: length)
        leaf.scale = (0.25, 0.03, 0.45) 
        
        angle = (2 * math.pi * i) / num_leaves
        
        # Orientation logic:
        # We want the leaf to radiate from the stem top.
        # The 'Z' axis of the scaled object is its length.
        leaf.rotation_mode = 'XYZ'
        
        # 1. Tilt it away from the vertical (stem)
        tilt_angle = math.radians(50) 
        # 2. Rotate around stem Z-axis to distribute leaves radially
        radial_angle = angle
        
        # To make them radiate correctly:
        # We rotate by radial_angle first, then tilt on the local X axis.
        # In Blender's Euler system (XYZ), we can use:
        leaf.rotation_euler = (tilt_angle, 0, radial_angle)
        
        # Position at top of stem and push outward along the radial direction
        offset_dist = 0.15
        leaf.location = (
            math.cos(radial_angle) * offset_dist,
            math.sin(radial_angle) * offset_dist,
            stem_height + 0.1 # Start slightly above the stem top to allow tilt overlap
        )

if __name__ == "__main__":
    main()
