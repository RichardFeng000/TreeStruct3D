import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def apply_subsurf(obj, levels=2):
    mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    mod.levels = levels
    mod.render_levels = levels

def create_feathered_wing(name, side, mat_dark, mat_white):
    # Create a wing as a group of folded feathers
    num_feathers = 10
    for i in range(num_feathers):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0)
        f = bpy.context.active_object
        f.name = f"{name}_Feather_{i}"
        
        # Scale to look like a feather: thin, long, slightly flat
        f.scale = (0.05 * side, 0.1, 0.25)
        
        # Fold them along the body side
        # X is out, Y is slight offset, Z is distributed vertically
        x_pos = 0.45 * side
        y_pos = (i - num_feathers/2) * 0.03 # Slight overlap
        z_pos = 0.6 + (i * 0.08)
        f.location = (x_pos, y_pos, z_pos)
        
        # Rotate to hug the plump body
        f.rotation_euler = (math.radians(10), math.radians(20 * side), math.radians(-5))
        
        # Material: charcoal/black with white highlights
        mat = mat_white if (i % 4 == 0) else mat_dark
        f.data.materials.append(mat)
        apply_subsurf(f, 1)
    return

def main():
    clear_scene()

    # Materials
    mat_dark = create_material("DarkGray", (0.05, 0.05, 0.06, 1.0)) # Charcoal/Black
    mat_light = create_material("PaleGray", (0.7, 0.7, 0.7, 1.0))   # Pale Gray
    mat_beak = create_material("SalmonPink", (0.95, 0.5, 0.4, 1.0)) # Salmon-pink
    mat_feet = create_material("OrangeRed", (0.8, 0.2, 0.1, 1.0))   # Orange-red
    mat_eye = create_material("BlackEye", (0.01, 0.01, 0.01, 1.0))
    mat_white = create_material("WhiteHighlight", (0.9, 0.9, 0.9, 1.0))

    # --- Body ---
    # Center at Z=0.6 so it sits above ground
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 0.6))
    body = bpy.context.active_object
    body.name = "BirdBody"
    body.scale = (1.0, 0.8, 1.2) # Plump rounded shape
    apply_subsurf(body)
    
    # Two-tone coloring: Light chest (-Y), Dark back (+Y)
    body.data.materials.append(mat_light) 
    body.data.materials.append(mat_dark)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    for f in bm.faces:
        if f.calc_center_median().y < 0:
            f.material_index = 0 # Pale Gray
        else:
            f.material_index = 1 # Charcoal
    bm.to_mesh(body.data)
    bm.free()

    # --- Head ---
    # Positioned to connect with body top
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(0, -0.2, 1.3))
    head = bpy.context.active_object
    head.name = "BirdHead"
    apply_subsurf(head)
    head.data.materials.append(mat_light)

    # --- Beak ---
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.07, radius2=0.01, depth=0.3, 
                                    location=(0, -0.5, 1.25), rotation=(math.radians(90), 0, 0))
    beak = bpy.context.active_object
    beak.name = "Beak"
    # Curve the beak slightly downwards
    bm_beak = bmesh.new()
    bm_beak.from_mesh(beak.data)
    for v in bm_beak.verts:
        if v.co.z > 0: # tip of cone (after rotation)
            v.co.y -= 0.05 * (v.co.z**2)
    bm_beak.to_mesh(beak.data)
    bm_beak.free()
    beak.data.materials.append(mat_beak)

    # --- Eyes ---
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(0.18 * side, -0.35, 1.4))
        eye = bpy.context.active_object
        eye.data.materials.append(mat_eye)

    # --- Wings (Folded) ---
    create_feathered_wing("Wing_L", 1, mat_dark, mat_white)
    create_feathered_wing("Wing_R", -1, mat_dark, mat_white)

    # --- Legs and Feet ---
    def create_leg(side):
        # Leg stem: positioned to start at bottom of body (Z~0.2) down to ground (Z=0)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.3, location=(0.2 * side, 0, 0.15))
        leg = bpy.context.active_object
        leg.data.materials.append(mat_feet)
        
        # Clawed Toes
        toe_configs = [
            (0.0, -0.08, math.radians(-20)),  # Mid
            (0.07, -0.05, math.radians(-45)), # Right
            (-0.07, -0.05, math.radians(45)), # Left
            (0.0, 0.1, math.radians(180))     # Back
        ]
        for i, (off_x, off_y, rot_z) in enumerate(toe_configs):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=0.15, 
                                                location=(0.2 * side + off_x, off_y, 0.05),
                                                rotation=(math.radians(-30), 0, rot_z))
            toe = bpy.context.active_object
            toe.data.materials.append(mat_feet)
            # Taper toe to a point
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

    # Parenting for organization
    for obj in bpy.data.objects:
        if obj != body:
            obj.parent = body

if __name__ == "__main__":
    main()
