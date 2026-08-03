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
    # Parameters for a detailed, pitted organic look
    radius = 2.0
    segments = 256
    rings = 128
    num_seeds = 350
    
    ridge_strength = 0.45
    pit_depth = 0.7
    sigma_ridge = 0.15
    sigma_pit = 0.3
    
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

    # Generate seed points on the surface of the dome for Voronoi-like cellular structure
    seeds = []
    for _ in range(num_seeds):
        phi = random.uniform(0, 2 * math.pi)
        costheta = random.uniform(0, 1) # Upper hemisphere
        theta = math.acos(costheta)
        
        x = radius * math.sin(theta) * math.cos(phi)
        y = radius * math.sin(theta) * math.sin(phi)
        z = radius * math.cos(theta)
        seeds.append(Vector((x, y, z)))

    # Displacement Logic
    for v in bm.verts:
        # Find the two nearest seeds to create Voronoi boundaries (ridges) and centers (pits)
        dists_sq = sorted([ (v.co - s).length_squared for s in seeds ])
        d1 = math.sqrt(dists_sq[0]) 
        d2 = math.sqrt(dists_sq[1])
        delta = d2 - d1 # Distance from Voronoi boundary
        
        # Ridge: peaks when delta is small (near cell boundaries)
        ridge_val = math.exp(-(delta**2) / (2 * sigma_ridge**2))
        # Pit: dips when d1 is small (at center of cells)
        pit_val = math.exp(-(d1**2) / (2 * sigma_pit**2))
        
        # Vary intensity based on height for organic irregularity
        height_factor = (v.co.z / radius) * 0.4 + 0.6
        current_ridge = ridge_strength * height_factor
        current_pit = pit_depth * (1.3 - height_factor * 0.5)

        # Final offset: Ridges push out, pits pull in
        offset = (current_ridge * ridge_val) - (current_pit * pit_val)
        
        # Apply displacement along the normal
        v.co += v.normal * offset

    # Finish BMesh and update mesh
    bm.to_mesh(mesh)
    bm.free()

    # Polish geometry
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    # Add a Subdivision Surface modifier for the organic rounded look
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    # Note: 'rental_type' was an error in previous version; Catmull-Clark is default.

    return obj

def main():
    clear_scene()
    coral = create_coral_dome()
    
    # Ensure it sits at the origin
    coral.location = (0, 0, 0)

if __name__ == "__main__":
    main()
