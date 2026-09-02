import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def apply_subsurf(obj, levels=2):
    """Adds a subdivision surface modifier to an object."""
    mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    mod.levels = levels
    mod.render_levels = levels

def create_feathered_wing(name, side, mat_dark, mat_white):
    """Creates a folded wing composed of layered elongated ellipsoids."""
    # We'll create several 'feather' meshes and parent them to the body
    feathers = []
    num_feathers = 12
    for i in range(num_feathers):
        # Each feather is a scaled sphere
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0))
        f = bpy.context.active_object
        f.name = f"{name}_Feather_{i}"
        
        # Scale into a feather shape: flat and long
        f.scale = (0.06 * side, 0.15, 0.3)
        
        # Position them to look folded along the body
        # X is outwards from center, Z goes up/down, Y is slight offset for thickness
        z_pos = 0.5 + (i * 0.07)
        x_pos = 0.45 * side + (i * 0.01 * side)
        y_pos = -0.05 + (i * 0.01)
        f.location = (x_pos, y_pos, z_pos)
        
        # Rotation to angle the feathers downwards and slightly inwards
        f.rotation_euler = (math.radians(10), math.radians(20 * side), math.radians(-15 * side))
        
        # Assign material: mostly charcoal/black, some white highlights
        mat = mat_white if (i % 5 == 0) else mat_dark
        f.data.materials.append(mat)
        apply_subsurf(f, 1)
        feathers.append(f)
    return feathers

def main():
    clear_scene()

    # Materials
    mat_dark = create_material("DarkGray", (0.05, 0.05, 0.06, 1.0))  # Charcoal/Black
    mat_light = create_material("PaleGray", (0.7, 0.7, 0.7, 1.0))    # Pale Gray
    mat_beak = create_material("SalmonPink", (0.95, 0.5, 0.4, 1.0))  # Salmon-pink
    mat_feet = create_material("OrangeRed", (0.8, 0.2, 0.1, 1.0))    # Orange-red
    mat_eye = create_material("BlackEye", (0.01, 0.01, 0.01, 1.0))
    mat_white = create_material("WhiteHighlight", (0.9, 0.9, 0.9, 1.0))

    # --- Body ---
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(0, 0, 0.7))
    body = bpy.context.active_object
    body.name = "BirdBody"
    body.scale = (1.1, 0.9, 0.8)
    apply_subsurf(body)
    
    # Assign materials based on position: Chest (-Y) vs Back (+Y)
    # To do this we need to assign multiple materials and set face indices
    body.data.materials.append(mat_light) # Index 0 (Chest)
    body.data.materials.append(mat_dark)  # Index 1 (Back/Wings area)
    
    bm = bmesh.new()
    bm.from_mesh(body.data)
    for f in bm.faces:
        # Bird faces -Y direction, so Y < 0 is chest
        if f.calc_center_median().y < 0:
            f.material_index = 0
        else:
            f.material_index = 1
    bm.to_mesh(body.data)
    bm.free()

    # --- Head ---
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(0, -0.25, 1.4))
    head = bpy.context.active_object
    head.name = "BirdHead"
    head.scale = (0.9, 0.8, 0.9)
    apply_subsurf(head)
    head.data.materials.append(mat_light)

    # --- Beak ---
    # Use a cone and then deform it via bmesh to be curved
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.06, radius2=0.01, depth=0.3, 
                                    location=(0, -0.55, 1.35), rotation=(math.radians(90), 0, 0))
    beak = bpy.context.active_object
    beak.name = "Beak"
    
    bm_beak = bmesh.new()
    bm_beak.from_mesh(beak.data)
    for v in bm_beak.verts:
        # In a cone rotated (90,0,0), local Z is the height of the cone
        # The tip is usually at +depth/2 or -depth/2 relative to center
        # We curve it slightly downwards (Y axis) based on its distance from base
        dist = v.co.z # Local coordinate after rotation? No, BMesh uses local coords.
        # For a cone rotated by 90 deg X, the "height" is actually along the original Z.
        # Let's apply curvature: if z > 0 (tip), move it slightly in Y.
        if v.co.z > 0:
            v.co.y -= 0.05 * (v.co.z**2) 
    bm_beak.to_mesh(beak.data)
    bm_beak.free()
    beak.data.materials.append(mat_beak)

    # --- Eyes ---
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0.2 * side, -0.4, 1.5))
        eye = bpy.context.active_object
        eye.name = f"Eye_{side}"
        eye.data.materials.append(mat_eye)

    # --- Wings ---
    create_feathered_wing("Wing_L", 1, mat_dark, mat_white)
    create_feathered_wing("Wing_R", -1, mat_dark, mat_white)

    # --- Legs and Feet ---
    def create_leg(side):
        # Leg stem
        bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.4, location=(0.2 * side, 0, 0.3))
        leg = bpy.context.active_object
        leg.name = f"Leg_{side}"
        leg.data.materials.append(mat_feet)
        
        # Clawed Toes (Front 3, Back 1)
        toe_configs = [
            (0.0, -0.06, math.radians(-20)),    # Center toe
            (0.08, -0.04, math.radians(-45)),   # Right toe
            (-0.08, -0.04, math.radians(45)),   # Left toe
            (0.0, 0.12, math.radians(180))      # Hallux (back)
        ]
        
        for i, (off_x, off_y, rot_z) in enumerate(toe_configs):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=0.18, 
                                                location=(0.2 * side + off_x, off_y, 0.1),
                                                rotation=(math.radians(-30), 0, rot_z))
            toe = bpy.context.active_object
            toe.name = f"Toe_{side}_{i}"
            toe.data.materials.append(mat_feet)
            
            # Taper the toe to a point using BMesh
            bm_toe = bmesh.new()
            bm_toe.from_mesh(toe.data)
            for v in bm_toe.verts:
                if v.co.z < 0: # Local bottom of cylinder is tip
                    v.co.x *= 0.2
                    v.co.y *= 0.2
            bm_toe.to_mesh(toe.data)
            bm_toe.free()

    create_leg(1)
    create_leg(-1)

    # Parenting for organization and clean scene structure
    for obj in bpy.data.objects:
        if obj != body:
            obj.parent = body

if __name__ == "__main__":
    main()
