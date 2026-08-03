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
        # Seaweed is organic and slightly wet/slimy
        bsdf.inputs['Roughness'].default_value = 0.25
        bsdf.inputs['Specular IOR Level'].default_value = 0.5
    return mat

def create_holdfast():
    """Creates a substantial dark, irregular base for the seaweed."""
    bm = bmesh.new()
    # Create a distorted sphere to represent a root holdfast
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=0.7)
    
    for v in bm.verts:
        # Randomize vertices for an organic, rocky/root look
        v.co += Vector((random.uniform(-0.3, 0.3), 
                        random.uniform(-0.3, 0.3), 
                        random.uniform(-0.3, 0.3)))
        # Flatten the bottom and splay it slightly
        if v.co.z < 0:
            v.co.z *= 0.5
            v.co.x *= 1.2
            v.co.y *= 1.2

    mesh = bpy.data.meshes.new("Holdfast")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Holdfast", mesh)
    bpy.context.collection.objects.link(obj)
    mat = create_material("RootMat", (0.03, 0.02, 0.01, 1.0))
    obj.data.materials.append(mat)
    return obj

def create_broad_blade(name, height=5.0, width=1.4):
    """Creates a broad seaweed blade with distinct lobes and ruffles."""
    bm = bmesh.new()
    res_u = 20 # across width (higher for better ruffling)
    res_v = 40 # along length (higher for smoother curvature)
    
    verts = []
    for v_idx in range(res_v):
        t = v_idx / (res_v - 1) # normalized height 0 to 1
        z_pos = t * height
        
        # LOBING: Width varies along the length of the blade
        # Combine a main envelope with higher frequency noise for lobed edges
        envelope = math.sin(t * math.pi)
        lobe_variation = 1.0 + 0.3 * math.sin(t * 7.5 + random.uniform(0, 1))
        current_width = envelope * width * lobe_variation
        
        for u_idx in range(res_u):
            # Normalized coordinate from -1 to 1 across the blade
            u = (u_idx / (res_u - 1)) * 2 - 1
            x_pos = u * current_width * 0.5
            
            # RUFFLING: Displacement perpendicular to the leaf surface
            # Combine several sines for an organic, ruffled effect
            ruffle = 0.4 * math.sin(u * 4 + t * 8)
            ruffle += 0.2 * math.cos(u * 8 - t * 5)
            ruffle *= (1.0 - abs(u)**2) # Taper ruffles toward edges slightly or keep them strong
            
            # CURVATURE: Organic bend as it grows upward
            # The spine of the leaf curves in a random direction
            curve_x = 0.8 * math.sin(t * 1.5 + random.uniform(0, 0.2))
            curve_y = 0.6 * math.cos(t * 1.2 + random.uniform(0, 0.2))
            
            # Final vertex position: Height is Z, width/ruffle on X/Y plane
            # We treat the leaf as roughly in the XZ plane and displace into Y
            final_x = x_pos + curve_x
            final_y = ruffle + curve_y
            final_z = z_pos
            
            verts.append(bm.verts.new((final_x, final_y, final_z)))

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
    
    # Create the dark root base
    create_holdfast()
    
    # Deep green color for seaweed
    leaf_mat = create_material("SeaweedMat", (0.04, 0.25, 0.06, 1.0))
    
    num_fronds = 8
    for f in range(num_fronds):
        # Randomized dimensions for each frond
        h = random.uniform(4.5, 6.5)
        w = random.uniform(1.0, 1.8)
        blade = create_broad_blade(f"Frond_{f}", height=h, width=w)
        bpy.context.collection.objects.link(blade)
        
        # Distribution around the base
        angle = (f / num_fronds) * 2 * math.pi + random.uniform(-0.4, 0.4)
        blade.rotation_euler[2] = angle
        
        # Lean fronds outward slightly from center
        blade.rotation_euler[0] = random.uniform(-0.4, 0.4)
        blade.rotation_euler[1] = random.uniform(-0.4, 0.4)
        
        blade.location = (0, 0, 0)
        blade.data.materials.append(leaf_mat)

if __name__ == "__main__":
    create_seaweed()
