import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Base Color'].default_value = color
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_branch(branch_mat):
    bm = bmesh.new()
    segments = 15
    radius_start = 0.07
    radius_end = 0.03
    length = 6.0
    ring_res = 8
    
    verts = []
    for i in range(segments + 1):
        z = (i / segments) * length
        # Add a bit more organic curve to the branch itself
        x = 0.1 * math.sin(z * 0.5) + random.uniform(-0.02, 0.02)
        y = 0.1 * math.cos(z * 0.3) + random.uniform(-0.02, 0.02)
        verts.append(Vector((x, y, z)))

    rings = []
    for i in range(segments + 1):
        r = radius_start - (i / segments) * (radius_start - radius_end)
        center = verts[i]
        # Calculate a basic tangent to keep rings perpendicular to the branch path
        if i < segments:
            tangent = (verts[i+1] - center).normalized()
        else:
            tangent = (center - verts[i-1]).normalized()
            
        ortho = Vector((0, 0, 1)) if abs(tangent.z) < 0.9 else Vector((0, 1, 0))
        right = tangent.cross(ortho).normalized()
        up = tangent.cross(right).normalized()
        
        ring = []
        for j in range(ring_res):
            angle = (2 * math.pi * j) / ring_res
            p = center + right * math.cos(angle) * r + up * math.sin(angle) * r
            ring.append(bm.verts.new(p))
        rings.append(ring)

    for i in range(segments):
        for j in range(ring_res):
            v1 = rings[i][j]
            v2 = rings[i][(j + 1) % ring_res]
            v3 = rings[i+1][(j + 1) % ring_res]
            v4 = rings[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

    bm.faces.new(rings[0])
    bm.faces.new(reversed(rings[-1]))
    
    mesh = bpy.data.meshes.new("BranchMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Branch", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(branch_mat)
    return obj

def create_needle_geometry(bm, start_pos, direction, length, radius):
    # Create a tapered, curved needle
    segments = 8
    ring_res = 4
    
    # Generate path with droop relative to the branch's local space
    path = []
    for i in range(segments + 1):
        t = i / segments
        dist = t * length
        
        # Needle curves slightly outwards then downwards
        # Direction is the initial launch vector
        pos = start_pos + direction * dist
        # Add quadratic droop (downwards)
        droop = 0.4 * (t**2)
        pos.z -= droop
        path.append(pos)

    rings = []
    for i in range(segments + 1):
        # Taper the needle from base to tip
        r = radius * (1.0 - (i / segments))
        p = path[i]
        
        # Orientation for the ring
        if i < segments:
            tangent = (path[i+1] - p).normalized()
        else:
            tangent = (p - path[i-1]).normalized()
            
        ortho = Vector((0, 0, 1)) if abs(tangent.z) < 0.9 else Vector((0, 1, 0))
        right = tangent.cross(ortho).normalized()
        up = tangent.cross(right).normalized()
        
        ring = []
        for j in range(ring_res):
            angle = (2 * math.pi * j) / ring_res
            rv = p + right * math.cos(angle) * r + up * math.sin(angle) * r
            ring.append(bm.verts.new(rv))
        rings.append(ring)

    for i in range(segments):
        for j in range(ring_res):
            v1 = rings[i][j]
            v2 = rings[i][(j + 1) % ring_res]
            v3 = rings[i+1][(j + 1) % ring_res]
            v4 = rings[i+1][j]
            bm.faces.new((v1, v2, v3, v4))

def create_needle_clusters(needle_mat):
    bm = bmesh.new()
    branch_len = 6.0
    num_bundles = 18 # Fewer bundles, more needles per bundle
    bundle_spacing = branch_len / num_bundles
    
    for i in range(num_bundles):
        z_pos = (i + 0.5) * bundle_spacing
        # Randomize start pos slightly to match the curved branch
        start_pos = Vector((0.1 * math.sin(z_pos * 0.5), 0.1 * math.cos(z_pos * 0.3), z_pos))
        
        # Each bundle has a distinct number of needles (e.g., pairs or triplets)
        needles_in_bundle = random.randint(2, 4)
        cluster_rot = random.uniform(0, 2 * math.pi)
        
        for n in range(needles_in_bundle):
            # Radiate needles from the bundle center
            angle = cluster_rot + (n / needles_in_bundle) * (2 * math.pi * 0.4)
            dir_vec = Vector((math.cos(angle), math.sin(angle), random.uniform(0.1, 0.5)))
            dir_vec = dir_vec.normalized()
            
            create_needle_geometry(bm, start_pos, dir_vec, length=1.4, radius=0.015)

    mesh = bpy.data.meshes.new("NeedlesMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Needles", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(needle_mat)
    return obj

def main():
    clear_scene()
    brown = (0.15, 0.09, 0.05, 1.0)
    green = (0.05, 0.2, 0.02, 1.0)
    branch_mat = create_material("BranchMat", brown)
    needle_mat = create_material("NeedleMat", green)
    create_branch(branch_mat)
    create_needle_clusters(needle_mat)

if __name__ == "__main__":
    main()
