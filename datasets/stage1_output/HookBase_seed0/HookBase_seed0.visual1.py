import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_box(name, width, depth, height, location=(0, 0, 0)):
    """Helper to create a scaled box."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (width, depth, height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj

def create_backplate(width, height, depth):
    """Creates the main flat rectangular panel."""
    # width is X, depth is Y (thickness), height is Z
    return create_box("Backplate", width, depth, height, location=(0, 0, 0))

def create_border_frame(width, height, depth, frame_thickness=0.03):
    """Creates a border frame consisting of four rails around the plate."""
    # The frame surrounds the backplate on the front face (XY plane essentially)
    # but in our setup: X=width, Y=depth, Z=height. 
    # Frame is on the front side (+Y).
    
    f_depth = depth + frame_thickness
    
    # Top bar
    create_box("FrameTop", width + 2*frame_thickness, f_depth, frame_thickness, 
               location=(0, (depth + f_depth/2)/2, height/2 + frame_thickness/2))
    
    # Bottom bar
    create_box("FrameBottom", width + 2*frame_thickness, f_depth, frame_thickness, 
               location=(0, (depth + f_depth/2)/2, -height/2 - frame_thickness/2))
    
    # Left bar
    create_box("FrameLeft", frame_thickness, f_depth, height, 
               location=(-width/2 - frame_thickness/2, (depth + f_depth/2)/2, 0))
    
    # Right bar
    create_box("FrameRight", frame_thickness, f_depth, height, 
               location=(width/2 + frame_thickness/2, (depth + f_depth/2)/2, 0))

def create_hook(pos_x, bottom_z):
    """Creates a single curved hook at the specified X position."""
    # Path: Start at plate -> move out in Y -> curve up and slightly back in Y
    points = []
    segments = 24
    out_dist = 0.08  # distance extending from wall (Y)
    curl_radius = 0.04 # curvature of the hook end
    
    for i in range(segments + 1):
        t = i / segments
        if t < 0.5: # Extending outward
            progress = t / 0.5
            y = progress * out_dist
            z = 0
            points.append(Vector((0, y, z)))
        else: # Curling up and back
            progress = (t - 0.5) / 0.5
            angle = progress * math.pi # Half circle curl
            y = out_dist + math.cos(angle) * curl_radius * 0.8
            z = math.sin(angle) * curl_radius
            points.append(Vector((0, y, z)))

    bm = bmesh.new()
    pipe_radius = 0.015
    res = 12
    
    prev_ring = []
    for p in points:
        current_ring = []
        # Create circle ring on XZ plane (perpendicular to Y axis)
        for j in range(res):
            angle = (j / res) * 2 * math.pi
            v = bm.verts.new((p.x + math.cos(angle)*pipe_radius, p.y, p.z + math.sin(angle)*pipe_radius))
            current_ring.append(v)
        
        # Fill the ring face (optional but helps with appearance)
        bm.faces.new(current_ring)
        
        if prev_ring:
            for j in range(res):
                v1 = prev_ring[j]
                v2 = prev_ring[(j+1)%res]
                v3 = current_ring[(j+1)%res]
                v4 = current_ring[j]
                bm.faces.new((v1, v2, v3, v4))
        prev_ring = current_ring

    mesh = bpy.data.meshes.new(f"HookMesh_{pos_x}")
    bm.to_mesh(mesh)
    bm.free()
    
    hook_obj = bpy.data.objects.new(f"Hook_{pos_x}", mesh)
    bpy.context.collection.objects.link(hook_obj)
    
    # Position the hook at bottom edge and correct X
    hook_obj.location = (pos_x, 0, bottom_z)
    return hook_obj

def main():
    clear_scene()

    # Parameters
    W, H, D = 0.6, 0.25, 0.02 # Width, Height, Depth
    num_hooks = 5
    frame_t = 0.03 # Frame thickness
    
    # Create Components
    create_backplate(W, H, D)
    create_border_frame(W, H, D, frame_t)
    
    # Hooks distribution along bottom edge
    bottom_z = -H/2 - frame_t/2
    hook_spacing = W / (num_hooks + 1)
    for i in range(1, num_hooks + 1):
        pos_x = -W/2 + (i * hook_spacing)
        create_hook(pos_x, bottom_z)

    # Final Polish: Smooth Shading and combine if needed
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for poly in obj.data.polygons:
                poly.use_smooth = True

if __name__ == "__main__":
    main()
