import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Base Color'].default_value = color
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_bowl():
    """Creates a wide, shallow lavender bowl."""
    # Parameters - slightly deeper than previous version for better proportions
    radius = 2.0
    height = 1.0
    thickness = 0.15

    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(0, 0, 0))
    bowl = bpy.context.active_object
    bowl.name = "PlantContainer"
    bowl.scale[2] = height / radius

    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bm = bmesh.new()
    bm.from_mesh(bowl.data)
    verts_to_delete = [v for v in bm.verts if v.co.z > 0]
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')
    bm.to_mesh(bowl.data)
    bm.free()

    solidify = bowl.modifiers.new(name="Solidify", type='SOLIDIFY')
    solidify.thickness = thickness
    solidify.offset = 1 
    
    bevel = bowl.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.05
    bevel.segments = 3

    lavender_color = (0.8, 0.7, 0.9, 1.0) # Pastel Lavender
    mat = create_material("LavenderMat", lavender_color)
    bowl.data.materials.append(mat)

    return bowl

def create_soil():
    """Creates a disc of soil inside the container."""
    radius = 1.85
    depth = 0.4 # Deeper soil to fill the bowl better
    z_pos = -0.2
    
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=radius, depth=depth, location=(0, 0, z_pos))
    soil = bpy.context.active_object
    soil.name = "Soil"

    bm = bmesh.new()
    bm.from_mesh(soil.data)
    for v in bm.verts:
        if v.co.z > 0: # Jitter only the top surface
            v.co.z += random.uniform(-0.05, 0.05)
    bm.to_mesh(soil.data)
    bm.free()

    brown_color = (0.12, 0.08, 0.04, 1.0)
    mat = create_material("SoilMat", brown_color)
    soil.data.materials.append(mat)
    return soil

def create_leaf(name, position, rotation_euler, scale_val):
    """Creates a single elongated broad leaf."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    segments = 12
    length = 2.8 * scale_val
    width = 0.7 * scale_val
    
    vein_verts = []
    for i in range(segments + 1):
        t = i / segments
        x = t * length
        y = 0
        z = (math.sin(t * math.pi) * 0.3) # Leaf curves upwards/outwards
        vein_verts.append(bm.verts.new(Vector((x, y, z))))

    leaf_verts = []
    for i in range(segments + 1):
        t = i / segments
        w_factor = math.sin(t * math.pi)
        current_w = w_factor * width
        v_curr = vein_verts[i].co
        if i < segments:
            dir = (vein_verts[i+1].co - v_curr).normalized()
        else:
            dir = (v_curr - vein_verts[i-1].co).normalized()
        side_vec = Vector((0, 1, 0)).cross(dir).normalized()
        v1 = bm.verts.new(v_curr + side_vec * current_w)
        v2 = bm.verts.new(v_curr - side_vec * current_w)
        leaf_verts.append((v1, v2))

    for i in range(segments):
        bm.faces.new((leaf_verts[i][0], leaf_verts[i+1][0], leaf_verts[i+1][1], leaf_verts[i][1]))

    bm.to_mesh(mesh)
    bm.free()

    obj.location = position
    obj.rotation_euler = rotation_euler
    
    green_color = (0.15, 0.4, 0.1, 1.0)
    mat = create_material("LeafMat", green_color)
    obj.data.materials.append(mat)

def create_plant():
    """Creates a cluster of broad leaves originating from soil surface."""
    num_leaves = 12
    soil_surface_z = -0.2 + 0.2 # top of the cylinder created in create_soil
    
    for i in range(num_leaves):
        angle = (2 * math.pi / num_leaves) * i + random.uniform(-0.3, 0.3)
        # Force rotation to be generally upwards and outwards
        rot_x = random.uniform(0.4, 1.1) # Angle away from Z axis
        rot_y = angle
        rot_z = random.uniform(-0.2, 0.2)
        
        pos = Vector((0, 0, soil_surface_z))
        scale = random.uniform(0.8, 1.4)
        
        create_leaf(f"Leaf_{i}", pos, (rot_x, rot_y, rot_z), scale)

def main():
    clear_scene()
    create_bowl()
    create_soil()
    create_plant()
    bpy.context.view_layer.objects.active = None

if __name__ == "__main__":
    main()
