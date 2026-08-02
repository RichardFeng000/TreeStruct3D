import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    # Clean up orphan data
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
        bsdf.inputs['Roughness'].default_value = 0.6
    return mat

def create_spider_plant():
    clear_scene()

    # Colors for high contrast to ensure visibility of edges
    # Deep green center, light cream/yellow edges
    color_center = (0.15, 0.4, 0.05, 1.0)  # Dark Green
    color_edge = (0.85, 0.9, 0.6, 1.0)     # Pale Yellow-Green/Cream
    
    mat_center = create_material("PlantCenter", color_center)
    mat_edge = create_material("PlantEdge", color_edge)

    # Plant parameters
    num_leaves = 220
    leaf_segments = 24
    
    mesh = bpy.data.meshes.new("SpiderPlant")
    obj = bpy.data.objects.new("SpiderPlant", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Assign materials to the object
    obj.data.materials.append(mat_center) # Index 0
    obj.data.materials.append(mat_edge)   # Index 1

    bm = bmesh.new()

    for i in range(num_leaves):
        # --- 1. Distribution for "Spherical Rosette" with arching flow ---
        # phi: rotation around Z
        phi = random.uniform(0, 2 * math.pi)
        
        # theta: angle from vertical (Z). 
        # Use a distribution that clusters leaves starting upwards then curving out
        theta = random.uniform(0, math.pi * 0.6) # Mostly upper hemisphere
        
        start_dir = Vector((
            math.sin(theta) * math.cos(phi),
            math.sin(theta) * math.sin(phi),
            math.cos(theta)
        ))

        length = random.uniform(3.0, 5.0)
        max_width = random.uniform(0.12, 0.22) # Slightly wider for visibility
        curvature = random.uniform(0.6, 1.2)   # How much they bend down

        prev_verts = []
        
        for s in range(leaf_segments + 1):
            t = s / leaf_segments
            
            # Create a quadratic curve for the leaf: start_pos + t*start_dir + t^2 * gravity
            # This creates an organic arching effect
            current_pos = start_dir * (t * length)
            # Apply downward pull increasing with length
            current_pos.z -= (t**2 * length * curvature)
            
            # Taper: Wide at base, very thin at tip
            w = max_width * (1.0 - t**0.6) if t < 1.0 else 0.01
            
            # Calculate local axis for the width strip
            # We want the "ribbon" to align with the curve tangent
            tangent = Vector((0,0,0)) # Simple approximation of leaf flow
            if s > 0:
                # Use distance from previous point as a rough tangent
                # but since we need a perpendicular vector for width...
                pass
            
            # Consistent "right" vector relative to the growth direction
            up = Vector((0, 0, 1)) if abs(start_dir.dot(Vector((0,0,1)))) < 0.9 else Vector((1, 0, 0))
            right = start_dir.cross(up).normalized()
            
            # Create vertices for this ring: [EdgeL, CenterL, CenterR, EdgeR]
            ring_verts = []
            offsets = [-1.0, -0.25, 0.25, 1.0]
            for offset_val in offsets:
                v_pos = current_pos + right * (offset_val * w * 0.5)
                ring_verts.append(bm.verts.new(v_pos))
            
            if prev_verts:
                # Connect the ring segments into quads
                for j in range(3):
                    f = bm.faces.new((prev_verts[j], prev_verts[j+1], ring_verts[j+1], ring_verts[j]))
                    # Material Index 0: Center, 1: Edge
                    if j == 1:
                        f.material_index = 0 # Center strip (green)
                    else:
                        f.material_index = 1 # Outer strips (cream)

            prev_verts = ring_verts

    bm.to_mesh(mesh)
    bm.free()
    
    # Smooth out the organic blades
    mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    mod.levels = 1
    mod.render_levels = 2
    
    # Set smooth shading
    for poly in mesh.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    create_spider_plant()
