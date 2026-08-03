import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
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
    node_principled.inputs['Roughness'].default_value = 0.8
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_mushroom():
    # Materials: Distinct beige-tan and dark brown/black
    mat_top = create_material("MushroomTop", (0.7, 0.6, 0.4, 1.0))  # Clearer beige-tan
    mat_bottom = create_material("MushroomGills", (0.05, 0.03, 0.02, 1.0)) # Dark brown

    # 1. Create the main dome
    bm = bmesh.new()
    # High resolution for organic smoothness
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=1.0)
    
    for v in bm.verts:
        # Flatten the sphere into a cap shape (convex dome)
        v.co.z *= 0.4
        
        # Calculate polar coordinates for pattern generation
        angle = math.atan2(v.co.y, v.co.x)
        dist = Vector((v.co.x, v.co.y, 0)).length
        
        # Subtle "organic wavy line patterns" - reducing amplitude to avoid 'bun' look
        # Combine radial and spiral frequencies for organic feel
        wave = (
            0.03 * math.sin(12 * angle + dist * 5) + 
            0.02 * math.cos(20 * angle - dist * 8)
        )
        v.co.z += wave
        
        # Subtle organic irregularity in the silhouette
        irregularity = 0.04 * math.sin(dist * 4 + angle * 3)
        v.co.x += (v.co.x / (dist + 0.1)) * irregularity if dist > 0 else 0
        v.co.y += (v.co.y / (dist + 0.1)) * irregularity if dist > 0 else 0

    # Cut the sphere to create a hollow cap (remove bottom half)
    verts_to_delete = [v for v in bm.verts if v.co.z < -0.05]
    bmesh.ops.delete(bm, geom=verts_to_delete)
    
    mesh_data = bpy.data.meshes.new("MushroomCapMesh")
    bm.to_mesh(mesh_data)
    cap_obj = bpy.data.objects.new("MushroomCap", mesh_data)
    bpy.context.collection.objects.link(cap_obj)
    cap_obj.data.materials.append(mat_top)
    bm.free()

    # 2. Create the Gills (radial plates)
    gill_bm = bmesh.new()
    num_gills = 72 # Increased density for better representation
    segments_per_gill = 12
    gill_depth = 0.3  # Make them deeper so they are visible in renders

    for i in range(num_gills):
        theta = (i / num_gills) * 2 * math.pi
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        
        # Create a radial plate from center to rim
        verts_top = []
        verts_bottom = []
        for s in range(segments_per_gill + 1):
            r = (s / segments_per_gill) * 0.98 # Reach near the edge of cap
            # Gills dip slightly and then curve down
            z_off = -0.05 - (math.sin((s/segments_per_gill)*math.pi) * gill_depth)
            
            v_t = gill_bm.verts.new(Vector((r * cos_t, r * sin_t, z_off)))
            # Give the plates a tiny bit of thickness for rendering stability
            v_b = gill_bm.verts.new(Vector((r * cos_t, r * sin_t, z_off - 0.01)))
            
            verts_top.append(v_t)
            verts_bottom.append(v_b)
        
        # Bridge the top and bottom vertices to form faces
        for s in range(segments_per_gill):
            try:
                gill_bm.faces.new([verts_top[s], verts_top[s+1], verts_bottom[s+1], verts_bottom[s]])
            except ValueError:
                pass

    gill_mesh_data = bpy.data.meshes.new("MushroomGillsMesh")
    gill_bm.to_mesh(gill_mesh_data)
    gill_obj = bpy.data.objects.new("Gills", gill_mesh_data)
    bpy.context.collection.objects.link(gill_obj)
    gill_obj.data.materials.append(mat_bottom)
    gill_bm.free()

    # Join the pieces into one object
    bpy.context.view_layer.objects.active = cap_obj
    cap_obj.select_set(True)
    gill_obj.select_set(True)
    bpy.ops.object.join()

    # Final polishing
    for poly in cap_obj.data.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    clear_scene()
    create_mushroom()
