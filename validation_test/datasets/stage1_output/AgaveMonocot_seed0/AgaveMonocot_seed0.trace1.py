import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Removes all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    node_bsdf.inputs['Base Color'].default_value = color
    node_bsdf.inputs['Roughness'].default_value = 0.7
    
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_agave():
    # Parameters for the agave plant
    num_leaves = 60
    golden_angle = 137.5 * (math.pi / 180)
    base_radius = 0.05
    max_leaf_length = 2.8
    max_leaf_width = 0.25
    leaf_thickness = 0.06
    
    # Define colors for variation
    green_dark = (0.05, 0.15, 0.05, 1.0)
    green_mid = (0.1, 0.3, 0.1, 1.0)
    green_light = (0.3, 0.45, 0.2, 1.0)

    def get_random_green():
        t = random.random()
        if t < 0.6:
            # Interpolate dark and mid
            f = random.random()
            return (
                green_dark[0] + f * (green_mid[0] - green_dark[0]),
                green_dark[1] + f * (green_mid[1] - green_dark[1]),
                green_dark[2] + f * (green_mid[2] - green_dark[2]),
                1.0
            )
        else:
            # Interpolate mid and light
            f = random.random()
            return (
                green_mid[0] + f * (green_light[0] - green_mid[0]),
                green_mid[1] + f * (green_light[1] - green_mid[1]),
                green_mid[2] + f * (green_light[2] - green_mid[2]),
                1.0
            )

    # Create the central root base
    bm_base = bmesh.new()
    bmesh.ops.create_uvsphere(bm_base, u_segments=16, v_segments=8, radius=0.3)
    for v in bm_base.verts:
        v.co.z *= 0.4 # Squash the base
    
    base_mesh = bpy.data.meshes.new("AgaveBaseMesh")
    bm_base.to_mesh(base_mesh)
    bm_base.free()
    
    base_obj = bpy.data.objects.new("AgaveBase", base_mesh)
    bpy.context.collection.objects.link(base_obj)
    # Material for the root
    base_obj.data.materials.append(create_material("RootMat", green_dark))

    # Create leaves in a spiral pattern
    for i in range(num_leaves):
        # Phyllotaxis positioning
        angle = i * golden_angle
        # Outer leaves are created first (index 0), inner last.
        # Use sqrt for more natural distribution from center
        radius = base_radius + (math.sqrt(i) * 0.15)
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        z = i * 0.02
        
        # Progress: 0 is oldest/outermost, 1 is youngest/innermost
        progress = i / num_leaves
        length = max_leaf_length * (1.2 - progress * 0.5)
        width = max_leaf_width * (1.0 - progress * 0.3)
        
        # Construct leaf geometry using BMesh
        bm = bmesh.new()
        segments = 16
        vertices_pairs = []
        
        for s in range(segments + 1):
            t = s / segments # normalized length from base (0) to tip (1)
            
            # Tapering: wide at base, pointed at tip
            cur_w = width * (1.0 - t**1.5) if t < 1.0 else 0
            if t == 1.0: cur_w = 0
            
            # Spine curvature: arch outward then curve slightly down
            dist_y = t * length * 0.9
            dist_z = (t * length * 0.4) - (t**2 * length * 0.3)
            
            # Create two vertices for the width of the leaf
            v1 = bm.verts.new(Vector((-cur_w/2, dist_y, dist_z)))
            v2 = bm.verts.new(Vector((cur_w/2, dist_y, dist_z)))
            vertices_pairs.append((v1, v2))
            
        # Create the faces for the surface of the leaf
        for s in range(segments):
            bm.faces.new((vertices_pairs[s][0], vertices_pairs[s+1][0], 
                          vertices_pairs[s+1][1], vertices_pairs[s][1]))

        # Give the leaf thickness via extrusion
        # We select all current faces and extrude them along their normals
        bm.faces.ensure_lookup_table()
        extrude_geom = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
        
        # Offset the extruded vertices to create volume
        verts_to_move = [v for v in extrude_geom['geom'] if isinstance(v, bmesh.types.BMVert)]
        for v in verts_to_move:
            # Approximate normal by moving along local Z axis or calculated face normals
            # For a simple flat-ish leaf, we can move them roughly "down" locally
            v.co.z -= leaf_thickness

        # Finalize the leaf mesh
        leaf_mesh = bpy.data.meshes.new(f"LeafMesh_{i}")
        bm.to_mesh(leaf_mesh)
        bm.free()
        
        leaf_obj = bpy.data.objects.new(f"Leaf_{i}", leaf_mesh)
        bpy.context.collection.objects.link(leaf_obj)
        
        # Position and rotate the leaf
        # The leaf was built extending along the Y axis from (0,0,0)
        # We want it to point away from the center (x,y,z)
        target_vec = Vector((x, y, z))
        if target_vec.length > 0:
            # Align leaf's local Y axis with the vector from origin to position
            rot_quat = target_vec.to_track_quat('Y', 'Z')
            leaf_obj.rotation_mode = 'QUATERNION'
            leaf_obj.rotation_quaternion = rot_quat
        
        # Add some random tilt for organic feel
        leaf_obj.rotation_euler[0] += random.uniform(-0.1, 0.1)
        leaf_obj.rotation_euler[2] += random.uniform(-0.1, 0.1)
        
        leaf_obj.location = target_vec
        
        # Apply material with subtle variation
        mat = create_material(f"Mat_Leaf_{i}", get_random_green())
        leaf_obj.data.materials.append(mat)

    # Optional: slightly vary scale of leaves for realism
    for obj in bpy.data.objects:
        if "Leaf_" in obj.name:
            s = 1.0 + random.uniform(-0.1, 0.1)
            obj.scale = (s, s, s)

if __name__ == "__main__":
    clear_scene()
    create_agave()
