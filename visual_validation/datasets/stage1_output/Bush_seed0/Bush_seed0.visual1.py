import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_tube_segment(bm, p1, p2, r1, r2, segments=6):
    """Creates a cylindrical tube segment between two points in a BMesh."""
    direction = (p2 - p1).normalized()
    if direction.length < 0.001:
        return

    # Create an orthogonal basis for the rings
    ortho1 = direction.orthogonal()
    ortho2 = direction.cross(ortho1).normalized()

    ring1 = []
    for i in range(segments):
        angle = (2 * math.pi / segments) * i
        pos = p1 + (ortho1 * math.cos(angle) + ortho2 * math.sin(angle)) * r1
        ring1.append(bm.verts.new(pos))

    ring2 = []
    for i in range(segments):
        angle = (2 * math.pi / segments) * i
        pos = p2 + (ortho1 * math.cos(angle) + ortho2 * math.sin(angle)) * r2
        ring2.append(bm.verts.new(pos))

    for i in range(segments):
        v1 = ring1[i]
        v2 = ring1[(i + 1) % segments]
        v3 = ring2[(i + 1) % segments]
        v4 = ring2[i]
        try:
            bm.faces.new((v1, v2, v3, v4))
        except ValueError:
            pass

def grow_bush_recursive(bm, start_pos, direction, length, radius, depth):
    """Recursively grows branches with organic curvature and bifurcation."""
    if depth < 0:
        return

    # To create a more organic look, each 'branch' is split into 2 sub-segments
    # This allows for a slight bend in every branch.
    current_pos = start_pos
    current_dir = direction
    sub_segments = 2
    seg_len = length / sub_segments
    
    for i in range(sub_segments):
        # Add slight random jitter to the segment direction for organic curvature
        jitter = Vector((random.uniform(-0.2, 0.2), 
                        random.uniform(-0.2, 0.2), 
                        random.uniform(-0.2, 0.2)))
        current_dir = (current_dir + jitter).normalized()
        
        # Pull slightly toward the center if too far out to maintain rounded mass
        if current_pos.length > 1.5:
            center_pull = -current_pos.normalized() * 0.2
            current_dir = (current_dir + center_pull).normalized()

        end_pos = current_pos + current_dir * seg_len
        
        # Radius tapers slightly throughout the sub-segments
        r_start = radius
        r_end = radius * 0.9
        create_tube_segment(bm, current_pos, end_pos, r_start, r_end)
        
        current_pos = end_pos

    # Bifurcation: exactly 2 children for the 'repeatedly bifurcate' requirement
    if depth > 0:
        for _ in range(2):
            # Create a wide angle split from the current direction
            split_jitter = Vector((random.uniform(-0.8, 0.8), 
                                  random.uniform(-0.8, 0.8), 
                                  random.uniform(-0.8, 0.8)))
            new_dir = (current_dir + split_jitter).normalized()
            
            # Bias new branches generally upwards/outwards to fill the rounded volume
            up_bias = Vector((0, 0, 1)) * 0.3
            new_dir = (new_dir + up_bias).normalized()

            grow_bush_recursive(
                bm, 
                current_pos, 
                new_dir, 
                length * random.uniform(0.65, 0.8), 
                radius * 0.7, 
                depth - 1
            )

def main():
    clear_scene()

    bm = bmesh.new()

    # Root configuration for a dense bush
    num_roots = 12 
    base_length = 0.7
    base_radius = 0.05
    max_depth = 4 # With sub-segments and bifurcation, this creates plenty of density
    origin = Vector((0, 0, 0))

    for i in range(num_roots):
        # Spread root stems around a circle on the XY plane
        angle = (2 * math.pi / num_roots) * i
        # Roots start leaning outwards and upwards
        root_dir = Vector((math.cos(angle), math.sin(angle), random.uniform(0.3, 0.8))).normalized()
        
        grow_bush_recursive(bm, origin, root_dir, base_length, base_radius, max_depth)

    # Finalize mesh
    mesh_data = bpy.data.meshes.new("BushMesh")
    bm.to_mesh(mesh_data)
    bm.free()

    bush_obj = bpy.data.objects.new("BareBush", mesh_data)
    bpy.context.collection.objects.link(bush_obj)

    # Aesthetics
    for poly in bush_obj.data.polygons:
        poly.use_smooth = True

    subdiv = bush_obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subdiv.levels = 1
    subdiv.render_levels = 2

if __name__ == "__main__":
    main()
