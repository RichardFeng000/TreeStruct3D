import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Base Color'].default_value = color
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_mushroom_cap():
    # 1. Setup Materials
    mat_top = create_material("MushroomTop", (0.85, 0.78, 0.65, 1.0))  # Beige-tan
    mat_bottom = create_material("MushroomGills", (0.05, 0.04, 0.03, 1.0)) # Dark brown/black

    # 2. Create the main dome using BMesh
    bm = bmesh.new()
    # Higher resolution for better organic deformation
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=1.0)
    
    # Transform the sphere into an irregular dome
    for v in bm.verts:
        # Flatten Z to make it a cap (oblate spheroid look)
        v.co.z *= 0.5
        
        # Add some organic irregularity/noise using trig functions to avoid purely random jitter
        angle = math.atan2(v.co.y, v.co.x)
        dist = Vector((v.co.x, v.co.y, 0)).length
        
        # Organic wavy line patterns (ridges) on the surface
        wave = 0.05 * math.sin(10 * angle + dist * 5) + 0.03 * math.cos(6 * angle - dist * 8)
        v.co.z += wave
        
        # General organic irregularity (slight wobble)
        v.co.x += 0.02 * math.sin(v.co.z * 10 + v.co.y * 5)
        v.co.y += 0.02 * math.cos(v.co.z * 10 + v.co.x * 5)

    # Remove the bottom half of the sphere to leave an opening for gills
    verts_to_delete = [v for v in bm.verts if v.co.z < -0.05]
    bmesh.ops.delete(bm, geom=verts_to_delete)
    
    # Create the mesh object for the cap top
    mesh_data = bpy.data.meshes.new("MushroomCapTop")
    bm.to_mesh(mesh_data)
    cap_obj = bpy.data.objects.new("MushroomCap", mesh_data)
    bpy.context.collection.objects.link(cap_obj)
    cap_obj.data.materials.append(mat_top)
    bm.free()

    # 3. Create the Gills (the underside structure)
    gill_bm = bmesh.new()
    num_gills = 100 # Dense radial gill structures
    gill_thickness = 0.008
    segments_per_gill = 24

    for i in range(num_gills):
        theta = (i / num_gills) * 2 * math.pi
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        
        # Create a radial strip for each gill
        verts = []
        for s in range(segments_per_gill + 1):
            r = (s / segments_per_gill) * 0.98 # Slightly inside the cap edge
            
            # Gills curve slightly upwards as they reach the edges of the dome
            z = -0.05 + (r * r * 0.15)
            
            # Small offset for thickness
            offset_x = -sin_t * gill_thickness / 2
            offset_y = cos_t * gill_thickness / 2
            
            v1 = gill_bm.verts.new(Vector((r * cos_t + offset_x, r * sin_t + offset_y, z)))
            v2 = gill_bm.verts.new(Vector((r * cos_t - offset_x, r * sin_t - offset_y, z)))
            verts.append((v1, v2))
        
        # Connect the vertices to form faces for this gill strip
        for s in range(segments_per_gill):
            try:
                gill_bm.faces.new([verts[s][0], verts[s+1][0], verts[s+1][1], verts[s][1]])
            except ValueError:
                # Skip if face already exists or is degenerate
                pass 

    # Create the mesh object for the gills
    gill_mesh_data = bpy.data.meshes.new("MushroomGills")
    gill_bm.to_mesh(gill_mesh_data)
    gill_obj = bpy.data.objects.new("Gills", gill_mesh_data)
    bpy.context.collection.objects.link(gill_obj)
    gill_obj.data.materials.append(mat_bottom)
    gill_bm.free()

    # Join the cap and gills into one object
    bpy.context.view_layer.objects.active = cap_obj
    cap_obj.select_set(True)
    gill_obj.select_set(True)
    bpy.ops.object.join()

    # Final cleanup: ensure the combined object is at origin and has smooth shading
    cap_obj.location = (0, 0, 0)
    
    # Smooth shading for organic look
    for poly in cap_obj.data.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    clear_scene()
    create_mushroom_cap()
