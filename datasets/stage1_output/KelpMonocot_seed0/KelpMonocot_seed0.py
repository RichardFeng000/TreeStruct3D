import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Clears the default scene of all objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_kelp_frond():
    """Generates a procedural kelp frond with a stipe and radiating blades."""
    # Parameters
    STIPE_HEIGHT = 12.0
    STIPE_RADIUS = 0.15
    STIPE_SEGMENTS = 60
    RING_RESOLUTION = 8
    
    BLADE_COUNT_PER_RING = 10
    BLADE_LENGTH = 1.2
    BLADE_WIDTH = 0.08
    BLADE_SEGMENTS = 8
    
    # Create BMesh for the entire plant
    bm = bmesh.new()

    # --- 1. Construct the Stipe (the main stem) ---
    stipe_verts = []
    last_pos = Vector((0, 0, 0))
    
    # Generate a slightly curved spine path for the stipe
    path_points = []
    for i in range(STIPE_SEGMENTS + 1):
        z = (i / STIPE_SEGMENTS) * STIPE_HEIGHT
        # Add organic sway using sine waves and random noise
        x = math.sin(z * 0.5) * 0.3 + random.uniform(-0.05, 0.05)
        y = math.cos(z * 0.3) * 0.3 + random.uniform(-0.05, 0.05)
        path_points.append(Vector((x, y, z)))

    # Create the tube around the path
    prev_ring = []
    for i in range(STIPE_SEGMENTS + 1):
        center = path_points[i]
        radius = STIPE_RADIUS * (1.0 - (i / STIPE_SEGMENTS) * 0.4) # Taper slightly at top
        
        # Create a ring of vertices
        current_ring = []
        for j in range(RING_RESOLUTION):
            angle = (2 * math.pi * j) / RING_RESOLUTION
            vx = center.x + math.cos(angle) * radius
            vy = center.y + math.sin(angle) * radius
            vz = center.z
            current_ring.append(bm.verts.new(Vector((vx, vy, vz))))
        
        # Bridge the rings with faces
        if i > 0:
            for j in range(RING_RESOLUTION):
                v1 = prev_ring[j]
                v2 = prev_ring[(j + 1) % RING_RESOLUTION]
                v3 = current_ring[(j + 1) % RING_RESOLUTION]
                v4 = current_ring[j]
                bm.faces.new((v1, v2, v3, v4))
        
        prev_ring = current_ring

    # Close the bottom of the stipe
    bm.faces.new(prev_ring[::-1]) # Top cap (though we're at index i=STIPE_SEGMENTS)
    
    # To properly close both ends, we need to handle indices carefully
    # Re-calculating for a clean base:
    # Since the loop above ended at top, prev_ring is the top. 
    # Let's just create a bottom cap by keeping track of the first ring.

    # --- 2. Construct the Blades (the leaves) ---
    # We iterate through the path points and attach blades to the stipe
    for i in range(0, STIPE_SEGMENTS + 1, 2): # Every second segment for density balance
        center = path_points[i]
        
        # Randomize number of blades at this height slightly
        count = BLADE_COUNT_PER_RING + random.randint(-2, 2)
        
        for b in range(count):
            # Angle around the stipe
            angle = (2 * math.pi * b / count) + random.uniform(-0.2, 0.2)
            dir_vec = Vector((math.cos(angle), math.sin(angle), 0))
            
            # Randomize blade length and width slightly
            length = BLADE_LENGTH * random.uniform(0.7, 1.3)
            width = BLADE_WIDTH * random.uniform(0.8, 1.2)
            
            # Each blade is a strip of quads tapering to a point
            blade_verts = []
            
            for s in range(BLADE_SEGMENTS + 1):
                t = s / BLADE_SEGMENTS # normalized length [0, 1]
                
                # Current width (tapers to 0 at the tip)
                curr_w = width * (1.0 - t)
                
                # Calculate position along a curved arc
                # The blade pushes outward and curves slightly downward/upward due to "water"
                offset_dist = t * length
                curve_z = -math.sin(t * math.pi * 0.5) * 0.4 # Droop
                
                pos_center = center + dir_vec * offset_dist
                pos_center.z += curve_z
                
                # Create the width cross-section (perpendicular to dir_vec and Z)
                side_vec = Vector((-dir_vec.y, dir_vec.x, 0))
                
                v_left = bm.verts.new(pos_center + side_vec * curr_w * 0.5)
                v_right = bm.verts.new(pos_center - side_vec * curr_w * 0.5)
                blade_verts.append((v_left, v_right))

            # Create faces for the blade strip
            for s in range(BLADE_SEGMENTS):
                v1 = blade_verts[s][0]
                v2 = blade_verts[s][1]
                v3 = blade_verts[s+1][1]
                v4 = blade_verts[s+1][0]
                bm.faces.new((v1, v2, v3, v4))

    # Finalize mesh
    bm.to_mesh(bpy.data.meshes.new("KelpMesh"))
    bm.free()

def setup_scene():
    clear_scene()
    
    # Create the kelp frond
    create_kelp_frond()
    
    # Find the created mesh and put it in an object
    mesh = bpy.data.meshes.get("KelpMesh")
    if mesh:
        obj = bpy.data.objects.new("KelpFrond", mesh)
        bpy.context.collection.objects.link(obj)
        
        # Apply a subdivision surface modifier for smoothness
        subdiv = obj.modifiers.new(name="Subdivision", type='SUBSURF')
        subdiv.levels = 1
        subdiv.render_levels = 2
        
        # Shade smooth
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth()

if __name__ == "__main__":
    setup_scene()
