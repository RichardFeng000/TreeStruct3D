import bpy
import bmesh
import math
from mathutils import Vector, Matrix, Quaternion

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
    return mat

def create_stem(material):
    """Creates a thin low-poly cylindrical stem."""
    mesh = bpy.data.meshes.new("Stem")
    obj = bpy.data.objects.new("Stem", mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    segments = 8
    radius = 0.02
    height = 1.0
    
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
    return obj

def create_leaf(name, material):
    """Creates a single low-poly oval leaflet."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Create a rounded low-poly leaf by manipulating a small grid or sphere
    # Using a scaled ellipsoid approach in bmesh for better control
    rings = 6
    segments = 8
    
    verts = []
    for i in range(rings):
        phi = (math.pi * i) / (rings - 1)
        ring_verts = []
        # Radius varies to make it rounded/oval
        r = math.sin(phi) * 0.25 
        for j in range(segments):
            theta = (2 * math.pi * j) / segments
            x = math.cos(theta) * r
            y = math.sin(theta) * r
            z = phi * 0.4 # Length of the leaf
            ring_verts.append(bm.verts.new((x, y, z)))
        verts.append(ring_verts)
        
    for i in range(rings - 1):
        for j in range(segments):
            v1 = verts[i][j]
            v2 = verts[i][(j + 1) % segments]
            v3 = verts[i+1][(j + 1) % segments]
            v4 = verts[i+1][j]
            bm.faces.new((v1, v2, v3, v4))
            
    bm.faces.new(verts[0])
    bm.faces.new(verts[-1])
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Dark Green color (R, G, B, A)
    dark_green = (0.05, 0.2, 0.05, 1.0)
    mat = create_material("CloverGreen", dark_green)
    
    # Stem
    stem = create_stem(mat)
    stem_height = 1.0
    
    # Leaf configuration (3 for a typical clover)
    num_leaves = 3
    for i in range(num_leaves):
        leaf = create_leaf(f"Leaf_{i}", mat)
        
        # Flatten the leaf to make it look like a petal/leaflet
        leaf.scale = (1.0, 0.4, 1.5) # Width, Thickness, Length
        
        # Positioning logic
        angle = (2 * math.pi * i) / num_leaves
        
        # Rotation: rotate around Z to distribute leaves, then tilt outward from stem
        # Use Euler for simplicity and reliability in Blender 5.0
        leaf.rotation_mode = 'XYZ'
        
        # Step 1: Rotate leaf so its length (scaled Z) points away from center
        # The leaf geometry was created along the local Z axis.
        # We rotate it to point outward by rotating around Y then Z.
        
        # Calculate orientation
        rot_z = angle
        rot_y = math.radians(60) # Tilt outwards
        
        leaf.rotation_euler = (0, rot_y, rot_z)
        
        # Position at the top of the stem
        offset_dist = 0.05
        leaf.location = (
            math.cos(angle) * offset_dist,
            math.sin(angle) * offset_dist,
            stem_height
        )

if __name__ == "__main__":
    main()
