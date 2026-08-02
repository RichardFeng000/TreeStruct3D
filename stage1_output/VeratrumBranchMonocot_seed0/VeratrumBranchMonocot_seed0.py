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
    # Slightly increase roughness for a more organic look
    if 'Roughness' in node_principled.inputs:
        node_principled.inputs['Roughness'].default_value = 0.8
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_leaf_geometry(name, length, width, bend=0.5, twist=0.1, material=None):
    """Procedurally generates a leaf mesh using BMesh."""
    bm = bmesh.new()
    res_l = 12  # Longitudinal resolution
    res_w = 4   # Width resolution
    
    verts = []
    for i in range(res_l + 1):
        t = i / res_l 
        # Taper width: pointed at both ends, widest slightly off-center for organic feel
        current_w = width * math.sin(t * math.pi)
        
        row = []
        for j in range(res_w + 1):
            u = (j / res_w) - 0.5
            
            x = t * length
            y = u * current_w
            z = 0
            
            # Organic bending along the spine
            bend_offset = math.sin(t * math.pi * 0.7) * bend * (t**1.5)
            z += bend_offset
            
            # Twist around X axis
            angle = t * twist
            rot = Matrix.Rotation(angle, 4, 'X')
            local_pos = Vector((0, y, 0))
            rotated_y = (rot @ local_pos).y
            rotated_z = (rot @ local_pos).z
            
            v = bm.verts.new(Vector((x, rotated_y, z + rotated_z)))
            row.append(v)
        verts.append(row)

    for i in range(res_l):
        for j in range(res_w):
            bm.faces.new((verts[i][j], verts[i][j+1], verts[i+1][j+1], verts[i+1][j]))

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if material:
        obj.data.materials.append(material)
    return obj

def create_stalk(height, radius, material):
    """Creates a slightly tapered central stalk."""
    bm = bmesh.new()
    segments = 12
    r_bottom = radius
    r_top = radius * 0.6
    
    bottom_verts = [bm.verts.new(Vector((math.cos(i/segments*2*math.pi)*r_bottom, math.sin(i/segments*2*math.pi)*r_bottom, 0))) for i in range(segments)]
    top_verts = [bm.verts.new(Vector((math.cos(i/segments*2*math.pi)*r_top, math.sin(i/segments*2*math.pi)*r_top, height))) for i in range(segments)]
    
    for i in range(segments):
        bm.faces.new((bottom_verts[i], bottom_verts[(i+1)%segments], top_verts[(i+1)%segments], top_verts[i]))
    
    bm.faces.new(bottom_verts)
    bm.faces.new(reversed(top_verts))

    mesh = bpy.data.meshes.new("StalkMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Stalk", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj

def main():
    clear_scene()
    
    mat_green = create_material("Green", (0.05, 0.25, 0.05, 1.0))
    mat_yellow_green = create_material("YellowGreen", (0.35, 0.45, 0.15, 1.0))
    
    stalk_height = 6.5
    stalk_radius = 0.12
    num_bracts = 140 # Increased significantly for density and overlap
    
    stalk = create_stalk(stalk_height, stalk_radius, mat_green)
    golden_angle = 2.39996 
    
    for i in range(num_bracts):
        # Pack Z positions tighter to ensure overlapping
        z_pos = (i / num_bracts) * (stalk_height * 0.85) + 0.5
        angle = i * golden_angle
        
        length = 0.4 + random.uniform(0, 0.2)
        width = 0.12 + random.uniform(0, 0.08)
        bend = 0.1 + random.uniform(0, 0.2)
        twist = random.uniform(-0.1, 0.1)
        mat = mat_green if i % 3 != 0 else mat_yellow_green
        
        bract = create_leaf_geometry(f"Bract_{i}", length, width, bend, twist, mat)
        
        # Offset slightly from center to avoid z-fighting with stalk
        pos_x = math.cos(angle) * (stalk_radius * 0.9)
        pos_y = math.sin(angle) * (stalk_radius * 0.9)
        bract.location = (pos_x, pos_y, z_pos)
        
        # Rotate to be more upright for overlap: -pi/4 instead of -pi/3
        rot_z = angle
        rot_y = -math.pi / 4 + random.uniform(-0.05, 0.05)
        bract.rotation_euler = (0, rot_y, rot_z)

    # Base leaves: wider and more spreading
    num_base_leaves = 12
    for i in range(num_base_leaves):
        angle = (i / num_base_leaves) * 2 * math.pi
        length = 2.0 + random.uniform(0, 0.8)
        width = 0.35 + random.uniform(0, 0.1)
        bend = 1.5 + random.uniform(0, 1.0)
        twist = random.uniform(-0.3, 0.3)
        
        leaf = create_leaf_geometry(f"BaseLeaf_{i}", length, width, bend, twist, mat_green)
        leaf.location = (math.cos(angle)*stalk_radius*0.5, math.sin(angle)*stalk_radius*0.5, 0.1)
        # More horizontal angle for base leaves
        rot_y = -math.pi / 8 + random.uniform(-0.1, 0.1)
        leaf.rotation_euler = (0, rot_y, angle)

if __name__ == "__main__":
    main()
