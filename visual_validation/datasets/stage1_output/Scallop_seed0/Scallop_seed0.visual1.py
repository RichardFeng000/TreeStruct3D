import bpy
import bmesh
import math
from mathutils import Vector

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

def create_scallop_valve(name, is_top=False, materials=None):
    # Resolution
    res_r = 60 # radial (growth rings)
    res_theta = 60 # angular (ribs)
    
    bm = bmesh.new()
    
    # Parameters for shell shape
    radius = 1.0
    height_scale = 0.3
    rib_count = 12
    ring_count = 8
    
    verts = []
    for i in range(res_r + 1):
        u = i / res_r # distance from hinge [0, 1]
        row = []
        for j in range(res_theta + 1):
            # theta ranges from -pi/3 to pi/3 for a fan shape
            theta = (j / res_theta) * (2 * math.pi / 3) - (math.pi / 3)
            
            # Basic Fan Coordinates
            x = u * math.cos(theta)
            y = u * math.sin(theta)
            
            # Dome height: quadratic curve that is 0 at center and edges
            z_dome = 4 * height_scale * u * (1 - u) # This creates a bulge in the middle
            # Actually, scallop shells are more like shallow bowls with highest point near hinge
            z_dome = height_scale * (1 - u**2)
            
            # Radial ribs: vary based on theta
            z_ribs = 0.05 * math.sin(rib_count * theta) * (u**0.5)
            
            # Growth rings: vary based on u
            z_rings = 0.02 * math.sin(ring_count * math.pi * u)
            
            z = z_dome + z_ribs + z_rings
            if is_top:
                z = -z
            
            v = bm.verts.new(Vector((x, y, z)))
            row.append(v)
        verts.append(row)

    # Create faces
    for i in range(res_r):
        for j in range(res_theta):
            face = bm.faces.new((
                verts[i][j], 
                verts[i+1][j], 
                verts[i+1][j+1], 
                verts[i][j+1]
            ))
            # Assign material based on u for growth ring colors (alternating cream/brown)
            if materials:
                mat_idx = 0 if (int(i / (res_r // ring_count)) % 2 == 0) else 1
                face.material_index = mat_idx

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    # Give it thickness and smooth it out
    subdiv = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subdiv.levels = 1
    
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.03
    solid.offset = -1
    # Offset material index for the interior (inner surface)
    solid.material_offset = 2 
    
    return obj

def assemble_scallop():
    clear_scene()
    
    # Create Materials
    # Index 0: Cream, Index 1: Brown, Index 2: Dark Interior
    mat_cream = create_material("Cream", (0.95, 0.9, 0.8, 1.0))
    mat_brown = create_material("Brown", (0.6, 0.4, 0.3, 1.0))
    mat_dark = create_material("DarkInterior", (0.2, 0.15, 0.1, 1.0))
    
    mats = [mat_cream, mat_brown, mat_dark]
    
    # Create valves
    valve_bottom = create_scallop_valve("Valve_Bottom", is_top=False, materials=mats)
    valve_top = create_scallop_valve("Valve_Top", is_top=True, materials=mats)
    
    # Assign materials to the objects
    for v in [valve_bottom, valve_top]:
        for m in mats:
            v.data.materials.append(m)

    # Position for "partially open" look
    # Hinge is at (0,0,z). We rotate around the Y axis (the hinge line).
    open_angle = math.radians(40)
    valve_top.rotation_euler[1] = open_angle
    
    # Adjust whole object for 3/4 perspective presentation
    for v in [valve_bottom, valve_top]:
        v.rotation_euler[0] = math.radians(-15)
        v.rotation_euler[2] = math.radians(20)

if __name__ == "__main__":
    assemble_scallop()
