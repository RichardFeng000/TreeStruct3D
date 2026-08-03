import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5):
    """Creates a simple Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_monitor():
    # --- Parameters ---
    screen_w, screen_h, screen_d = 24.0, 14.0, 0.8
    bezel_thickness = 0.6
    base_w, base_d, base_h = 8.0, 5.0, 0.3
    arm_r, arm_h = 0.4, 4.0

    # Materials
    mat_bezel = create_material("BezelMat", (0.8, 0.75, 0.6, 1.0), metallic=0.9, roughness=0.2) # Tan-Silver
    mat_screen = create_material("ScreenMat", (0.3, 0.3, 0.3, 1.0), metallic=0.1, roughness=0.4)  # Gray Cloud-ish
    mat_base = create_material("BaseMat", (0.1, 0.1, 0.1, 1.0), metallic=0.5, roughness=0.6)     # Dark Base

    # --- 1. Monitor Chassis ---
    # X=Width, Y=Depth, Z=Height
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    monitor_obj = bpy.context.active_object
    monitor_obj.name = "Monitor_Chassis"
    monitor_obj.scale = (screen_w / 2, screen_d / 2, screen_h / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bm = bmesh.new()
    bm.from_mesh(monitor_obj.data)
    
    # Find the front face (Positive Y axis - facing forward)
    front_face = None
    for f in bm.faces:
        if f.normal.y > 0.9:
            front_face = f
            break
    
    if front_face:
        # Use inset_region instead of inset_individual for a single face
        res = bmesh.ops.inset_region(bm, faces=[front_face], thickness=bezel_thickness, use_boundary=True)
        screen_face = res['faces'][0]
        # Extrude inwards slightly to create the display recessed area
        bmesh.ops.translate(bm, verts=screen_face.verts, vec=(0, -0.1, 0))
        
        # Assign material indices
        # Index 0: Bezel, Index 1: Screen
        for f in bm.faces:
            f.material_index = 0 # Default all to bezel
        
        screen_face.material_index = 1
    
    bm.to_mesh(monitor_obj.data)
    bm.free()

    monitor_obj.data.materials.append(mat_bezel)
    monitor_obj.data.materials.append(mat_screen)

    # Add bevel for realism on the outer chassis
    bevel_mod = monitor_obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel_mod.width = 0.1
    bevel_mod.segments = 3

    # --- 2. Pedestal Arm ---
    # Positioned at the back (negative Y) and bottom of screen (negative Z)
    arm_z_pos = -screen_h/2 + arm_h/2
    arm_y_pos = -screen_d/4
    bpy.ops.mesh.primitive_cylinder_add(radius=arm_r, depth=arm_h, location=(0, arm_y_pos, arm_z_pos))
    arm_obj = bpy.context.active_object
    arm_obj.name = "Pedestal_Arm"
    arm_obj.data.materials.append(mat_base)

    # --- 3. Base Stand ---
    # Positioned at the very bottom
    base_z_pos = -screen_h/2
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, arm_y_pos, base_z_pos))
    base_obj = bpy.context.active_object
    base_obj.name = "Base_Stand"
    base_obj.scale = (base_w / 2, base_d / 2, base_h / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    base_obj.data.materials.append(mat_base)

    # Bevel the base
    base_bevel = base_obj.modifiers.new(name="Bevel", type='BEVEL')
    base_bevel.width = 0.15
    base_bevel.segments = 3

    # Final positioning: Lift everything so that the bottom of the base is at Z=0
    lift_amount = (screen_h / 2) + (base_h / 2)
    monitor_obj.location.z = lift_amount
    arm_obj.location.z += lift_amount
    base_obj.location.z += lift_amount

def main():
    clear_scene()
    create_monitor()

if __name__ == "__main__":
    main()
