import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clear the default scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.4):
    """Create a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Roughness'].default_value = roughness
    
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_mussel_valve(name):
    """
    Generates one valve of a mussel shell as an elongated teardrop.
    """
    bm = bmesh.new()
    
    # Parameters for a more realistic mussel shape
    res_long = 64
    res_arc = 32
    length = 5.0
    width_max = 2.2
    height_max = 1.8
    thickness = 0.1
    
    # Growth ring parameters - much subtler than previous iteration
    ring_freq = 8.0
    ring_amp = 0.03

    outer_verts = []
    for i in range(res_long + 1):
        u = i / res_long # distance from hinge [0, 1]
        
        # Teardrop profile: starts very small at u=0 and expands
        # Use a power function to create the tapered 'point' at the hinge
        swell = (u ** 0.7) 
        if u == 0: swell = 0.02 # Small but not zero for topology
        
        # Subtle concentric growth rings along the length
        ring_mod = 1.0 + ring_amp * math.sin(u * ring_freq * math.pi)
        
        w = width_max * swell * ring_mod
        h = height_max * swell * ring_mod
        z = u * length
        
        row = []
        for j in range(res_arc + 1):
            # Half-circle arc (0 to pi)
            theta = (j / res_arc) * math.pi
            x = w * math.cos(theta)
            y = h * math.sin(theta)
            row.append(bm.verts.new(Vector((x, y, z))))
        outer_verts.append(row)

    # Create outer faces
    for i in range(res_long):
        for j in range(res_arc):
            bm.faces.new((
                outer_verts[i][j], 
                outer_verts[i+1][j], 
                outer_verts[i+1][j+1], 
                outer_verts[i][j+1]
            ))

    # Inner surface: offset slightly to create shell thickness
    inner_verts = []
    for i in range(res_long + 1):
        u = i / res_long
        swell = (u ** 0.7)
        if u == 0: swell = 0.02
        
        # Inner is slightly smaller and shifted along Y to create a hollow shell
        w_inner = width_max * swell * 0.95
        h_inner = height_max * swell * 0.95
        z = u * length
        
        row = []
        for j in range(res_arc + 1):
            theta = (j / res_arc) * math.pi
            x = w_inner * math.cos(theta)
            y = h_inner * math.sin(theta) - thickness
            row.append(bm.verts.new(Vector((x, y, z))))
        inner_verts.append(row)

    # Create inner faces (reversed normals)
    for i in range(res_long):
        for j in range(res_arc):
            bm.faces.new((
                inner_verts[i][j+1], 
                inner_verts[i+1][j+1], 
                inner_verts[i+1][j], 
                inner_verts[i][j]
            ))

    # Bridge the edges: Hinge end, Open end, and side lips
    for j in range(res_arc):
        bm.faces.new((outer_verts[0][j], outer_verts[0][j+1], inner_verts[0][j+1], inner_verts[0][j]))
    for j in range(res_arc):
        bm.faces.new((outer_verts[res_long][j], inner_verts[res_long][j], inner_verts[res_long][j+1], outer_verts[res_long][j+1]))
    for i in range(res_long):
        bm.faces.new((outer_verts[i][0], outer_verts[i+1][0], inner_verts[i+1][0], inner_verts[i][0]))
        bm.faces.new((outer_verts[i][res_arc], inner_verts[i][res_arc], inner_verts[i+1][res_arc], outer_verts[i+1][res_arc]))

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def main():
    clear_scene()
    
    # Materials: Cream-Brown outer and Dark interior
    mat_outer = create_material("MusselOuter", (0.75, 0.6, 0.4, 1.0), roughness=0.8) # Warm cream-brown
    mat_inner = create_material("MusselInner", (0.02, 0.01, 0.03, 1.0), roughness=0.2) # Dark glossy interior

    valve_top = create_mussel_valve("ValveTop")
    valve_bottom = create_mussel_valve("ValveBottom")
    
    # Mirror bottom valve across XZ plane
    valve_bottom.scale = (1, -1, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    valves = [valve_top, valve_bottom]

    for v in valves:
        v.data.materials.append(mat_outer)
        v.data.materials.append(mat_inner)
        
        # Assign materials based on face normals relative to Y axis
        # Top valve outer faces point +Y, bottom valve outer faces point -Y
        for poly in v.data.polygons:
            if v == valve_top:
                poly.material_index = 0 if poly.normal.y > 0 else 1
            else:
                poly.material_index = 0 if poly.normal.y < 0 else 1

    # Set the hinge at origin (0,0,0), rotate to be partially open
    valve_top.rotation_euler = (0, math.radians(-25), 0)
    valve_bottom.rotation_euler = (0, math.radians(25), 0)
    
    # Ensure they are perfectly joined at the hinge point
    valve_top.location = (0, 0, 0)
    valve_bottom.location = (0, 0, 0)

    for v in valves:
        v.data.polygons.foreach_set("use_smooth", [True] * len(v.data.polygons))
        subsurf = v.modifiers.new(name="Subdiv", type='SUBSURF')
        subsurf.levels = 2

    # Container for final perspective view
    container = bpy.data.objects.new("MusselContainer", None)
    bpy.context.collection.objects.link(container)
    valve_top.parent = container
    valve_bottom.parent = container
    
    # 3/4 Perspective rotation
    container.rotation_euler = (math.radians(-70), 0, math.radians(45))

if __name__ == "__main__":
    main()
