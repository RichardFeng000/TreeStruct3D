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
    # Parameters for a more aggressive, organic cellular look
    radius = 2.0
    segments = 400 # High resolution for fine detail
    rings = 200
    
    # We'll use two layers of seeds to achieve "varying scales"
    num_seeds_large = 150   # Main cellular structure
    num_seeds_small = 800   # Fine pitting/detail
    
    # Create UV Sphere as base
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

    def get_random_points_on_hemisphere(count, r):
        pts = []
        for _ in range(count):
            phi = random.uniform(0, 2 * math.pi)
            # Distribution for a hemisphere surface
            z = random.uniform(0, 1) 
            theta = math.acos(z)
            x = r * math.sin(theta) * math.cos(phi)
            y = r * math.sin(theta) * math.sin(phi)
            z_coord = r * math.cos(theta)
            pts.append(Vector((x, y, z_coord)))
        return pts

    seeds_large = get_random_points_on_hemisphere(num_seeds_large, radius)
    seeds_small = get_random_points_on_hemisphere(num_seeds_small, radius)

    # Calculate average spacing for normalization
    avg_dist_large = math.sqrt((2 * math.pi * (radius**2)) / num_seeds_large)
    avg_dist_small = math.sqrt((2 * math.pi * (radius**2)) / num_seeds_small)

    for v in bm.verts:
        # --- Large Scale Structure ---
        # Find distance to nearest seed for large cells
        d1_l = min((v.co - s).length for s in seeds_large)
        norm_l = d1_l / avg_dist_large
        # Power function creates steeper ridges and flatter pits
        # We map norm_l so that 0 is deep pit, ~1 is ridge
        val_large = (norm_l**2.5) * 0.4 - 0.3

        # --- Small Scale Detail ---
        d1_s = min((v.co - s).length for s in seeds_small)
        norm_s = d1_s / avg_dist_small
        # Smaller amplitude, more frequent pits
        val_small = (norm_s**3.0) * 0.15 - 0.1

        # Total displacement
        offset = val_large + val_small
        
        # Add some organic irregularity based on position
        variation = 1.0 + 0.2 * math.sin(v.co.x * 1.5) * math.cos(v.co.y * 1.5)
        offset *= variation
        
        # Apply displacement along the normal
        v.co += v.normal * offset

    bm.to_mesh(mesh)
    bm.free()

    # Polish geometry
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    # Subdiv for organic feel, but not so much that it erases the pits
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 1 

    return obj

def main():
    clear_scene()
    coral = create_coral_dome()
    
    # Ensure it sits at origin
    coral.location = (0, 0, 0)
    
    # Material: White geometry with some roughness for organic look
    mat = bpy.data.materials.new(name="CoralWhite")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.95, 0.95, 0.95, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.7
    coral.data.materials.append(mat)

if __name__ == "__main__":
    main()
