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
    # Add some slight roughness/specular for a shell look
    node_principled.inputs['Roughness'].default_value = 0.3
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_scallop_valve(name, is_bottom=True):
    # Parameters
    res_r = 40  # radial resolution for growth rings
    res_theta = 60 # angular resolution for ribs
    radius = 1.2
    ribs_count = 14
    rings_count = 10
    dome_height = 0.4
    
    bm = bmesh.new()
    
    verts = []
    for i in range(res_r + 1):
        u = i / res_r  # Normalize radius [0, 1]
        row = []
        for j in range(res_theta + 1):
            # theta from -pi/3 to pi/3 (approx 120 degrees)
            theta = (j / res_theta) * (2 * math.pi / 3) - (math.pi / 3)
            
            # Scallop shells are more oval than circular sectors
            # We scale the radius based on theta to make it wider/rounded
            r_scale = 1.0 + 0.2 * math.sin(theta)**2
            x = u * radius * r_scale * math.cos(theta)
            y = u * radius * r_scale * math.sin(theta)
            
            # Dome: Convex shape, highest in center, lower at hinge and edges
            # Z is 0 at the hinge (u=0) and outer edge (u=1), peak in middle
            z_dome = dome_height * (1 - (2*u-1)**2) 
            
            # Ribs: Radial ridges
            z_ribs = 0.06 * math.cos(ribs_count * theta) * u
            
            # Rings: Concentric growth patterns
            z_rings = 0.03 * math.sin(rings_count * 2 * math.pi * u)
            
            z = z_dome + z_ribs + z_rings
            if not is_bottom: # Flip for top valve
                z = -z
            
            v = bm.verts.new(Vector((x, y, z)))
            row.append(v)
        verts.append(row)

    # Create faces and assign material indices based on growth rings
    for i in range(res_r):
        for j in range(res_theta):
            face = bm.faces.new((
                verts[i][j], 
                verts[i+1][j], 
                verts[i+1][j+1], 
                verts[i][j+1]
            ))
            # Alternating cream (0) and brown (1) growth rings
            face.material_index = 0 if (int(i / (res_r // (rings_count * 2))) % 2 == 0) else 1

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    # Ensure the hinge is at (0,0,0) for rotation
    # Our current coordinate system puts u=0 at x=0, y=0.
    
    # Smooth shading
    for poly in obj.data.polygons:
        poly.use_smooth = True
        
    # Give it thickness and define the inner surface material (index 2)
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.04
    solid.offset = -1
    solid.material_offset = 2 # Interior material index
    
    return obj

def assemble_scallop():
    clear_scene()
    
    # Materials: Index 0=Cream, 1=Brown, 2=DarkInterior
    mat_cream = create_material("Cream", (0.95, 0.88, 0.75, 1.0))
    mat_brown = create_material("Brown", (0.5, 0.35, 0.2, 1.0))
    mat_dark = create_material("DarkInterior", (0.2, 0.18, 0.15, 1.0))
    
    mats = [mat_cream, mat_brown, mat_dark]
    
    # Create valves
    v_bottom = create_scallop_valve("Valve_Bottom", is_bottom=True)
    v_top = create_scallop_valve("Valve_Top", is_bottom=False)
    
    for v in [v_bottom, v_top]:
        for m in mats:
            v.data.materials.append(m)

    # The hinge point for both is at (0, 0, 0). 
    # Rotate the top valve to "open" it.
    # We rotate around X axis since our fan extends along Y/Z mostly.
    # Actually, looking at coordinates: x=cos(theta), y=sin(theta). Hinge is (0,0,z)
    # The hinge line is the Z-axis if we aren't careful, but here it's actually 
    # the origin point since theta varies. To make a "hinge" as a line:
    # Let's align the shells so they rotate around the Y axis (the width of the fan).
    # Wait, in our current setup, u=0 is the point (0,0,0). 
    # The 'line' for the hinge should be the X-axis or similar.
    # Let's simply shift and rotate them.
    
    v_top.rotation_euler[1] = math.radians(45) # Open angle
    v_bottom.rotation_euler[1] = math.radians(-10) # Slight tilt for bottom
    
    # Final orientation for a 3/4 perspective render
    container = bpy.data.objects.new("Container", None)
    bpy.context.collection.objects.link(container)
    v_bottom.parent = container
    v_top.parent = container
    
    container.rotation_euler[0] = math.radians(-20)
    container.rotation_euler[2] = math.radians(30)

if __name__ == "__main__":
    assemble_scallop()
