import bpy
import bmesh
import math
from mathutils import Vector, Matrix

def clear_scene():
    """Clears all objects from the current scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_rounded_slab(name, length, width, thickness, radius, z_pos):
    """Creates a rectangular slab with rounded corners."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    # Create initial cube centered at origin
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale to actual dimensions
    for v in bm.verts:
        v.co.x *= length
        v.co.y *= width
        v.co.z *= thickness

    # Identify the 4 vertical edges for rounding corners
    vertical_edges = []
    for e in bm.edges:
        # Vertical edges are those where x and y of both verts are basically the same
        v1, v2 = e.verts
        if abs(v1.co.x - v2.co.x) < 0.001 and abs(v1.co.y - v2.co.y) < 0.001:
            vertical_edges.append(e)

    # Bevel vertical edges for rounded corners
    bmesh.ops.bevel(bm, 
                    geom=vertical_edges, 
                    offset=radius, 
                    segments=12, 
                    affect='EDGES')

    # Soften all remaining sharp edges slightly for a realistic look
    all_edges = [e for e in bm.edges]
    bmesh.ops.bevel(bm, 
                    geom=all_edges, 
                    offset=0.005, 
                    segments=2, 
                    affect='EDGES')

    bm.to_mesh(mesh)
    bm.free()
    
    obj.location.z = z_pos
    return obj

def create_pedestal_leg(name, x_pos, height, shaft_radius, base_radius):
    """Creates a pedestal leg with a flared circular base."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    
    # Create the main shaft as a cylinder
    bmesh.ops.create_cone(bm, 
                          cap_ends=True, 
                          segments=32, 
                          radius1=shaft_radius, 
                          radius2=shaft_radius, 
                          depth=height)

    # The cone is created from -height/2 to height/2.
    # Find the bottom face vertices and scale them out for the flare
    bottom_verts = [v for v in bm.verts if v.co.z < -height/2 + 0.01]
    for v in bottom_verts:
        v.co.x *= (base_radius / shaft_radius)
        v.co.y *= (base_radius / shaft_radius)

    # To make the flare look smooth, we find the edges connecting the shaft and the base
    # These are the vertical-ish edges at the bottom
    flare_edges = []
    for e in bm.edges:
        v1, v2 = e.verts
        if abs(v1.co.z - v2.co.z) < 0.01 and (abs(v1.co.x) > shaft_radius + 0.001):
            # This is the bottom rim edge
            flare_edges.append(e)
        elif abs(v1.co.z - v2.co.z) > height * 0.5: # Vertical edges of the leg
             # Only if they are at the bottom part (approx)
             if min(v1.co.z, v2.co.z) < -height/4:
                 flare_edges.append(e)

    # Refine geometry by beveling the base rim and transition
    # Specifically targeting the sharp bottom edge
    bottom_rim_edges = [e for e in bm.edges if all(abs(v.co.z + height/2) < 0.01 for v in e.verts)]
    bmesh.ops.bevel(bm, geom=bottom_rim_edges, offset=0.01, segments=3, affect='EDGES')

    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = (x_pos, 0, 0)
    return obj

def main():
    clear_scene()
    
    # --- Dimensions ---
    TABLE_LENGTH = 1.2
    TABLE_WIDTH = 0.6
    TABLE_THICKNESS = 0.04
    CORNER_RADIUS = 0.1
    
    TOTAL_HEIGHT = 0.38 # Low profile
    LEG_SHAFT_RADIUS = 0.05
    LEG_BASE_RADIUS = 0.15
    LEG_X_OFFSET = 0.35  # Positioned towards the ends of the rectangular top
    
    # Leg height is the distance between the two slabs
    leg_height = TOTAL_HEIGHT - (2 * TABLE_THICKNESS)
    
    # Calculate Z positions so bottom shelf sits on ground (Z=0)
    bottom_slab_z = TABLE_THICKNESS / 2
    top_slab_z = TOTAL_HEIGHT - (TABLE_THICKNESS / 2)
    leg_center_z = (bottom_slab_z + TABLE_THICKNESS) + (leg_height / 2)

    # Create Top Slab
    create_rounded_slab("TableTop", TABLE_LENGTH, TABLE_WIDTH, TABLE_THICKNESS, CORNER_RADIUS, top_slab_z)
    
    # Create Bottom Shelf
    create_rounded_slab("BottomShelf", TABLE_LENGTH, TABLE_WIDTH, TABLE_THICKNESS, CORNER_RADIUS, bottom_slab_z)
    
    # Create Pedestal Legs
    leg1 = create_pedestal_leg("LegLeft", -LEG_X_OFFSET, leg_height, LEG_SHAFT_RADIUS, LEG_BASE_RADIUS)
    leg1.location.z = leg_center_z
    
    leg2 = create_pedestal_leg("LegRight", LEG_X_OFFSET, leg_height, LEG_SHAFT_RADIUS, LEG_BASE_RADIUS)
    leg2.location.z = leg_center_z

if __name__ == "__main__":
    main()
