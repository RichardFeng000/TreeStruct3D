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

def create_mussel_valve(name, is_top=True):
    """
    Procedurally generates one valve of a mussel shell.
    The shape is an elongated teardrop with concentric growth rings.
    """
    bm = bmesh.new()
    
    # Parameters
    res_long = 64  # Resolution along the length
    res_arc = 32   # Resolution around the arc
    length = 4.0
    width_max = 1.8
    height_max = 1.4
    thickness = 0.15
    
    # Ring parameters
    ring_freq = 12.0
    ring_amp = 0.06

    # We will create two layers: outer and inner
    # Outer surface (with rings)
    outer_verts = []
    for i in range(res_long + 1):
        u = i / res_long # distance from hinge [0, 1]
        
        # Basic teardrop profile swell: starts small at hinge, expands, then rounds off
        swell = math.sin(u * math.pi * 0.8) if u < 0.8 else math.sin(0.8 * math.pi * 0.8)
        if u == 0: swell = 0.05 # Small start at hinge
        
        # Add growth rings (concentric ripples along the length)
        ring_mod = 1.0 + ring_amp * math.sin(u * ring_freq * 2 * math.pi)
        
        w = width_max * swell * ring_mod
        h = height_max * swell * ring_mod
        z = u * length
        
        row = []
        for j in range(res_arc + 1):
            theta = (j / res_arc) * math.pi # Semi-circle arc
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

    # Inner surface (slightly offset inwards)
    inner_verts = []
    for i in range(res_long + 1):
        u = i / res_long
        swell = math.sin(u * math.pi * 0.8) if u < 0.8 else math.sin(0.8 * math.pi * 0.8)
        if u == 0: swell = 0.05
        
        # Inner shell is smoother and slightly smaller
        w_inner = width_max * swell * 0.92
        h_inner = height_max * swell * 0.92
        z = u * length
        
        row = []
        for j in range(res_arc + 1):
            theta = (j / res_arc) * math.pi
            # Shift inner surface inwards along Y axis to create shell thickness
            x = w_inner * math.cos(theta)
            y = h_inner * math.sin(theta) - thickness
            row.append(bm.verts.new(Vector((x, y, z))))
        inner_verts.append(row)

    # Create inner faces (inverted order for correct normals)
    for i in range(res_long):
        for j in range(res_arc):
            bm.faces.new((
                inner_verts[i][j+1], 
                inner_verts[i+1][j+1], 
                inner_verts[i+1][j], 
                inner_verts[i][j]
            ))

    # Bridge the edges (the "lip" and ends)
    # Hinge end
    for j in range(res_arc):
        bm.faces.new((outer_verts[0][j], outer_verts[0][j+1], inner_verts[0][j+1], inner_verts[0][j]))
    # Open end
    for j in range(res_arc):
        bm.faces.new((outer_verts[res_long][j], inner_verts[res_long][j], inner_verts[res_long][j+1], outer_verts[res_long][j+1]))
    # Side edges (the arc boundaries)
    for i in range(res_long):
        bm.faces.new((outer_verts[i][0], outer_verts[i+1][0], inner_verts[i+1][0], inner_verts[i][0]))
        bm.faces.new((outer_verts[i][res_arc], inner_verts[i][res_arc], inner_verts[i+1][res_arc], outer_verts[i+1][res_arc]))

    # Correct way to create a mesh from BMesh in Blender
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def main():
    clear_scene()
    
    # Materials: Outer (brown-cream tones), Inner (dark purple/black)
    mat_outer = create_material("MusselOuter", (0.2, 0.15, 0.1, 1.0), roughness=0.7)
    mat_inner = create_material("MusselInner", (0.03, 0.01, 0.04, 1.0), roughness=0.2)

    # Create two valves
    valve_top = create_mussel_valve("ValveTop")
    valve_bottom = create_mussel_valve("ValveBottom")
    
    # Mirror the bottom valve across XZ plane (Y is depth in this construction)
    valve_bottom.scale = (1, -1, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    valves = [valve_top, valve_bottom]

    for v in valves:
        v.data.materials.append(mat_outer)
        v.data.materials.append(mat_inner)
        
        # Assign materials by checking face normals relative to the center of the shell
        for poly in v.data.polygons:
            # For our construction, outer faces usually point "up" or "down" (away from interior)
            # The inner surface was built with vertices shifted along -Y (before mirroring)
            # A reliable way is to check if the normal points generally away from the hinge axis center.
            center = Vector((0, 0, 0))
            for vert_idx in poly.vertices:
                center += v.data.vertices[vert_idx].co
            center /= len(poly.vertices)
            
            # Normals pointing away from the 'core' of the shell are outer.
            # Since we mirrored valve_bottom, let's check normal direction relative to object scale/position.
            if v == valve_top:
                if poly.normal.y > 0:
                    poly.material_index = 0 # Outer
                else:
                    poly.material_index = 1 # Inner
            else:
                # For the mirrored bottom, outer is pointing in -Y direction
                if poly.normal.y < 0:
                    poly.material_index = 0 # Outer
                else:
                    poly.material_index = 1 # Inner

    # Hinge and Openness Logic
    # The hinge is at (0,0,0), object extends along Z axis
    valve_top.rotation_euler = (0, math.radians(-20), 0)
    valve_bottom.rotation_euler = (0, math.radians(20), 0)
    
    # Slight separation at the hinge for visual clarity
    valve_top.location = (0, 0.05, 0)
    valve_bottom.location = (0, -0.05, 0)

    # Smooth shading and Subdivision Surface modifier for organic look
    for v in valves:
        v.data.polygons.foreach_set("use_smooth", [True] * len(v.data.polygons))
        subsurf = v.modifiers.new(name="Subdiv", type='SUBSURF')
        subsurf.levels = 1
        subsurf.render_levels = 2

    # Parent both to an empty for final transformation into a three-quarter perspective view
    container = bpy.data.objects.new("MusselContainer", None)
    bpy.context.collection.objects.link(container)
    valve_top.parent = container
    valve_bottom.parent = container
    
    # Rotate the whole assembly to get a 3/4 view
    container.rotation_euler = (math.radians(-60), 0, math.radians(45))

if __name__ == "__main__":
    main()
