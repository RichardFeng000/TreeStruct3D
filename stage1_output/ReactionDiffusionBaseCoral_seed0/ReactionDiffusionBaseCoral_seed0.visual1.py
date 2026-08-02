import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears default objects from the scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_coral_dome():
    # Parameters for a detailed, pitted organic cellular look
    radius = 2.0
    segments = 300 # High resolution for fine detail
    rings = 150
    num_seeds = 600 # Increased seed count for smaller, more numerous cells
    
    pit_depth = 0.4  # How deep the centers of the cells go
    ridge_height = 0.2 # Height of ridges relative to surface
    
    # Create UV Sphere
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, 
        segments=segments, 
        ring_count=rings, 
        location=(0, 0, 0)
    )
    obj = bpy.context.active_object
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)

    # Cut the sphere into a dome (remove bottom half)
    verts_to_delete = [v for v in bm.verts if v.co.z < -0.1]
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')

    # Generate seed points on the surface of the dome to drive cellular structure
    seeds = []
    for _ in range(num_seeds):
        phi = random.uniform(0, 2 * math.pi)
        costheta = random.uniform(0, 1) # Upper hemisphere
        theta = math.acos(costheta)
        
        x = radius * math.sin(theta) * math.cos(phi)
        y = radius * math.sin(theta) * math.sin(phi)
        z = radius * math.cos(theta)
        seeds.append(Vector((x, y, z)))

    # Pre-calculate an average seed distance to normalize displacement
    avg_dist = math.sqrt((4 * math.pi * (radius**2)) / num_seeds)

    # Displacement Logic: Create Voronoi cells with pits at centers and ridges at boundaries
    for v in bm.verts:
        # Find the nearest seed distance d1
        # For efficiency we check a subset or use squared lengths, 
        # but for this size, a simple loop is fine.
        d1 = min((v.co - s).length for s in seeds)
        
        # Normalize distance relative to average cell spacing
        norm_dist = d1 / avg_dist
        
        # Cellular Function: 
        # At seed (norm_dist=0), we want a deep pit (negative offset)
        # As norm_dist increases, we move towards the ridge (positive offset)
        # We use a power function to make the pits more "concave" and walls steeper
        offset = (norm_dist**1.5 * ridge_height) - pit_depth
        
        # Organic Variation: Modulate strength based on position for irregularity
        variation = 0.8 + 0.4 * math.sin(v.co.x * 2) * math.cos(v.co.y * 2)
        offset *= variation
        
        # Apply displacement along the normal to keep dome shape foundation
        v.co += v.normal * offset

    # Finish BMesh and update mesh
    bm.to_mesh(mesh)
    bm.free()

    # Polish geometry
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    # Add Subdivision Surface for a smooth, organic coral feel
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1 # One level enough with high base resolution
    subsurf.render_levels = 2

    return obj

def main():
    clear_scene()
    coral = create_coral_dome()
    
    # Ensure it sits at the origin
    coral.location = (0, 0, 0)
    
    # Optional: Set a white material to match description's "white geometry"
    mat = bpy.data.materials.new(name="CoralWhite")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.9, 0.9, 0.9, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.8
    coral.data.materials.append(mat)

if __name__ == "__main__":
    main()
