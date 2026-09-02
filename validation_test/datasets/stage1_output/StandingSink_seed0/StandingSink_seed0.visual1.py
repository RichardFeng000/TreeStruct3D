import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Creates a basic Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def bmesh_to_obj(name, bm):
    """Helper to convert BMesh to a Blender object."""
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_basin():
    """Creates a flared square basin with rounded corners."""
    # Dimensions
    w, d, h = 0.65, 0.5, 0.2
    wall = 0.03
    radius = 0.12
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale to basic dimensions
    for v in bm.verts:
        v.co.x *= (w / 2)
        v.co.y *= (d / 2)
        v.co.z *= (h / 2)
        
    # Flare the top (Z > 0)
    top_verts = [v for v in bm.verts if v.co.z > 0]
    for v in top_verts:
        v.co.x *= 1.1
        v.co.y *= 1.1
        
    # Bevel edges for rounded corners (Verticals)
    edges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.05]
    bmesh.ops.bevel(bm, geom=edges, offset=radius, segments=4, affect='EDGES')

    # Create the bowl hole
    top_face = None
    for f in bm.faces:
        if f.normal.z > 0.9:
            top_face = f
            break
            
    if top_face:
        res = bmesh.ops.inset_individual(bm, faces=[top_face], thickness=wall)
        inner_face = res['faces'][0]
        # Push the inner face down to create the hollow part
        bmesh.ops.translate(bm, verts=inner_face.verts, vec=(0, 0, -h * 0.8))
        # Slightly bevel the bottom of the interior bowl for smoothness
        bottom_edges = [e for e in bm.edges if abs(e.verts[0].co.z - (-h/2 + wall)) < 0.01]
        bmesh.ops.bevel(bm, geom=bottom_edges, offset=0.02, segments=2)

    obj = bmesh_to_obj("Basin", bm)
    bm.free()
    return obj

def create_pedestal():
    """Creates the tapered central column with a square base."""
    p_h = 0.85
    b_w = 0.4
    t_w = 0.2
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Initial scaling
    for v in bm.verts:
        v.co.z *= (p_h / 2)
        v.co.x *= (b_w / 2)
        v.co.y *= (b_w / 2)

    # Taper the top vertices
    top_verts = [v for v in bm.verts if v.co.z > 0]
    for v in top_verts:
        v.co.x *= (t_w / b_w)
        v.co.y *= (t_w / b_w)

    # Add support loops to prevent 'egg' shape when subdivided
    # We do this by extruding/insetting slightly at top and bottom faces
    for face in [f for f in bm.faces if abs(f.normal.z) > 0.9]:
        bmesh.ops.inset_individual(bm, faces=[face], thickness=0.02)

    obj = bmesh_to_obj("Pedestal", bm)
    # Position it so the top meets the bottom of the basin (which is at -h/2)
    # Pedestal center Z = - (p_h / 2 + h / 2) where h is basin height (0.2)
    obj.location.z = -(p_h / 2 + 0.1)
    bm.free()
    return obj

def create_faucet():
    """Creates a chrome gooseneck faucet with handles."""
    chrome_mat = create_material("Chrome", (0.8, 0.8, 0.8, 1), metallic=1.0, roughness=0.1)
    
    # Base plate
    bm_base = bmesh.new()
    bmesh.ops.create_cube(bm_base, size=1.0)
    for v in bm_base.verts:
        v.co.x *= 0.12; v.co.y *= 0.06; v.co.z *= 0.02
    obj_base = bmesh_to_obj("FaucetBase", bm_base)
    # Place at the back edge of the basin (basin depth is ~0.5, so y=0.25 approx)
    obj_base.location = Vector((0, 0.22, 0.1))
    obj_base.data.materials.append(chrome_mat)
    bm_base.free()

    # Gooseneck pipe using a cylinder/cone
    radius = 0.018
    bm_neck = bmesh.new()
    bmesh.ops.create_cone(bm_neck, cap_ends=True, segments=16, radius1=radius, radius2=radius, depth=0.35)
    
    # Deform the cylinder into a curve
    for v in bm_neck.verts:
        z = v.co.z + 0.175 # Move origin to bottom of pipe
        if z > 0.05:
            # Simple arc approximation
            angle = (z / 0.3) * math.pi / 2
            v.co.y += math.sin(angle) * 0.1
            v.co.z -= (z * 0.2) # Tilt slightly down at the end

    obj_neck = bmesh_to_obj("FaucetNeck", bm_neck)
    obj_neck.location = Vector((0, 0.22, 0.1))
    obj_neck.data.materials.append(chrome_mat)
    bm_neck.free()

    # Handles
    for side in [-1, 1]:
        bm_h = bmesh.new()
        bmesh.ops.create_cube(bm_h, size=1.0)
        for v in bm_h.verts:
            v.co.x *= 0.04; v.co.y *= 0.04; v.co.z *= 0.08
        obj_h = bmesh_to_obj(f"Handle_{side}", bm_h)
        obj_h.location = Vector((side * 0.07, 0.22, 0.14))
        obj_h.data.materials.append(chrome_mat)
        bm_h.free()

def main():
    clear_scene()

    # Dark Forest Green glossy ceramic
    ceramic_mat = create_material("ForestGreen", (0.02, 0.15, 0.04, 1), metallic=0.0, roughness=0.1)

    basin = create_basin()
    pedestal = create_pedestal()
    create_faucet()

    basin.data.materials.append(ceramic_mat)
    pedestal.data.materials.append(ceramic_mat)

    # Refine geometry with subdivision but ensure it's not too aggressive
    for obj in [basin, pedestal]:
        mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
        mod.levels = 1 # Lowered to keep the square structure visible
        mod.render_levels = 2
        
        for poly in obj.data.polygons:
            poly.use_smooth = True

if __name__ == "__main__":
    main()
