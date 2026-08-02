import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple material with a specific color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        # Make seaweed slightly shiny/wet
        bsdf.inputs['Roughness'].default_value = 0.3
    return mat

def create_holdfast():
    """Creates a substantial dark base for the seaweed."""
    bm = bmesh.new()
    # Root clump: deformed sphere
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=0.6)
    
    for v in bm.verts:
        v.co += Vector((random.uniform(-0.2, 0.2), 
                        random.uniform(-0.2, 0.2), 
                        random.uniform(-0.2, 0.2)))
        if v.co.z < 0:
            v.co.z *= 0.4 # Flatten bottom

    mesh = bpy.data.meshes.new("Holdfast")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Holdfast", mesh)
    bpy.context.collection.objects.link(obj)
    mat = create_material("RootMat", (0.02, 0.01, 0.01, 1.0))
    obj.data.materials.append(mat)
    return obj

def create_broad_blade(name, height=4.0, width=1.2):
    """Creates a single broad, ruffled and lobed seaweed blade."""
    bm = bmesh.new()
    res_u = 16 # across width
    res_v = 32 # along length
    
    verts = []
    for v_idx in range(res_v):
        # Normalized coordinate from 0 to 1
        t = v_idx / (res_v - 1)
        y = t * height
        
        # Width variation: tapered at bottom and top, wider in middle-upper part
        # Use a smooth curve for the width profile
        w_profile = math.sin(t * math.pi) * width
        
        for u_idx in range(res_u):
            # Normalized coordinate from -1 to 1
            u = (u_idx / (res_u - 1)) * 2 - 1
            x = u * w_profile * 0.5
            
            # Ruffles and lobing: combine sines for organic feel
            # Z depends on position along blade (t) and across width (u)
            z = 0.15 * math.sin(u * 3 + t * 4) * (1 - abs(u))
            z += 0.2 * math.cos(t * 6) * u
            
            # General curvature: bend the blade as it grows upward
            bend_angle = t * 0.8 # radians
            # Rotate x, z around Y axis (roughly)
            final_x = x * math.cos(bend_angle) - z * math.sin(bend_angle)
            final_z = x * math.sin(bend_angle) + z * math.cos(bend_angle)
            # Add a global curve to the spine of the leaf
            final_x += 0.5 * math.sin(t * 2) 
            
            verts.append(bm.verts.new((final_x, 0, y))) # Use Z as height

    # Create faces
    for j in range(res_v - 1):
        for i in range(res_u - 1):
            try:
                bm.faces.new((verts[j * res_u + i], 
                              verts[j * res_u + i + 1], 
                              verts[(j + 1) * res_u + i + 1], 
                              verts[(j + 1) * res_u + i]))
            except:
                pass

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    return obj

def create_seaweed():
    clear_scene()
    
    # Root base
    create_holdfast()
    
    leaf_mat = create_material("SeaweedMat", (0.05, 0.3, 0.08, 1.0))
    
    num_fronds = 7
    for f in range(num_fronds):
        # Create a broad blade
        height = random.uniform(4.0, 6.0)
        width = random.uniform(0.8, 1.5)
        blade = create_broad_blade(f"Frond_{f}", height=height, width=width)
        bpy.context.collection.objects.link(blade)
        
        # Randomize rotation around the vertical axis
        angle = (f / num_fronds) * 2 * math.pi + random.uniform(-0.5, 0.5)
        blade.rotation_euler[2] = angle
        
        # Slight tilt in X or Y to create a cluster effect
        blade.rotation_euler[0] = random.uniform(-0.3, 0.3)
        blade.rotation_euler[1] = random.uniform(-0.3, 0.3)
        
        # Position it at the base
        blade.location = (0, 0, 0)
        
        blade.data.materials.append(leaf_mat)

if __name__ == "__main__":
    create_seaweed()
