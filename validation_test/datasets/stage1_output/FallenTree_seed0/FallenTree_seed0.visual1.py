import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a basic diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        # Make it look a bit more like bark (roughness)
        bsdf.inputs['Roughness'].default_value = 0.9
    return mat

def create_detailed_trunk(name, start, end, radius_start, radius_end):
    """Creates a trunk with organic ridge-like bark texture."""
    bm = bmesh.new()
    rings = 64
    segments = 32
    
    verts = []
    for i in range(rings):
        t = i / (rings - 1)
        curr_radius = radius_start + t * (radius_end - radius_start)
        center = start.lerp(end, t)
        
        ring_verts = []
        for j in range(segments):
            angle = (2 * math.pi * j) / segments
            
            # Create ridges: use sine waves combined with random noise for 'peeling' look
            ridge = math.sin(angle * 5 + t * 2) * 0.15
            roughness = random.uniform(-0.05, 0.05)
            offset_r = curr_radius + ridge + roughness
            
            v = Vector((
                center.x + math.cos(angle) * offset_r,
                center.y + math.sin(angle) * offset_r,
                center.z + random.uniform(-0.05, 0.05) # slight Z jitter for horizontal lie
            ))
            ring_verts.append(bm.verts.new(v))
        verts.append(ring_verts)

    for i in range(rings - 1):
        for j in range(segments):
            v1 = verts[i][j]
            v2 = verts[i][(j + 1) % segments]
            v3 = verts[i+1][(j + 1) % segments]
            v4 = verts[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    # Left end: Broken stump (Squared-off/Jagged)
    stump_verts = verts[0]
    # Group vertices to make it look less circular and more "broken"
    for v in stump_verts:
        # Shift based on quadrants to create a squared-off effect
        v.co.x -= 0.1 * random.uniform(0.5, 1.5)
        v.co.y += random.uniform(-0.2, 0.2)
        v.co.z += random.uniform(-0.2, 0.2)

    # Cap ends
    bm.faces.new(verts[0])
    bm.faces.new(verts[-1])
    
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def grow_branch(bm, start, direction, length, radius, depth):
    """Recursively grows branches that taper to points."""
    if depth <= 0 or radius < 0.01:
        return
        
    num_segs = 8
    seg_verts = []
    for i in range(num_segs):
        angle = (2 * math.pi * i) / num_segs
        perp = direction.cross(Vector((0,1,0))) if abs(direction.dot(Vector((0,1,0)))) < 0.9 else direction.cross(Vector((1,0,0)))
        perp.normalize()
        ortho = direction.cross(perp).normalized()
        v = start + (perp * math.cos(angle) + ortho * math.sin(angle)) * radius
        seg_verts.append(bm.verts.new(v))
        
    end_pos = start + direction * length
    # Taper the radius significantly for twigs
    next_radius = radius * 0.65
    
    end_verts = []
    for i in range(num_segs):
        angle = (2 * math.pi * i) / num_segs
        perp = direction.cross(Vector((0,1,0))) if abs(direction.dot(Vector((0,1,0)))) < 0.9 else direction.cross(Vector((1,0,0)))
        perp.normalize()
        ortho = direction.cross(perp).normalized()
        # If it's the final depth, taper to a near-point (twig)
        current_r = next_radius if depth > 1 else next_radius * 0.1
        v = end_pos + (perp * math.cos(angle) + ortho * math.sin(angle)) * current_r
        end_verts.append(bm.verts.new(v))
        
    for i in range(num_segs):
        bm.faces.new((seg_verts[i], seg_verts[(i+1)%num_segs], end_verts[(i+1)%num_segs], end_verts[i]))
        
    # Branching factor
    num_children = random.randint(1, 2) if depth > 1 else 0
    for _ in range(num_children):
        # Randomize direction more for "tangled" look
        offset = Vector((random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.6), random.uniform(-0.3, 0.7)))
        new_dir = (direction + offset).normalized()
        grow_branch(bm, end_pos, new_dir, length * 0.75, next_radius, depth - 1)

def generate_fallen_tree():
    clear_scene()
    
    # Warm sandy tan-brown material
    bark_mat = create_material("BarkMat", (0.72, 0.58, 0.42, 1.0))
    
    trunk_start = Vector((-6, 0, 0))
    trunk_end = Vector((8, 0, 0))
    trunk_radius_left = 0.8
    trunk_radius_right = 0.4
    
    # Create Trunk
    trunk_mesh = create_detailed_trunk("Trunk", trunk_start, trunk_end, trunk_radius_left, trunk_radius_right)
    trunk_obj = bpy.data.objects.new("FallenTrunk", trunk_mesh)
    bpy.context.collection.objects.link(trunk_obj)
    trunk_obj.data.materials.append(bark_mat)

    # Create Branches in a single BMesh for efficiency
    branch_bm = bmesh.new()
    num_main_branches = 15
    for i in range(num_main_branches):
        t = random.uniform(0.1, 0.8) # Concentrate branches away from the very end/stump
        pos = trunk_start.lerp(trunk_end, t)
        # Upward and outward spread
        dir = Vector((random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.6), random.uniform(0.3, 1.0))).normalized()
        rad = (trunk_radius_left + t * (trunk_radius_right - trunk_radius_left)) * 0.5
        grow_branch(branch_bm, pos, dir, random.uniform(1.2, 3.0), rad, 3)

    branches_mesh = bpy.data.meshes.new("Branches")
    branch_bm.to_mesh(branches_mesh)
    branch_bm.free()
    branches_obj = bpy.data.objects.new("Branches", branches_mesh)
    bpy.context.collection.objects.link(branches_obj)
    branches_obj.data.materials.append(bark_mat)

if __name__ == "__main__":
    generate_fallen_tree()
