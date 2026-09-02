import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clear all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.5, specular=0.5):
    """Create a simple Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['Specular IOR Level'].default_value = specular
    return mat

def build_starfruit():
    # Parameters for a more authentic carambola shape
    segments_z = 64
    segments_theta = 120 # Higher resolution for sharper ridges
    radius_base = 0.8
    amplitude = 0.35     # Increased to create deeper valleys and prominent ribs
    height = 2.5
    
    mesh = bpy.data.meshes.new("Starfruit")
    obj = bpy.data.objects.new("Starfruit", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    rings = []
    for i in range(segments_z):
        # z from -height/2 to height/2
        norm_z = (i / (segments_z - 1)) * 2 - 1 # Range -1 to 1
        z = norm_z * (height / 2)
        
        # Ellipsoidal profile: narrower at the ends, plump in the middle
        taper = math.sqrt(max(0, 1.0 - (norm_z**2) * 0.4))
        
        ring = []
        for j in range(segments_theta):
            theta = (j / segments_theta) * 2 * math.pi
            # Star shape: modulation with higher amplitude for prominent ridges
            # We use a slightly modified cosine to make the ribs feel more structural
            r = (radius_base + amplitude * math.cos(5 * theta)) * taper
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            ring.append(bm.verts.new(Vector((x, y, z))))
        rings.append(ring)

    # Bridge the rings to create faces
    for i in range(segments_z - 1):
        for j in range(segments_theta):
            v1 = rings[i][j]
            v2 = rings[i][(j + 1) % segments_theta]
            v3 = rings[i+1][(j + 1) % segments_theta]
            v4 = rings[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    # Close the caps
    bm.faces.new(rings[0][::-1]) # Bottom
    bm.faces.new(rings[-1])      # Top

    bm.to_mesh(mesh)
    bm.free()

    # Add Subdivision Surface for a waxy, smooth look while preserving the ribs
    subdiv = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subdiv.levels = 1 # Lowered slightly to prevent "blobbing" out the star shape
    subdiv.render_levels = 2
    
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    return obj

def build_stem():
    """Create a slightly twisted brown stem."""
    mesh = bpy.data.meshes.new("Stem")
    obj = bpy.data.objects.new("Stem", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    stem_radius = 0.05
    stem_height = 0.4
    steps = 12
    res = 12
    
    verts = []
    for i in range(steps + 1):
        z = (i / steps) * stem_height
        # Twist and slight curve
        offset_x = 0.06 * math.sin(z * 3)
        offset_y = 0.04 * math.cos(z * 2)
        
        ring = []
        for j in range(res):
            theta = (j / res) * 2 * math.pi
            twist_angle = z * 2.0
            x = stem_radius * math.cos(theta + twist_angle) + offset_x
            y = stem_radius * math.sin(theta + twist_angle) + offset_y
            ring.append(bm.verts.new(Vector((x, y, z))))
        verts.append(ring)
        
    for i in range(steps):
        for j in range(res):
            v1 = verts[i][j]
            v2 = verts[i][(j + 1) % res]
            v3 = verts[i+1][(j + 1) % res]
            v4 = verts[i+1][j]
            bm.faces.new((v1, v2, v3, v4))
            
    bm.faces.new(verts[-1])
    bm.to_mesh(mesh)
    bm.free()
    
    # Position stem on top of the fruit (fruit height 2.5, centered at 0 -> top is 1.25)
    obj.location = (0, 0, 1.25)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()
    return obj

def main():
    clear_scene()
    
    # Fruit: Pale cream-yellow with waxy properties
    fruit_mat = create_material(
        "FruitMat", 
        (0.96, 0.91, 0.42, 1.0), # Creamy yellow
        roughness=0.15,           # More glossy/waxy
        specular=0.8
    )
    # Stem: Brown
    stem_mat = create_material(
        "StemMat", 
        (0.2, 0.15, 0.1, 1.0), 
        roughness=0.6, 
        specular=0.2
    )
    
    fruit = build_starfruit()
    stem = build_stem()
    
    fruit.data.materials.append(fruit_mat)
    stem.data.materials.append(stem_mat)

if __name__ == "__main__":
    main()
