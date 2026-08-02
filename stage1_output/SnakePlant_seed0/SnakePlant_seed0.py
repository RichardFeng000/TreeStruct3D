import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_materials():
    """Creates the characteristic green and cream materials for the snake plant."""
    mat_green = bpy.data.materials.new(name="Sansevieria_Green")
    mat_green.use_nodes = True
    nodes = mat_green.node_tree.nodes
    nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.05, 0.2, 0.05, 1.0) # Dark muted green

    mat_cream = bpy.data.materials.new(name="Sansevieria_Cream")
    mat_cream.use_nodes = True
    nodes = mat_cream.node_tree.nodes
    nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.8, 0.85, 0.7, 1.0) # Light cream/yellow-green

    return mat_green, mat_cream

def create_leaf(name, height, width, curvature, materials):
    """Creates a single sword-shaped leaf with banding."""
    bm = bmesh.new()
    
    # Parameters for the leaf shape
    segments_h = 32 # Vertical resolution for banding and bending
    segments_w = 8  # Horizontal resolution (elliptical cross section)
    
    # Create vertices for the leaf
    # We build it as a series of rings from bottom to top
    rings = []
    for i in range(segments_h + 1):
        t = i / segments_h # normalized height [0, 1]
        
        # Tapering logic: Wide at base, stays wide for a bit, then tapers to point
        if t < 0.2:
            current_width = width * (0.8 + 0.2 * (t / 0.2))
        elif t < 0.7:
            current_width = width
        else:
            # Taper to a point at the top
            current_width = width * (1.0 - (t - 0.7) / 0.3)
        
        # Apply curvature offset (simple arc)
        offset_x = math.sin(t * math.pi * 0.5) * curvature
        offset_y = math.cos(t * math.pi * 0.2) * (curvature * 0.3)
        
        ring = []
        for j in range(segments_w):
            angle = (j / segments_w) * 2 * math.pi
            # Slightly elliptical cross section
            vx = offset_x + math.cos(angle) * current_width * 0.5
            vy = offset_y + math.sin(angle) * current_width * 0.2
            vz = t * height
            ring.append(bm.verts.new(Vector((vx, vy, vz))))
        rings.append(ring)

    # Create faces
    for i in range(segments_h):
        for j in range(segments_w):
            v1 = rings[i][j]
            v2 = rings[i+1][j]
            v3 = rings[i+1][(j + 1) % segments_w]
            v4 = rings[i][(j + 1) % segments_w]
            
            face = bm.faces.new((v1, v2, v3, v4))
            
            # Assign material based on height segment for banding effect
            # We use a sine wave or modulo to create the stripes
            band_freq = 5 # Number of bands per leaf
            if int(i * band_freq / segments_h) % 2 == 0:
                face.material_index = 0
            else:
                face.material_index = 1

    # Finalize mesh
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    # Assign materials to the object
    obj.data.materials.append(materials[0]) # Green
    obj.data.materials.append(materials[1]) # Cream
    
    return obj

def main():
    clear_scene()
    
    mats = create_materials()
    
    # Plant parameters
    num_leaves = 14
    base_radius = 0.3
    
    for i in range(num_leaves):
        # Randomize dimensions for an organic look
        height = random.uniform(2.5, 4.5)
        width = random.uniform(0.2, 0.4)
        curvature = random.uniform(0.3, 0.8) * random.choice([-1, 1])
        
        leaf_name = f"Leaf_{i}"
        leaf = create_leaf(leaf_name, height, width, curvature, mats)
        
        # Position and rotate the leaf to splay from a common base
        angle = (2 * math.pi / num_leaves) * i + random.uniform(-0.2, 0.2)
        splay = random.uniform(0.15, 0.35) # radians from vertical
        
        # Move to be slightly offset from center
        leaf.location.x = math.cos(angle) * (base_radius * 0.5)
        leaf.location.y = math.sin(angle) * (base_radius * 0.5)
        
        # Rotate leaf to splay outwards
        # We rotate around the axis perpendicular to the angle vector
        rotation_axis = Vector((-math.sin(angle), math.cos(angle), 0))
        leaf.rotation_euler = rotation_axis.to_track_quat('Y', 'Z').to_euler()
        
        # Apply additional rotation for the splay angle
        # In Blender, it's easier to just set Euler angles directly relative to the base
        # Let's override the previous rot and use a simpler method:
        leaf.rotation_mode = 'XYZ'
        leaf.rotation_euler[0] = splay * math.cos(angle) # Approximation of splay
        leaf.rotation_euler[1] = splay * math.sin(angle)
        # Ensure it doesn't lean too far back/forward symmetrically
        leaf.rotation_euler[2] = angle

    # To make the base look more "clustered", we can slightly overlap them 
    # by moving their origins or adjusting the rotation logic.
    # The current setup creates a nice radial burst of sword leaves.

if __name__ == "__main__":
    main()
