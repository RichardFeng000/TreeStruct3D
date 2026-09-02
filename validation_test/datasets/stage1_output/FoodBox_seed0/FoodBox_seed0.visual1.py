import bpy
import bmesh
import math
import random
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
    # Reduce specular for a printed matte look
    if 'Roughness' in node_principled.inputs:
        node_principled.inputs['Roughness'].default_value = 0.8
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_box():
    # Dimensions for a rectangular food packaging box
    width, depth, height = 0.8, 1.2, 1.6
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    box = bpy.context.active_object
    box.name = "FoodPackagingBox"
    box.scale = (width, depth, height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return box

def add_pattern_element(parent_obj, type, position, normal, size, material):
    # Offset slightly to avoid z-fighting (0.001 instead of 0.01)
    offset_pos = position + (normal * 0.002)
    
    if type == "circle":
        bpy.ops.mesh.primitive_cylinder_add(radius=size, depth=0.005, location=offset_pos)
        elem = bpy.context.active_object
        target_quat = Vector((0, 0, 1)).rotation_difference(normal)
        elem.rotation_mode = 'QUATERNION'
        elem.rotation_quaternion = target_quat
        
    elif type == "dot":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=size, location=offset_pos)
        elem = bpy.context.active_object
        # Flatten sphere to look like a printed dot
        if normal.x != 0: elem.scale = (0.1, 1, 1)
        elif normal.y != 0: elem.scale = (1, 0.1, 1)
        else: elem.scale = (1, 1, 0.1)
        
    elif type == "block":
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=offset_pos)
        elem = bpy.context.active_object
        s_x, s_y, s_z = size
        # Scale the block to be very thin relative to its normal
        if normal.x != 0: elem.scale = (0.005, s_y, s_z)
        elif normal.y != 0: elem.scale = (s_x, 0.005, s_z)
        else: elem.scale = (s_x, s_y, 0.005)
        
        target_quat = Vector((0, 0, 1)).rotation_difference(normal)
        elem.rotation_mode = 'QUATERNION'
        elem.rotation_quaternion = target_quat
    
    if 'elem' in locals():
        elem.data.materials.append(material)
        elem.parent = parent_obj

def create_scribble(box, material):
    # Box dimensions: width=0.8 (x), depth=1.2 (y), height=1.6 (z)
    # Top face is at Z = 0.8
    z_pos = 0.8 + 0.003
    points = []
    curr_x, curr_y = random.uniform(-0.2, 0.2), random.uniform(-0.4, 0.4)
    
    for _ in range(30):
        points.append(Vector((curr_x, curr_y, z_pos)))
        curr_x += random.uniform(-0.1, 0.1)
        curr_y += random.uniform(-0.1, 0.1)
        # Clamp to top face: x in [-0.4, 0.4], y in [-0.6, 0.6]
        curr_x = max(-0.35, min(0.35, curr_x))
        curr_y = max(-0.55, min(0.55, curr_y))

    curve_data = bpy.data.curves.new('ScribbleCurve', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = 0.008 # Make it thicker for visibility
    curve_data.bevel_resolution = 3
    
    polyline = curve_data.splines.new('POLY')
    polyline.points.add(len(points) - 1)
    for i, p in enumerate(points):
        polyline.points[i].co = (p.x, p.y, p.z, 1.0)
    
    obj = bpy.data.objects.new('ScribbleText', curve_data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.parent = box

def main():
    clear_scene()
    
    # Vibrant color palette
    mat_magenta = create_material("MagentaBG", (1.0, 0.0, 0.5, 1.0)) # More vibrant
    mat_lavender = create_material("Lavender", (0.8, 0.6, 1.0, 1.0))
    mat_pink = create_material("Pink", (1.0, 0.4, 0.7, 1.0))
    mat_green = create_material("Green", (0.2, 0.9, 0.3, 1.0)) # Brighter green
    mat_blue = create_material("Blue", (0.0, 0.3, 0.9, 1.0))
    mat_black = create_material("BlackText", (0.0, 0.0, 0.0, 1.0))
    
    box = create_box()
    box.data.materials.append(mat_magenta)
    
    # Faces for a box of size (0.8, 1.2, 1.6)
    faces = [
        (Vector((0, 0, 1)), Vector((0, 0, 0.8))),   # Top
        (Vector((0, 0, -1)), Vector((0, 0, -0.8))),  # Bottom
        (Vector((1, 0, 0)), Vector((0.4, 0, 0))),    # Right
        (Vector((-1, 0, 0)), Vector((-0.4, 0, 0))),  # Left
        (Vector((0, 1, 0)), Vector((0, 0.6, 0))),    # Front
        (Vector((0, -1, 0)), Vector((0, -0.6, 0))),  # Back
    ]
    
    for i in range(5): # Top and sides
        normal = faces[i][0]
        center = faces[i][1]
        
        # Circles/Blobs
        for _ in range(random.randint(3, 5)):
            offset = Vector((0,0,0))
            if normal.x != 0: offset = Vector((0, random.uniform(-0.4, 0.4), random.uniform(-0.6, 0.6)))
            elif normal.y != 0: offset = Vector((random.uniform(-0.3, 0.3), 0, random.uniform(-0.6, 0.6)))
            else: offset = Vector((random.uniform(-0.3, 0.3), random.uniform(-0.4, 0.4), 0))
            pos = center + offset
            mat = random.choice([mat_lavender, mat_pink])
            add_pattern_element(box, "circle", pos, normal, random.uniform(0.15, 0.3), mat)

        # Green dots (clusters)
        for _ in range(4):
            cluster_center = center + Vector((random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3)))
            if normal.x != 0: cluster_center.x = center.x
            elif normal.y != 0: cluster_center.y = center.y
            else: cluster_center.z = center.z
            
            for _ in range(6):
                dot_offset = Vector((random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)))
                if normal.x != 0: dot_offset.x = 0
                elif normal.y != 0: dot_offset.y = 0
                else: dot_offset.z = 0
                add_pattern_element(box, "dot", cluster_center + dot_offset, normal, 0.04, mat_green)

        # Blue blocks
        for _ in range(random.randint(1, 3)):
            offset = Vector((random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3)))
            if normal.x != 0: offset.x = 0
            elif normal.y != 0: offset.y = 0
            else: offset.z = 0
            pos = center + offset
            add_pattern_element(box, "block", pos, normal, (0.25, 0.15, 0.3), mat_blue)

    create_scribble(box, mat_black)

if __name__ == "__main__":
    main()
