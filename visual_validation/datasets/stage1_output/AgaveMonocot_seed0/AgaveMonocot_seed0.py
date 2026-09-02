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
    node_bsdf.inputs['Roughness'].default_value = 0.6
    # Give it a slightly waxy look
    if 'Specular' in node_bsdf.inputs:
        node_bsdf.inputs['Specular'].default_value = 0.5
    
    links = mat.node_tree.links
    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_agave():
    # Parameters for the agave plant
    num_leaves = 70
    golden_angle = 137.5 * (math.pi / 180)
    max_leaf_length = 3.0
    max_leaf_width = 0.3  # Width of the fleshy base
    max_leaf_thickness = 0.15 # Thickness of the fleshy base
    
    green_dark = (0.04, 0.18, 0.04, 1.0)
    green_mid = (0.12, 0.35, 0.1, 1.0)
    green_light = (0.3, 0.5, 0.2, 1.0)

    def get_random_green():
        t = random.random()
        if t < 0.6:
            f = random.random()
            return (
                green_dark[0] + f * (green_mid[0] - green_dark[0]),
                green_dark[1] + f * (green_mid[1] - green_dark[1]),
                green_dark[2] + f * (green_mid[2] - green_dark[2]),
                1.0
            )
        else:
            f = random.random()
            return (
                green_mid[0] + f * (green_light[0] - green_mid[0]),
                green_mid[1] + f * (green_light[1] - green_mid[1]),
                green_mid[2] + f * (green_light[2] - green_mid[2]),
                1.0
            )

    # Create central base
    bm_base = bmesh.new()
    bmesh.ops.create_uvsphere(bm_base, u_segments=16, v_segments=8, radius=0.3)
    for v in bm_base.verts:
        v.co.z *= 0.5
    
    base_mesh = bpy.data.meshes.new("AgaveBaseMesh")
    bm_base.to_mesh(base_mesh)
    bm_base.free()
    base_obj = bpy.data.objects.new("AgaveBase", base_mesh)
    bpy.context.collection.objects.link(base_obj)
    base_obj.data.materials.append(create_material("RootMat", green_dark))

    # Create leaves in a spiral pattern
    for i in range(num_leaves):
        angle = i * golden_angle
        
        # Compact rosette: origins close to center, slightly staggered
        start_radius = 0.05 + (i * 0.002)
        x = math.cos(angle) * start_radius
        y = math.sin(angle) * start_radius
        z = i * 0.015 # Gradual rise in center
        
        # Progress: youngest leaves are smallest/innermost (higher index i)
        # Older leaves are larger and more outer.
        age_factor = 1.0 - (i / num_leaves)
        length = max_leaf_length * (0.6 + age_factor * 0.4)
        width = max_leaf_width * (0.7 + age_factor * 0.3)
        thickness = max_leaf_thickness * (0.7 + age_factor * 0.3)
        
        bm = bmesh.new()
        segments = 12 # longitudinal divisions
        ring_res = 8   # cross-section resolution
        
        prev_ring = []
        
        for s in range(segments + 1):
            t = s / segments
            
            # Tapering: fleshier at base, very pointed at tip
            w_t = width * (1.0 - t**1.2) if t < 1.0 else 0
            h_t = thickness * (1.0 - t**1.5) if t < 1.0 else 0
            
            # Curvature: arching outward and slightly downward/upward depending on age
            spine_y = t * length
            spine_z = (t**0.7 * length * 0.4) - (t**2 * length * 0.35)
            
            current_ring = []
            for r in range(ring_res):
                phi = (r / ring_res) * 2 * math.pi
                # Elliptical cross section to represent "thick" succulent leaves
                vx = math.cos(phi) * w_t
                vz = math.sin(phi) * h_t
                
                v = bm.verts.new(Vector((vx, spine_y, spine_z + vz)))
                current_ring.append(v)
            
            if s > 0:
                for r in range(ring_res):
                    v1 = prev_ring[r]
                    v2 = prev_ring[(r+1)%ring_res]
                    v3 = current_ring[(r+1)%ring_res]
                    v4 = current_ring[r]
                    try:
                        bm.faces.new((v1, v2, v3, v4))
                    except: pass # Handle duplicate faces at tip

            prev_ring = current_ring

        # Close the tip (degenerate point)
        if len(prev_ring) > 0 and segments > 0:
            bm.verts.ensure_lookup_table()
            # The last ring is very small, but we can merge them to a single point for a sharp tip
            tip = bm.verts.new(Vector((0, length, (1**0.7 * length * 0.4) - (1**2 * length * 0.35))))
            for r in range(ring_res):
                v1 = prev_ring[r]
                v2 = prev_ring[(r+1)%ring_res]
                try:
                    bm.faces.new((v1, v2, tip))
                except: pass

        leaf_mesh = bpy.data.meshes.new(f"LeafMesh_{i}")
        bm.to_mesh(leaf_mesh)
        bm.free()
        
        leaf_obj = bpy.data.objects.new(f"Leaf_{i}", leaf_mesh)
        bpy.context.collection.objects.link(leaf_obj)
        
        # Rotation to align with radiating direction from center
        target_vec = Vector((x, y, z))
        if target_vec.length > 0:
            rot_quat = target_vec.to_track_quat('Y', 'Z')
            leaf_obj.rotation_mode = 'QUATERNION'
            leaf_obj.rotation_quaternion = rot_quat
        
        # Organic variations
        leaf_obj.location = target_vec
        leaf_obj.rotation_euler[0] += random.uniform(-0.15, 0.15)
        leaf_obj.rotation_euler[2] += random.uniform(-0.1, 0.1)
        
        # Color variation
        mat = create_material(f"Mat_Leaf_{i}", get_random_green())
        leaf_obj.data.materials.append(mat)

if __name__ == "__main__":
    clear_scene()
    create_agave()
