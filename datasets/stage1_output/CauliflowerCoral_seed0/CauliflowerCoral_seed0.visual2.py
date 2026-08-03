import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Clear default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Create a material with sandy beige/tan tones and rough finish."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Warm sandy beige/tan with faint green-gray undertones
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.9
        bsdf.inputs['Specular IOR Level'].default_value = 0.2
    return mat

def get_random_point_on_sphere(radius, center=Vector((0, 0, 0)), z_scale=1.0):
    """Returns a point on the surface of an ellipsoid."""
    phi = random.uniform(0, 2 * math.pi)
    costheta = random.uniform(-1, 1)
    theta = math.acos(costheta)
    
    x = radius * math.sin(theta) * math.cos(phi)
    y = radius * math.sin(theta) * math.sin(phi)
    z = radius * math.cos(theta) * z_scale
    return center + Vector((x, y, z))

def generate_cauliflower_coral():
    # 1. Setup Parameters
    BASE_RADIUS = 2.0
    Z_SCALE = 0.5  # Low and wide
    LOBE_COUNT = 80
    BUMP_COUNT = 600
    GRAIN_COUNT = 1200
    VOXEL_SIZE = 0.04 # Finer for more detail
    
    # Warm sandy beige / tan color
    coral_color = (0.82, 0.75, 0.60, 1.0) 
    material = create_material("CoralMaterial", coral_color)

    objs = []
    
    # Core: A flattened sphere to start from
    bpy.ops.mesh.primitive_uv_sphere_add(radius=BASE_RADIUS * 0.7, location=(0, 0, 0))
    core = bpy.context.active_object
    core.scale[2] = Z_SCALE
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    objs.append(core)

    # Level 1: Large Lobes (connected to core)
    for _ in range(LOBE_COUNT):
        pos = get_random_point_on_sphere(BASE_RADIUS * 0.6, z_scale=Z_SCALE)
        radius = random.uniform(0.4, 0.8)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=pos)
        objs.append(bpy.context.active_object)

    # Level 2: Medium Bumps (connected to lobes or core)
    for _ in range(BUMP_COUNT):
        parent = random.choice(objs)
        # Sample surface of parent instead of just offset from center
        p_radius = 0.6 if parent == core else random.uniform(0.3, 0.7)
        pos = get_random_point_on_sphere(p_radius, center=parent.location, z_scale=1.0)
        
        radius = random.uniform(0.15, 0.35)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=pos)
        objs.append(bpy.context.active_object)

    # Level 3: Tiny Grains (for the "granular" tactile quality)
    for _ in range(GRAIN_COUNT):
        parent = random.choice(objs)
        p_radius = 0.5 if parent == core else random.uniform(0.1, 0.4)
        pos = get_random_point_on_sphere(p_radius, center=parent.location, z_scale=1.0)
        
        radius = random.uniform(0.03, 0.1)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=pos)
        objs.append(bpy.context.active_object)

    # Join all objects into one mesh to prepare for remesh
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    
    coral_obj = bpy.context.active_object
    coral_obj.name = "CauliflowerCoral"

    # Remesh to fuse everything into a single organic skin (eliminates floating pieces)
    remesh = coral_obj.modifiers.new(name="Remesh", type='REMESH')
    remesh.mode = 'VOXEL'
    remesh.voxel_size = VOXEL_SIZE
    bpy.ops.object.modifier_apply(modifier="Remesh")

    # High-frequency vertex jitter to break the "smooth plastic" look and add grit
    bm = bmesh.new()
    bm.from_mesh(coral_obj.data)
    for v in bm.verts:
        # Stronger noise for tactile roughness
        noise_vec = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
        v.co += noise_vec * 0.015
    bm.to_mesh(coral_obj.data)
    bm.free()

    # Material and Shading
    coral_obj.data.materials.append(material)
    for poly in coral_obj.data.polygons:
        poly.use_smooth = True

    # Center the object
    coral_obj.location = (0, 0, 0)

if __name__ == "__main__":
    clear_scene()
    generate_cauliflower_coral()
