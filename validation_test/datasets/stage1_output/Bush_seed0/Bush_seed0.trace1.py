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

def grow_bush(bm, start_pos, direction, length, radius, depth):
    """Recursively grows branches for the bush."""
    if depth <= 0:
        return

    # Calculate end position of this segment
    end_pos = start_pos + direction * length
    
    # Radius decreases along the branch
    end_radius = radius * 0.75
    
    # Create the physical geometry for this segment
    create_tube_segment(bm, start_pos, end_pos, radius, end_radius)

    # Determine how many children to spawn (2 or 3)
    num_children = random.randint(2, 3)
    
    for _ in range(num_children):
        # Create a new direction: start with parent and add randomness
        jitter = Vector((
            random.uniform(-0.7, 0.7),
            random.uniform(-0.7, 0.7),
            random.uniform(-0.7, 0.7)
        ))
        
        new_dir = (direction + jitter).normalized()
        
        # Bias the growth to keep the bush rounded and generally upward/outward
        if depth > 2:
            center_pull = -end_pos.normalized() * 0.3
            new_dir = (new_dir + center_pull).normalized()

        # Avoid branches going straight back down too much early on
        if new_dir.z < -0.1 and depth > 3:
            new_dir.z += 0.4
            new_dir = new_dir.normalized()

        # Recursive call with decreased length and radius
        grow_bush(
            bm, 
            end_pos, 
            new_dir, 
            length * random.uniform(0.6, 0.8), 
            end_radius, 
            depth - 1
        )

def main():
    clear_scene()

    # Create a new BMesh for the bush
    bm = bmesh.new()

    # Root configuration
    num_roots = 8
    base_length = 0.8
    base_radius = 0.06
    max_depth = 5
    origin = Vector((0, 0, 0))

    # Create root stems spreading upwards and outwards from the center
    for i in range(num_roots):
        # Distribute roots around a circle on XZ plane, leaning up
        angle = (2 * math.pi / num_roots) * i
        root_dir = Vector((math.cos(angle), 0, math.sin(angle)))
        # Tilt them generally upwards (Y is usually up in some contexts, but Z is Blender's default UP)
        root_dir = (root_dir + Vector((0, 0, 1.5))).normalized()
        
        grow_bush(bm, origin, root_dir, base_length, base_radius, max_depth)

    # Create a mesh data object to hold the BMesh geometry
    mesh_data = bpy.data.meshes.new("BushMesh")
    bm.to_mesh(mesh_data)
    bm.free()

    # Create the Object and link it to the scene
    bush_obj = bpy.data.objects.new("BareBush", mesh_data)
    bpy.context.collection.objects.link(bush_obj)

    # Smooth shading for organic look
    for poly in bush_obj.data.polygons:
        poly.use_smooth = True

    # Add Subdivision Surface to smooth the tube segments
    subdiv = bush_obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subdiv.levels = 1
    subdiv.render_levels = 2

if __name__ == "__main__":
    main()
