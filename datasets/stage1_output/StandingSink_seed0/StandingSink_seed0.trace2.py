import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears all default objects from the scene."""
    if "Cube" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
    if "Camera" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Camera"], do_unlink=True)
    if "Light" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Light"], do_unlink=True)
    # Ensure all other objects are gone too
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
    """Creates the flared square basin with rounded corners."""
    width = 0.6
    depth = 0.5
    height = 0.2
    wall_thickness = 0.03
    corner_radius = 0.1

    bm = bmesh.new()
    # Create main outer volume as a cube
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale to basin dimensions
    for v in bm.verts:
        v.co.x *= (width / 2)
        v.co.y *= (depth / 2)
        v.co.z *= (height / 2)

    # Flare top vertices outwards slightly for the "flared" look
    top_verts = [v for v in bm.verts if v.co.z > 0]
    for v in top_verts:
        v.co.x *= 1.15
        v.co.y *= 1.15

    # Bevel the four vertical corners to make it rounded-square
    verticals = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.1]
    bmesh.ops.bevel(bm, geom=verticals, offset=corner_radius, segments=8, affect='EDGES')

    # Find top face to create the bowl
    top_face = None
    for f in bm.faces:
        if f.normal.z > 0.9:
            top_face = f
            break
    
    if top_face:
        # Inset and extrude down to make a basin hole
        res = bmesh.ops.inset_individual(bm, faces=[top_face], thickness=wall_thickness)
        inner_face = res['faces'][0]
        # Extrude downwards (negative Z)
        bmesh.ops.translate(bm, verts=inner_face.verts, vec=(0, 0, - (height * 0.85)))
        
        # Create a floor for the basin by adding a face if needed, but here we just move vertices
        # To make it a real bowl, let's refine: inset again at the bottom or just leave as is
        # For simplicity in bmesh, let's keep this extruded volume.

    obj = bmesh_to_obj("Basin", bm)
    bm.free()
    return obj

def create_pedestal():
    """Creates the tapered central column."""
    p_height = 0.8
    base_width = 0.45
    top_width = 0.25
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    for v in bm.verts:
        v.co.z *= (p_height / 2)
        v.co.x *= (base_width / 2)
        v.co.y *= (base_width / 2)

    # Taper the top vertices
    top_verts = [v for v in bm.verts if v.co.z > 0]
    for v in top_verts:
        v.co.x *= (top_width / base_width)
        v.co.y *= (top_width / base_width)

    # Bevel bottom edges for a softer look at the floor contact
    bottom_edges = [e for e in bm.edges if abs(e.verts[0].co.z + p_height/2) < 0.01]
    bmesh.ops.bevel(bm, geom=bottom_edges, offset=0.03, segments=4)

    obj = bmesh_to_obj("Pedestal", bm)
    # Position the pedestal so it sits under the basin (basin is at origin and extends +/- 0.1Z)
    # Basin bottom is at -0.1Z. Pedestal should go from -0.1 to -0.9.
    obj.location.z = - (p_height / 2 + 0.1)
    bm.free()
    return obj

def create_faucet():
    """Creates a chrome gooseneck faucet with two handles."""
    chrome_mat = create_material("Chrome", (0.8, 0.8, 0.8, 1), metallic=1.0, roughness=0.1)
    
    # Faucet Base Plate
    bm_base = bmesh.new()
    bmesh.ops.create_cube(bm_base, size=1.0)
    for v in bm_base.verts:
        v.co.x *= 0.08
        v.co.y *= 0.05
        v.co.z *= 0.02
    obj_base = bmesh_to_obj("FaucetBase", bm_base)
    # Position at the back edge of the basin (basin depth is approx 0.5, so y = -0.2 to -0.3)
    obj_base.location = Vector((0, -0.21, 0.1))
    obj_base.data.materials.append(chrome_mat)
    bm_base.free()

    # Gooseneck Pipe using a cylinder (cone with same radii)
    radius = 0.015
    bm_neck = bmesh.new()
    # Blender 5.0: create_cone uses radius1, radius2, and depth
    bmesh.ops.create_cone(bm_neck, cap_ends=True, segments=16, radius1=radius, radius2=radius, depth=0.3)
    
    # Bend the cylinder into a gooseneck shape by manipulating vertices
    # The default cone is created along Z axis from -depth/2 to +depth/2
    for v in bm_neck.verts:
        z = v.co.z + 0.15 # Shift so bottom is at local 0
        if z > 0.1:
            # Create a curve effect
            bend = (z - 0.1) * 0.6
            v.co.y += bend
            if z > 0.2:
                # Curve back down
                v.co.z -= (z - 0.2) * 0.5
    
    obj_neck = bmesh_to_obj("FaucetNeck", bm_neck)
    obj_neck.location = Vector((0, -0.21, 0.1))
    obj_neck.data.materials.append(chrome_mat)
    bm_neck.free()

    # Handles (left and right)
    for side in [-1, 1]:
        bm_h = bmesh.new()
        bmesh.ops.create_cube(bm_h, size=1.0)
        for v in bm_h.verts:
            v.co.x *= 0.03
            v.co.y *= 0.03
            v.co.z *= 0.06
        obj_h = bmesh_to_obj(f"Handle_{side}", bm_h)
        # Offset handles to the left and right of the base plate
        obj_h.location = Vector((side * 0.08, -0.21, 0.13))
        obj_h.data.materials.append(chrome_mat)
        bm_h.free()

def main():
    clear_scene()

    # Materials: Dark Forest Green glossy ceramic (very dark green)
    ceramic_mat = create_material("ForestGreenCeramic", (0.01, 0.06, 0.02, 1), metallic=0.0, roughness=0.05)

    # Build Components
    basin = create_basin()
    pedestal = create_pedestal()
    create_faucet()

    # Assign Material to ceramic parts
    basin.data.materials.append(ceramic_mat)
    pedestal.data.materials.append(ceramic_mat)

    # Add Subdivision Surface and smoothing for a high-end polished look
    for obj in [basin, pedestal]:
        mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
        mod.levels = 2
        mod.render_levels = 2
        
        # Smooth shading
        for poly in obj.data.polygons:
            poly.use_smooth = True

if __name__ == "__main__":
    main()
