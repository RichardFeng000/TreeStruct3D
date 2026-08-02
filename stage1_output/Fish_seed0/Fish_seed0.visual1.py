import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, is_body=False):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Roughness'].default_value = 0.8
    
    if is_body:
        # Add subtle cloud-like variation using noise texture
        node_noise = nodes.new(type='ShaderNodeTexNoise')
        node_noise.inputs['Scale'].default_value = 4.0
        node_noise.inputs['Detail'].default_value = 2.0
        
        node_rgb_mix = nodes.new(type='ShaderNodeMixRGB')
        node_rgb_mix.blend_type = 'MIX'
        node_rgb_mix.inputs['Fac'].default_value = 0.3
        node_rgb_mix.inputs[1].default_value = color
        # Slightly lighter variant for the "clouds"
        node_rgb_mix.inputs[2].default_value = (color[0]*1.2, color[1]*1.2, color[2]*1.2, 1.0)
        
        links.new(node_noise.outputs['Fac'], node_rgb_mix.inputs['Fac'])
        links.new(node_rgb_mix.outputs['Color'], node_principled.inputs['Base Color'])
    else:
        node_principled.inputs['Base Color'].default_value = color
        links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
        
    if is_body:
        links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])

    return mat

def create_fan_fin(name, width, max_height, rays_count=15, color_mat=None):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    ray_width = width / (rays_count * 3)
    half_w = width / 2
    
    for i in range(rays_count):
        # X position for the ray
        x_offset = ((i - (rays_count - 1) / 2) / (rays_count - 1)) * width if rays_count > 1 else 0
        
        # Calculate height based on a parabolic arc for "fan shape"
        normalized_x = x_offset / half_w if half_w != 0 else 0
        h = max_height * (1.0 - 0.4 * (normalized_x**2))
        
        v1 = bm.verts.new(Vector((x_offset - ray_width/2, 0, 0)))
        v2 = bm.verts.new(Vector((x_offset + ray_width/2, 0, 0)))
        v3 = bm.verts.new(Vector((x_offset + ray_width/2, 0, h)))
        v4 = bm.verts.new(Vector((x_offset - ray_width/2, 0, h)))
        bm.faces.new((v1, v2, v3, v4))
        
    bm.to_mesh(mesh)
    bm.free()
    if color_mat:
        obj.data.materials.append(color_mat)
    return obj

def create_fish():
    periwinkle = create_material("Periwinkle", (0.6, 0.7, 0.9, 1.0), is_body=True)
    gold_brown = create_material("GoldBrown", (0.6, 0.4, 0.2, 1.0))
    black = create_material("Black", (0.05, 0.05, 0.05, 1.0))

    # Body Construction - Laterally compressed shape
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0), segments=32, ring_count=16)
    body = bpy.context.active_object
    body.name = "FishBody"
    # X: Very thin (compressed), Y: Long, Z: Height
    body.scale = (0.18, 2.5, 0.9)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    bm = bmesh.new()
    bm.from_mesh(body.data)
    
    for v in bm.verts:
        # Taper head and tail more aggressively
        if v.co.y > 0: # Head side
            taper = (1.0 - (v.co.y - 1.5)*0.4 if v.co.y > 1.5 else 1.0)
            v.co.x *= max(0.2, taper)
            v.co.z *= max(0.6, taper)
        elif v.co.y < 0: # Tail side
            taper = (1.0 + (v.co.y * 0.4)) # Y is negative
            v.co.x *= max(0.2, taper)
            v.co.z *= max(0.3, taper)

    # Create a small pointed mouth / snout indentation
    front_verts = [v for v in bm.verts if v.co.y > 2.4]
    for v in front_verts:
        v.co.x *= 0.2 # Pinch to a point
        if abs(v.co.x) < 0.05:
            v.co.y -= 0.05 # Slight indent for mouth opening

    bm.to_mesh(body.data)
    bm.free()
    
    for poly in body.data.polygons:
        poly.use_smooth = True
    body.data.materials.append(periwinkle)

    # Eyes
    def add_eye(side):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(side * 0.2, 1.8, 0.3))
        eye = bpy.context.active_object
        eye.data.materials.append(black)
        eye.parent = body

    add_eye(1)
    add_eye(-1)

    # Fins - using the fan geometry function
    # Dorsal: Top center back
    dorsal = create_fan_fin("DorsalFin", width=0.8, max_height=0.7, rays_count=16, color_mat=gold_brown)
    dorsal.location = (0, 0.2, 0.9)
    dorsal.parent = body

    # Caudal: Tail
    caudal = create_fan_fin("CaudalFin", width=1.0, max_height=1.4, rays_count=22, color_mat=gold_brown)
    caudal.location = (0, -2.5, 0)
    caudal.rotation_euler = (math.radians(90), 0, 0)
    caudal.parent = body

    # Pectorals: Sides
    for side in [1, -1]:
        pec = create_fan_fin(f"PectoralFin_{'L' if side > 0 else 'R'}", width=0.6, max_height=0.7, rays_count=12, color_mat=gold_brown)
        pec.location = (side * 0.25, 0.8, 0)
        pec.rotation_euler = (math.radians(90), 0, math.radians(90 if side > 0 else -90))
        pec.parent = body

    # Pelvics: Bottom front
    for side in [1, -1]:
        pel = create_fan_fin(f"PelvicFin_{'L' if side > 0 else 'R'}", width=0.4, max_height=0.5, rays_count=10, color_mat=gold_brown)
        pel.location = (side * 0.2, 0.6, -0.8)
        pel.rotation_euler = (math.radians(90), 0, math.radians(90 if side > 0 else -90))
        pel.parent = body

    # Anal: Bottom rear
    anal = create_fan_fin("AnalFin", width=0.5, max_height=0.6, rays_count=12, color_mat=gold_brown)
    anal.location = (0, -0.8, -0.9)
    anal.rotation_euler = (0, math.radians(180), 0)
    anal.parent = body

if __name__ == "__main__":
    clear_scene()
    create_fish()
