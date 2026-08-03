import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_grass_material():
    """Creates a dark green material for the grass."""
    mat = bpy.data.materials.new(name="GrassMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    # Clear existing nodes to be safe
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Dark Green color (RGBA)
    node_principled.inputs['Base Color'].default_value = (0.02, 0.15, 0.01, 1.0)
    node_principled.inputs['Roughness'].default_value = 0.8
    
    links = mat.node_tree.links
    links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_grass_tuft():
    """Creates a procedural clump of grass blades with natural curvature."""
    num_blades = 180
    segments_per_blade = 12
    base_radius = 0.25
    avg_height = 1.4
    blade_width_base = 0.02
    blade_width_tip = 0.002

    # Create a single mesh for the whole tuft
    mesh = bpy.data.meshes.new("GrassTuft")
    obj = bpy.data.objects.new("GrassTuft", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()

    for i in range(num_blades):
        # Start position at base
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0, base_radius)
        start_pos = Vector((math.cos(angle) * dist, math.sin(angle) * dist, 0))
        
        # Blade properties (determined once per blade for smoothness)
        height = random.uniform(avg_height * 0.5, avg_height * 1.5)
        # Lean direction: general push outwards from center
        lean_dir = Vector((math.cos(angle), math.sin(angle), 0)) * random.uniform(0.2, 0.6)
        # Curvature: a secondary bend to make it look natural (arching)
        curve_dir = Vector((random.uniform(-1, 1), random.uniform(-1, 1), -0.3)).normalized() * random.uniform(0.4, 1.2)
        
        side_a = []
        side_b = []
        
        for s in range(segments_per_blade + 1):
            t = s / segments_per_blade # normalized [0, 1]
            
            # Parabolic growth: Linear vertical + quadratic lean/bend
            # z is primarily linear but dips slightly at the very end for a droop effect
            z_val = t * height if t < 0.8 else (height - (t-0.8)**2 * 0.5)
            
            # x, y offsets combine initial lean and quadratic curvature
            offset = (lean_dir * t) + (curve_dir * (t**2))
            curr_pos = start_pos + Vector((offset.x, offset.y, z_val))
            
            # Linear taper for width
            width = blade_width_base + t * (blade_width_tip - blade_width_base)
            
            # Perpendicular vector for the width of the strip
            # Use cross product with Z-up to find a local "across" direction
            tangent = Vector((offset.x, offset.y, z_val - (0 if s==0 else (s-1)/segments_per_blade * height))).normalized()
            if tangent.length < 0.01: # fallback for perfectly vertical blades
                tangent = Vector((0, 0, 1))
            
            perp = tangent.cross(Vector((0, 0, 1))) if abs(tangent.z) < 0.9 else tangent.cross(Vector((1, 0, 0)) )
            perp = perp.normalized()
            
            v1 = bm.verts.new(curr_pos + perp * (width / 2))
            v2 = bm.verts.new(curr_pos - perp * (width / 2))
            side_a.append(v1)
            side_b.append(v2)

        # Create faces to connect the vertex strips
        for s in range(segments_per_blade):
            try:
                bm.faces.new((side_a[s], side_a[s+1], side_b[s+1], side_b[s]))
            except ValueError:
                pass # Avoid duplicate faces

    # Finalize bmesh
    bm.to_mesh(mesh)
    bm.free()

    # Apply material
    grass_mat = create_grass_material()
    obj.data.materials.append(grass_mat)
    
    # Smoothing and modifiers
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subsurf.levels = 1

if __name__ == "__main__":
    clear_scene()
    create_grass_tuft()
