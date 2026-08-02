import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5, is_cloud=False):
    """Creates a Principled BSDF material with optional cloud texture."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    for n in nodes:
        nodes.remove(n)
        
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    
    if is_cloud:
        # Create a "cloud" texture for the screen using Noise and ColorRamp
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 5.0
        noise.inputs['Detail'].default_value = 15.0
        
        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color = (0.2, 0.2, 0.2, 1.0) # Dark gray
        ramp.color_ramp.elements[1].color = (0.6, 0.6, 0.6, 1.0) # Light gray
        
        links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
        links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
        
    return mat

def create_monitor():
    # --- Parameters ---
    screen_w, screen_h, screen_d = 24.0, 14.0, 0.8
    bezel_thickness = 0.5
    base_w, base_d, base_h = 8.0, 6.0, 0.4
    arm_r, arm_h = 0.4, 4.0

    # Materials
    # Bezel: Light tan-and-silver metallic
    mat_bezel = create_material("BezelMat", (0.85, 0.82, 0.7, 1.0), metallic=0.9, roughness=0.2)
    # Screen: Gray cloud-textured
    mat_screen = create_material("ScreenMat", (0.4, 0.4, 0.4, 1.0), metallic=0.0, roughness=0.6, is_cloud=True)
    # Base: Dark base stand
    mat_base = create_material("BaseMat", (0.05, 0.05, 0.05, 1.0), metallic=0.3, roughness=0.4)

    # --- 1. Monitor Chassis ---
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    monitor_obj = bpy.context.active_object
    monitor_obj.name = "Monitor"
    monitor_obj.scale = (screen_w / 2, screen_d / 2, screen_h / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bm = bmesh.new()
    bm.from_mesh(monitor_obj.data)
    
    # Identify front face (Y positive)
    front_face = None
    for f in bm.faces:
        if f.normal.y > 0.9:
            front_face = f
            break
    
    if front_face:
        # Inset to create bezel
        res = bmesh.ops.inset_region(bm, faces=[front_face], thickness=bezel_thickness, use_boundary=True)
        screen_face = res['faces'][0]
        # Recess the screen slightly
        bmesh.ops.translate(bm, verts=screen_face.verts, vec=(0, -0.1, 0))
        
        for f in bm.faces:
            f.material_index = 0 # Bezel
        screen_face.material_index = 1 # Screen
    
    bm.to_mesh(monitor_obj.data)
    bm.free()

    monitor_obj.data.materials.append(mat_bezel)
    monitor_obj.data.materials.append(mat_screen)

    # Bevel outer edges for better light catch
    bevel = monitor_obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.1
    bevel.segments = 3

    # --- 2. Pedestal Arm ---
    arm_y_pos = -screen_d/4
    arm_z_start = -screen_h/2 + arm_h/2 # Offset based on monitor half-height
    bpy.ops.mesh.primitive_cylinder_add(radius=arm_r, depth=arm_h, location=(0, arm_y_pos, arm_z_start))
    arm_obj = bpy.context.active_object
    arm_obj.name = "Arm"
    arm_obj.data.materials.append(mat_base)

    # --- 3. Base Stand ---
    base_z_pos = -screen_h/2 # Sits at the bottom of the screen height reference
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, arm_y_pos, base_z_pos))
    base_obj = bpy.context.active_object
    base_obj.name = "Base"
    base_obj.scale = (base_w / 2, base_d / 2, base_h / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    base_obj.data.materials.append(mat_base)

    base_bev = base_obj.modifiers.new(name="Bevel", type='BEVEL')
    base_bev.width = 0.15
    base_bev.segments = 3

    # Lift assembly so bottom of base is at Z=0
    lift = (screen_h / 2) + (base_h / 2)
    monitor_obj.location.z = lift
    arm_obj.location.z += lift
    base_obj.location.z += lift

def main():
    clear_scene()
    create_monitor()

if __name__ == "__main__":
    main()
