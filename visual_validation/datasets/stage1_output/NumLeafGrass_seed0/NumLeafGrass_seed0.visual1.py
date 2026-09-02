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
    """Creates a low-poly rounded leaflet based on a flattened sphere."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Create a low-poly sphere and flatten it later via scale
    # To keep it low poly but rounded, we use a small number of segments
    rings = 6
    segments = 8
    
    verts = []
    for i in range(rings):
        phi = (math.pi * i) / (rings - 1)
        ring_verts = []
        r = math.sin(phi) # Basic unit sphere radius
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
            
    # Close the poles if necessary (bmesh faces.new can handle the lists)
    try:
        bm.faces.new(verts[0])
        bm.faces.new(verts[-1])
    except:
        pass # BMesh might complain if pole is already a point/degenerate
    
    bm.to_mesh(mesh)
    bm.free()
    
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Dark Green color (R, G, B, A)
    dark_green = (0.02, 0.15, 0.02, 1.0)
    mat = create_material("CloverGreen", dark_green)
    
    # Stem
    stem = create_stem(mat)
    stem_height = 1.0
    
    # Clover configuration (3 leaflets)
    num_leaves = 3
    for i in range(num_leaves):
        leaf = create_leaf(f"Leaf_{i}", mat)
        
        # Flatten and shape the leaf to be a rounded oval/disk
        # X: Width, Y: Thickness (very thin), Z: Length (rounded)
        # In our create_leaf, the sphere is center-based. 
        # We want it to look like a flat petal.
        leaf.scale = (0.3, 0.05, 0.3) # Small, rounded, and thin
        
        # Positioning logic
        angle = (2 * math.pi * i) / num_leaves
        
        # Rotate to orient the "flat" side correctly and tilt outward
        leaf.rotation_mode = 'XYZ'
        
        # Calculate orientation: 
        # 1. Tilt leaf along its local axis so it points away from center
        # Since we scaled Y as thickness, XZ is the face of the leaf.
        rot_z = angle
        rot_y = math.radians(45) # Moderate tilt for a cluster look
        
        leaf.rotation_euler = (0, rot_y, rot_z)
        
        # Position at the top of the stem
        # Offset slightly so they radiate from a central point
        offset_dist = 0.02
        leaf.location = (
            math.cos(angle) * offset_dist,
            math.sin(angle) * offset_dist,
            stem_height
        )

if __name__ == "__main__":
    main()
