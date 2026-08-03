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
        # Periwinkle blue-gray with cloud variation
        node_noise = nodes.new(type='ShaderNodeTexNoise')
        node_noise.inputs['Scale'].default_value = 3.0
        node_noise.inputs['Detail'].default_value = 4.0
        
        node_rgb_mix = nodes.new(type='ShaderNodeMixRGB')
        node_rgb_mix.blend_type = 'MIX'
        node_rgb_mix.inputs['Fac'].default_value = 0.4
        node_rgb_mix.inputs[1].default_value = color
        # Slightly lighter variation
        node_rgb_mix.inputs[2].default_value = (color[0]*1.15, color[1]*1.15, color[2]*1.15, 1.0)
        
        links.new(node_noise.outputs['Fac'], node_rgb_mix.inputs['Fac'])
        links.new(node_rgb_mix.outputs['Color'], node_principled.inputs['Base Color'])
        links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    else:
        node_principled.inputs['Base Color'].default_value = color
        links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])

    return mat

def create_ribbed_fin(name, width, max_height, rays_count=12, color_mat=None):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Create a base thin membrane and then add ribs on top
    half_w = width / 2
    
    # Membrane
    for i in range(rays_count + 1):
        x = ((i / rays_count) - 0.5) * width
        normalized_x = (x / half_w) if half_w != 0 else 0
        h = max_height * (1.0 - 0.3 * (normalized_x**2))
        
        # We build the fin as a series of thin strips to create "ribs" effect
        if i < rays_count:
            x_next = (((i+1) / rays_count) - 0.5) * width
            norm_x_next = (x_next / half_w) if half_w != 0 else 0
            h_next = max_height * (1.0 - 0.3 * (norm_x_next**2))
            
            v1 = bm.verts.new(Vector((x, 0, 0)))
            v2 = bm.verts.new(Vector((x_next, 0, 0)))
            v3 = bm.verts.new(Vector((x_next, 0, h_next)))
            v4 = bm.verts.new(Vector((x, 0, h)))
            bm.faces.new((v1, v2, v3, v4))
            
    # To make them "ribbed", we slightly extrude the ribs or add thickness
    # For a simple script, creating thin strips is enough if colored well, 
    # but let's give it some actual geometry by adding small offset rails.
    for i in range(rays_count):
        x = ((i / rays_count) - 0.5) * width
        normalized_x = (x / half_w) if half_w != 0 else 0
        h = max_height * (1.0 - 0.3 * (normalized_x**2))
        
        v1 = bm.verts.new(Vector((x, 0, 0)))
        v2 = bm.verts.new(Vector((x, 0.02, 0))) # Small thickness
        v3 = bm.verts.new(Vector((x, 0.02, h)))
        v4 = bm.verts.new(Vector((x, 0, h)))
        bm.faces.new((v1, v2, v3, v4))

    bm.to_mesh(mesh)
    bm.free()
    if color_mat:
        obj.data.materials.append(color_mat)
    return obj

def create_fish():
    periwinkle = create_material("Periwinkle", (0.6, 0.7, 0.9, 1.0), is_body=True)
    gold_brown = create_material("GoldBrown", (0.5, 0.3, 0.1, 1.0))
    black = create_material("Black", (0.02, 0.02, 0.02, 1.0))

    # Body Construction - Laterally compressed oval
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0), segments=32, ring_count=16)
    body = bpy.context.active_object
    body.name = "FishBody"
    # X: thin (compressed), Y: length, Z: height
    body.scale = (0.15, 2.4, 0.85)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    bm = bmesh.new()
    bm.from_mesh(body.data)
    
    for v in bm.verts:
        # Head taper (positive Y)
        if v.co.y > 0:
            taper = (1.0 - (v.co.y - 1.5)*0.4 if v.co.y > 1.5 else 1.0)
            v.co.x *= max(0.3, taper)
            v.co.z *= max(0.6, taper)
        # Tail taper (negative Y)
        elif v.co.y < 0:
            taper = (1.0 + (v.co.y * 0.5)) 
            v.co.x *= max(0.2, taper)
            v.co.z *= max(0.3, taper)

    # Mouth opening and pointed snout
    front_verts = [v for v in bm.verts if v.co.y > 2.1]
    for v in front_verts:
        if abs(v.co.x) < 0.05:
            v.co.y += 0.1 # Push tip out a bit to make it "pointed"
            # Indent the very center for mouth opening
            if abs(v.co.z) < 0.1:
                v.co.y -= 0.15

    bm.to_mesh(body.data)
    bm.free()
    
    for poly in body.data.polygons:
        poly.use_smooth = True
    body.data.materials.append(periwinkle)

    # Eyes
    def add_eye(side):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(side * 0.22, 1.7, 0.3))
        eye = bpy.context.active_object
        eye.data.materials.append(black)
        eye.parent = body

    add_eye(1)
    add_eye(-1)

    # Fins - Ribbed fan geometry
    # Dorsal
    dorsal = create_ribbed_fin("DorsalFin", width=0.9, max_height=0.7, rays_count=15, color_mat=gold_brown)
    dorsal.location = (0, 0.3, 0.85)
    dorsal.parent = body

    # Caudal
    caudal = create_ribbed_fin("CaudalFin", width=1.2, max_height=1.4, rays_count=20, color_mat=gold_brown)
    caudal.location = (0, -2.4, 0)
    caudal.rotation_euler = (math.radians(90), 0, 0)
    caudal.parent = body

    # Pectorals
    for side in [1, -1]:
        pec = create_ribbed_fin(f"PectoralFin_{'L' if side > 0 else 'R'}", width=0.7, max_height=0.8, rays_count=12, color_mat=gold_brown)
        pec.location = (side * 0.2, 0.7, 0)
        pec.rotation_euler = (math.radians(90), 0, math.radians(90 if side > 0 else -90))
        pec.parent = body

    # Pelvics
    for side in [1, -1]:
        pel = create_ribbed_fin(f"PelvicFin_{'L' if side > 0 else 'R'}", width=0.5, max_height=0.6, rays_count=10, color_mat=gold_brown)
        pel.location = (side * 0.2, 0.5, -0.8)
        pel.rotation_euler = (math.radians(90), 0, math.radians(90 if side > 0 else -90))
        pel.parent = body

    # Anal
    anal = create_ribbed_fin("AnalFin", width=0.6, max_height=0.5, rays_count=12, color_mat=gold_brown)
    anal.location = (0, -1.0, -0.85)
    anal.rotation_euler = (0, math.radians(180), 0)
    anal.parent = body

if __name__ == "__main__":
    clear_scene()
    create_fish()
