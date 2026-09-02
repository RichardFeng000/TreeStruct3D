import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Clears the default scene of all objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple principled BSDF material with a specific base color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Base Color'].default_value = color
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_leaf_geometry(name, length, width, bend=0.5, twist=0.1, material=None):
    """
    Procedurally generates a leaf mesh using BMesh.
    The leaf is constructed as a grid of vertices tapered at both ends.
    """
    bm = bmesh.new()
    res_l = 16  # Longitudinal resolution
    res_w = 4   # Width resolution
    
    verts = []
    for i in range(res_l + 1):
        t = i / res_l # normalized length [0, 1]
        
        # Taper width: starts at 0, peaks in middle, ends at 0 (pointed)
        current_w = width * math.sin(t * math.pi)
        
        row = []
        for j in range(res_w + 1):
            u = (j / res_w) - 0.5 # normalized width [-0.5, 0.5]
            
            # Local coordinates before deformation
            x = t * length
            y = u * current_w
            z = 0
            
            # Apply organic bending along the spine
            # Bending occurs mainly in Z (upward/downward)
            bend_offset = math.sin(t * math.pi * 0.5) * bend * t
            z += bend_offset
            
            # Apply twist around the X axis
            angle = t * twist
            rot = Matrix.Rotation(angle, 4, 'X')
            local_pos = Vector((0, y, 0)) # distance from spine
            rotated_y = (rot @ local_pos).y
            rotated_z = (rot @ local_pos).z
            
            # Final position relative to the leaf origin (start of leaf)
            v = bm.verts.new(Vector((x, rotated_y, z + rotated_z)))
            row.append(v)
        verts.append(row)

    # Create faces
    for i in range(res_l):
        for j in range(res_w):
            bm.faces.new((verts[i][j], verts[i][j+1], verts[i+1][j+1], verts[i+1][j]))

    # Create mesh and object
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    if material:
        obj.data.materials.append(material)
        
    # Add subdivision surface for smoothness
    mod = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    mod.levels = 1
    mod.render_levels = 2
    
    return obj

def create_stalk(height, radius, material):
    """Creates a slightly tapered central stalk."""
    bm = bmesh.new()
    # Construct a cone manually to avoid operator parameter issues across versions
    segments = 16
    r_bottom = radius
    r_top = radius * 0.7
    
    # Bottom ring
    bottom_verts = []
    for i in range(segments):
        angle = (i / segments) * 2 * math.pi
        bottom_verts.append(bm.verts.new(Vector((math.cos(angle)*r_bottom, math.sin(angle)*r_bottom, 0))))
        
    # Top ring
    top_verts = []
    for i in range(segments):
        angle = (i / segments) * 2 * math.pi
        top_verts.append(bm.verts.new(Vector((math.cos(angle)*r_top, math.sin(angle)*r_top, height))))
        
    # Bridge the rings
    for i in range(segments):
        v1 = bottom_verts[i]
        v2 = bottom_verts[(i + 1) % segments]
        v3 = top_verts[(i + 1) % segments]
        v4 = top_verts[i]
        bm.faces.new((v1, v2, v3, v4))
        
    # Caps
    bm.faces.new(bottom_verts)
    bm.faces.new(reversed(top_verts)) # Reversed to ensure normal points up

    mesh = bpy.data.meshes.new("StalkMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Stalk", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    # Materials
    mat_green = create_material("Green", (0.1, 0.35, 0.1, 1.0))
    mat_yellow_green = create_material("YellowGreen", (0.4, 0.5, 0.2, 1.0))
    
    # Constants
    stalk_height = 6.0
    stalk_radius = 0.1
    num_bracts = 50
    
    # Central Stalk
    stalk = create_stalk(stalk_height, stalk_radius, mat_green)
    
    # Fibonacci-style spiral distribution for bracts
    golden_angle = 2.39996 # approx radians (137.5 deg)
    
    for i in range(num_bracts):
        z_pos = (i / num_bracts) * stalk_height * 0.85 + 0.4
        angle = i * golden_angle
        
        # Bract properties
        length = 0.5 + random.uniform(0, 0.3)
        width = 0.15 + random.uniform(0, 0.1)
        bend = 0.2 + random.uniform(0, 0.3)
        twist = random.uniform(-0.2, 0.2)
        mat = random.choice([mat_green, mat_yellow_green])
        
        bract = create_leaf_geometry(f"Bract_{i}", length, width, bend, twist, mat)
        
        # Positioning on stalk surface
        pos_x = math.cos(angle) * stalk_radius
        pos_y = math.sin(angle) * stalk_radius
        bract.location = (pos_x, pos_y, z_pos)
        
        # Rotation: Orient the leaf to point outward and upward
        # We rotate in Z first, then tilt it up.
        # Since our leaf geometry is built along X axis:
        rot_z = angle
        rot_y = -math.pi / 3 + random.uniform(-0.1, 0.1) # Angle relative to vertical stalk
        bract.rotation_euler = (0, rot_y, rot_z)

    # Lower spreading leaves
    num_base_leaves = 8
    for i in range(num_base_leaves):
        angle = (i / num_base_leaves) * 2 * math.pi
        length = 1.8 + random.uniform(0, 0.6)
        width = 0.3 + random.uniform(0, 0.15)
        bend = 1.2 + random.uniform(0, 0.8) # More bend to spread outward
        twist = random.uniform(-0.4, 0.4)
        
        leaf = create_leaf_geometry(f"BaseLeaf_{i}", length, width, bend, twist, mat_green)
        
        pos_x = math.cos(angle) * stalk_radius
        pos_y = math.sin(angle) * stalk_radius
        leaf.location = (pos_x, pos_y, 0.1)
        
        # Spread outward more horizontally than the bracts
        rot_y = -math.pi / 6 + random.uniform(-0.1, 0.1)
        leaf.rotation_euler = (0, rot_y, angle)

if __name__ == "__main__":
    main()
