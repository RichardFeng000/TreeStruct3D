import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_ruffled_lobe(name, center, scale, rotation):
    """Creates an organic ruffled lobe using smooth trigonometric displacement."""
    # Resolution for a smooth organic feel
    res_theta = 80 
    res_r = 40      
    radius = 1.5 * scale
    
    # Pre-calculate random phases for this specific lobe to ensure coherent waves
    # instead of per-vertex noise.
    phase1 = random.uniform(0, 2 * math.pi)
    phase2 = random.uniform(0, 2 * math.pi)
    phase3 = random.uniform(0, 2 * math.pi)
    phase4 = random.uniform(0, 2 * math.pi)
    
    bm = bmesh.new()
    
    # Create a grid of vertices in polar coordinates
    verts = []
    for r_idx in range(res_r):
        # Use a non-linear distribution for radius to get more detail at the edges
        norm_r = r_idx / float(res_r - 1)
        r_val = norm_r * radius
        
        ring = []
        for t_idx in range(res_theta):
            theta = (t_idx / float(res_theta)) * 2 * math.pi
            
            # --- Organic Displacement Logic ---
            # Edge factor increases displacement towards the perimeter (lettuce effect)
            edge_factor = norm_r**2.0
            
            # 1. Ruffling: High-frequency oscillations around the perimeter
            # We combine multiple frequencies for organic complexity
            ruffle = (
                math.sin(theta * 5 + phase1) * 0.6 +
                math.sin(theta * 11 + phase2) * 0.3 +
                math.sin(theta * 23 + phase3) * 0.1
            )
            
            # 2. Curling: Radial folding (concentric ripples)
            curl = math.sin(norm_r * 6 + phase4) * 0.4
            
            # Total Z displacement: combine ruffling and radial curls
            z = (ruffle + curl) * edge_factor * scale
            
            # To create "folds" rather than just a heightmap, we displace X and Y slightly
            # based on the ruffle pattern to push edges in/out.
            offset_r = ruffle * 0.2 * edge_factor * scale
            x = (r_val + offset_r) * math.cos(theta)
            y = (r_val + offset_r) * math.sin(theta)
            
            v = bm.verts.new(Vector((x, y, z)))
            ring.append(v)
        verts.append(ring)

    # Create faces between the concentric rings
    for r in range(res_r - 1):
        for t in range(res_theta):
            v1 = verts[r][t]
            v2 = verts[r+1][t]
            v3 = verts[r+1][(t + 1) % res_theta]
            v4 = verts[r][(t + 1) % res_theta]
            try:
                bm.faces.new((v1, v2, v3, v4))
            except ValueError:
                pass # Avoid duplicate faces

    # Finalize mesh
    mesh_data = bpy.data.meshes.new(name)
    bm.to_mesh(mesh_data)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh_data)
    bpy.context.collection.objects.link(obj)
    
    # Transform and rotate to overlap organically
    obj.location = center
    obj.rotation_euler = rotation
    
    return obj

def apply_organic_modifiers(obj):
    """Applies thickness and smoothing."""
    for poly in obj.data.polygons:
        poly.use_smooth = True

    # Solidify to create thin sheets
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.025 * (obj.scale[0] if hasattr(obj, 'scale') else 1.0)
    solid.offset = 0
    
    # Subdivision to ensure organic smoothness
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3

def main():
    clear_scene()
    
    lobes_count = 10
    lobe_objects = []
    
    # Spread lobes in a low-lying cluster around the origin
    for i in range(lobes_count):
        scale = random.uniform(1.0, 2.2)
        
        angle = (i / lobes_count) * 2 * math.pi
        dist = random.uniform(0.3, 1.8)
        center = Vector((
            math.cos(angle) * dist, 
            math.sin(angle) * dist, 
            random.uniform(-0.3, 0.3)
        ))
        
        # Random rotations to create organic overlaps and gaps
        rotation = Vector((
            random.uniform(-math.pi/2, math.pi/2),
            random.uniform(-math.pi/2, math.pi/2),
            random.uniform(0, 2 * math.pi)
        ))
        
        lobe = create_ruffled_lobe(f"Lobe_{i}", center, scale, rotation)
        apply_organic_modifiers(lobe)
        lobe_objects.append(lobe)

    # Join all parts into one coherent organic structure
    bpy.ops.object.select_all(action='DESELECT')
    for obj in lobe_objects:
        obj.select_set(True)
    
    if lobe_objects:
        bpy.context.view_layer.objects.active = lobe_objects[0]
        bpy.ops.object.join()
        
        final_obj = bpy.context.active_object
        final_obj.name = "CoralStructure"
        
        # Re-center the resulting object at origin
        bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')
        final_obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
