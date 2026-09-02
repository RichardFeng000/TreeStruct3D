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
    """Create a material with sandy beige/tan tones."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.85
    return mat

def generate_cauliflower_coral():
    # 1. Setup Parameters for a "low and wide" silhouette
    BASE_RADIUS = 2.5
    Z_SCALE = 0.4
    LOBE_COUNT = 60
    CLUSTER_COUNT = 180
    POLYP_COUNT = 800 # For the granular texture
    VOXEL_SIZE = 0.05
    
    # Warm sandy beige / tan with faint green-gray undertones
    coral_color = (0.75, 0.68, 0.52, 1.0) 
    material = create_material("CoralMaterial", coral_color)

    objs = []
    
    # Create a base flat cylinder/disc to ensure the "low and wide" look
    bpy.ops.mesh.primitive_cylinder_add(radius=BASE_RADIUS, depth=0.5, location=(0, 0, 0))
    base_obj = bpy.context.active_object
    objs.append(base_obj)

    # Helper to get a point on the flattened hemisphere surface
    def get_surface_point(radius, z_scale):
        phi = random.uniform(0, 2 * math.pi)
        costheta = random.uniform(0, 1) # Only upper half
        theta = math.acos(costheta)
        x = radius * math.sin(theta) * math.cos(phi)
        y = radius * math.sin(theta) * math.sin(phi)
        z = radius * math.cos(theta) * z_scale
        return Vector((x, y, z))

    # 2. Large Lobes - Ensuring overlap to prevent floating pieces
    for _ in range(LOBE_COUNT):
        pos = get_surface_point(BASE_RADIUS * 0.8, Z_SCALE)
        radius = random.uniform(0.5, 1.0)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=pos)
        objs.append(bpy.context.active_object)

    # 3. Medium Clusters - Layered on top of lobes
    for _ in range(CLUSTER_COUNT):
        parent = random.choice(objs)
        p_loc = parent.location
        
        # Random offset restricted to ensure connectivity
        offset = Vector((random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.6), random.uniform(-0.3, 0.6)))
        pos = p_loc + offset
        
        # Keep them within the overall low-profile boundary
        if pos.z > Z_SCALE * 2.5: 
            pos.z = Z_SCALE * 2.5
            
        radius = random.uniform(0.2, 0.4)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=pos)
        objs.append(bpy.context.active_object)

    # 4. Granular Surface Bumps (Polyp clusters) - Added before remesh for tactile quality
    for _ in range(POLYP_COUNT):
        parent = random.choice(objs)
        p_loc = parent.location
        # Very small offsets to create surface "grain"
        offset = Vector((random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3)))
        pos = p_loc + offset
        radius = random.uniform(0.05, 0.12)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=pos)
        objs.append(bpy.context.active_object)

    # Join all objects into one mesh
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    
    coral_obj = bpy.context.active_object
    coral_obj.name = "CauliflowerCoral"

    # 5. Remesh to fuse everything into a single organic skin
    remesh = coral_obj.modifiers.new(name="Remesh", type='REMESH')
    remesh.mode = 'VOXEL'
    remesh.voxel_size = VOXEL_SIZE
    bpy.ops.object.modifier_apply(modifier="Remesh")

    # 6. Final geometric refinement for "rough" quality
    # We apply a slight displacement using BMesh to avoid the "melted plastic" look
    bm = bmesh.new()
    bm.from_mesh(coral_obj.data)
    for v in bm.verts:
        # Add high-frequency noise based on vertex position
        noise = (random.random() - 0.5) * 0.02
        v.co += v.normal * noise
    bm.to_mesh(coral_obj.data)
    bm.free()

    # Material and Shading
    coral_obj.data.materials.append(material)
    for poly in coral_obj.data.polygons:
        poly.use_smooth = True

    # Ensure center of mass is at origin
    coral_obj.location = (0, 0, 0)

if __name__ == "__main__":
    clear_scene()
    generate_cauliflower_coral()
