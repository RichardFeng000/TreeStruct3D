import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default scene of all objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_mushroom_stem():
    """
    Creates a procedurally generated mushroom stem.
    Features: Curved path, tapering radius, and organic bumpy surface.
    """
    # Parameters
    height = 5.0
    base_radius = 0.7
    top_radius = 0.35
    rings_count = 64  # Vertical resolution
    segments_per_ring = 32 # Radial resolution
    curvature_amount = 1.2
    bumpiness = 0.12
    noise_scale = 0.5

    # Initialize BMesh
    bm = bmesh.new()

    # Create the stem's spine path and ring vertices
    # We use a parametric approach: t goes from 0 (base) to 1 (top)
    rings = []
    for i in range(rings_count):
        t = i / (rings_count - 1)
        
        # Define the center of the ring at this height (the curve)
        # Using a sine wave for a natural organic bend
        center_x = math.sin(t * math.pi) * curvature_amount * t
        center_y = math.cos(t * 2 * math.pi) * (curvature_amount * 0.3) * t
        center_z = t * height
        center = Vector((center_x, center_y, center_z))

        # Calculate the radius at this height (linear taper)
        current_radius = base_radius - (base_radius - top_radius) * t
        
        # Add organic variance to the ring's overall thickness
        ring_variance = 1.0 + (random.uniform(-0.1, 0.1))
        current_radius *= ring_variance

        # Create vertices for this ring
        ring_verts = []
        for j in range(segments_per_ring):
            angle = (2 * math.pi / segments_per_ring) * j
            
            # Basic circle coordinates
            vx = math.cos(angle) * current_radius
            vy = math.sin(angle) * current_radius
            vz = 0
            
            # Add "bumps" - local organic displacement
            # We mix some random noise with a bit of frequency based on the angle and height
            bump_offset = (
                math.sin(angle * 3 + t * 5) * bumpiness + 
                random.uniform(-bumpiness, bumpiness) * 0.5
            )
            
            # Push the vertex outward along its normal direction relative to center
            norm_dir = Vector((vx, vy, vz)).normalized()
            offset_vec = norm_dir * bump_offset
            
            # Final position: Center + Circle Position + Bump Offset
            vert_pos = center + Vector((vx, vy, vz)) + offset_vec
            
            v = bm.verts.new(vert_pos)
            ring_verts.append(v)
        
        rings.append(ring_verts)

    # Connect the rings with faces
    for i in range(rings_count - 1):
        ring_bottom = rings[i]
        ring_top = rings[i+1]
        for j in range(segments_per_ring):
            v1 = ring_bottom[j]
            v2 = ring_bottom[(j + 1) % segments_per_ring]
            v3 = ring_top[(j + 1) % segments_per_ring]
            v4 = ring_top[j]
            
            try:
                bm.faces.new((v1, v2, v3, v4))
            except ValueError:
                # Face might already exist in some edge cases
                pass

    # Close the bottom of the stem (cap the base)
    base_ring = rings[0]
    bm.faces.new(base_ring)
    
    # Close the top of the stem (cap the top)
    top_ring = rings[-1]
    # We need to reverse order for consistent normals
    bm.faces.new(reversed(top_ring))

    # Finalize BMesh into a mesh object
    mesh = bpy.data.meshes.new("MushroomStem")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("MushroomStem", mesh)
    bpy.context.collection.objects.link(obj)

    # Apply modifiers for organic smoothing
    # Subdivision Surface for smoothness
    subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3

    # Smooth shading
    for poly in mesh.polygons:
        poly.use_smooth = True

    return obj

def main():
    clear_scene()
    create_mushroom_stem()

if __name__ == "__main__":
    main()
