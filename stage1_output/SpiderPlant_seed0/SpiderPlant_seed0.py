import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, color):
    """Creates a Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.4
    return mat

def create_spider_plant():
    clear_scene()

    # Yellow-green base, light cream/yellow edges
    color_center = (0.35, 0.6, 0.1, 1.0)  # Vibrant Yellow-Green
    color_edge = (0.8, 0.9, 0.5, 1.0)     # Pale Light Yellow/Cream
    
    mat_center = create_material("PlantCenter", color_center)
    mat_edge = create_material("PlantEdge", color_edge)

    num_leaves = 250
    leaf_segments = 24
    
    mesh = bpy.data.meshes.new("SpiderPlant")
    obj = bpy.data.objects.new("SpiderPlant", mesh)
    bpy.context.collection.objects.link(obj)
    
    obj.data.materials.append(mat_center) # Index 0
    obj.data.materials.append(mat_edge)   # Index 1

    bm = bmesh.new()

    for i in range(num_leaves):
        # Distribution for a dense spherical rosette
        phi = random.uniform(0, 2 * math.pi)
        # theta: Angle from Z axis (up). Distribute more towards the sides to fill sphere
        theta = random.uniform(0, math.pi * 0.7)
        
        start_dir = Vector((
            math.sin(theta) * math.cos(phi),
            math.sin(theta) * math.sin(phi),
            math.cos(theta)
        ))

        length = random.uniform(4.0, 6.0)
        # Increase max_width to make them "blade-like" instead of needle-like
        max_width = random.uniform(0.25, 0.35)
        curvature = random.uniform(0.5, 1.3)

        prev_verts = []
        
        for s in range(leaf_segments + 1):
            t = s / leaf_segments
            
            # Quadratic curve for organic arching
            current_pos = start_dir * (t * length)
            current_pos.z -= (t**2 * length * curvature * 0.6)
            
            # Taper: Slightly wider base, sharp tip
            w = max_width * (1.0 - t**0.7) if t < 1.0 else 0.005
            
            # Calculate orientation for the ribbon
            up = Vector((0, 0, 1)) if abs(start_dir.dot(Vector((0,0,1)))) < 0.9 else Vector((1, 0, 0))
            right = start_dir.cross(up).normalized()
            
            # Vertices for the ring: [EdgeL, CenterL, CenterR, EdgeR]
            # Widened center strip (from -0.3 to 0.3) relative to total width (-1 to 1)
            ring_verts = []
            offsets = [-1.0, -0.3, 0.3, 1.0]
            for offset_val in offsets:
                v_pos = current_pos + right * (offset_val * w * 0.5)
                ring_verts.append(bm.verts.new(v_pos))
            
            if prev_verts:
                for j in range(3):
                    f = bm.faces.new((prev_verts[j], prev_verts[j+1], ring_verts[j+1], ring_verts[j]))
                    # Center strip index 0, edges index 1
                    f.material_index = 0 if j == 1 else 1

            prev_verts = ring_verts

    bm.to_mesh(mesh)
    bm.free()
    
    mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    mod.levels = 1
    
    for poly in mesh.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    create_spider_plant()
