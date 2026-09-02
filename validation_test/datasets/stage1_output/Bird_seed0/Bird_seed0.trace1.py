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
    # Create a wing as a series of overlapping plates to simulate feathers
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Create several "feather" segments
    for i in range(8):
        # Each feather is a flattened sphere/ellipsoid segment
        v1 = Vector((0, -0.2 + i*0.05, 0))
        v2 = Vector((0.3 * side, -0.1 + i*0.05, 0.2))
        v3 = Vector((0.4 * side, 0.1 + i*0.05, 0.1))
        v4 = Vector((0, 0.2 + i*0.05, -0.1))
        
        # Simple quad for each feather scale
        face = bm.faces.new([bm.verts.new(v1), bm.verts.new(v2), bm.verts.new(v3), bm.verts.new(v4)])
        # Randomly assign white highlights to some feathers
        face.material_index = 1 if (i % 5 == 0) else 0

    bm.to_mesh(mesh)
    bm.free()
    
    obj.data.materials.append(mat_dark)
    obj.data.materials.append(mat_white)
    
    # Position and shape the wing to fold against body
    obj.location = (0.3 * side, 0, 0.7)
    obj.rotation_euler = (0, math.radians(15 * side), math.radians(-20 * side))
    obj.scale = (1, 1.2, 1)
    
    apply_subsurf(obj, 1)
    return obj

def main():
    clear_scene()

    # Materials
    mat_dark = create_material("DarkGray", (0.05, 0.05, 0.06, 1.0)) # Charcoal/Black
    mat_light = create_material("PaleGray", (0.7, 0.7, 0.7, 1.0))   # Pale Gray
    mat_beak = create_material("SalmonPink", (0.95, 0.5, 0.4, 1.0)) # Salmon-pink
    mat_feet = create_material("OrangeRed", (0.8, 0.2, 0.1, 1.0))   # Orange-red
    mat_eye = create_material("BlackEye", (0.01, 0.01, 0.01, 1.0))
    mat_white = create_material("WhiteHighlight", (0.9, 0.9, 0.9, 1.0))

    # Body: Plump rounded shape
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(0, 0, 0.7))
    body = bpy.context.active_object
    body.name = "BirdBody"
    body.scale = (1.1, 0.9, 0.8)
    apply_subsurf(body)
    
    # Material assignment for body: Chest vs Back
    body.data.materials.append(mat_light) # Index 0: Pale Gray
    body.data.materials.append(mat_dark)  # Index 1: Dark Charcoal
    
    bm = bmesh.new()
    bm.from_mesh(body.data)
    for f in bm.faces:
        if f.calc_center_median().y < 0: # Chest side (negative Y)
            f.material_index = 0
        else: # Back side
            f.material_index = 1
    bm.to_mesh(body.data)
    bm.free()

    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(0, -0.2, 1.4))
    head = bpy.context.active_object
    head.name = "BirdHead"
    head.scale = (0.9, 0.8, 0.9)
    apply_subsurf(head)
    head.data.materials.append(mat_light)

    # Beak: Short slightly curved salmon-pink beak
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.06, radius2=0.01, depth=0.25, 
                                    location=(0, -0.5, 1.35), rotation=(math.radians(90), 0, 0))
    beak = bpy.context.active_object
    beak.name = "Beak"
    
    # Curve the beak using bmesh
    bm = bmesh.new()
    bm.from_mesh(beak.data)
    for v in bm.verts:
        if v.co.z < 0: # Tip of cone (after rotation, Z is local height/length)
            # Shift tip slightly to create a curve effect relative to the root
            v.co.y -= 0.05 
    bm.to_mesh(beak.data)
    bm.free()
    beak.data.materials.append(mat_beak)

    # Eyes
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.04, location=(0.18 * side, -0.35, 1.5))
        eye = bpy.context.active_object
        eye.name = f"Eye_{side}"
        eye.data.materials.append(mat_eye)

    # Wings: Folded against the body with white highlights
    create_feathered_wing("Wing_L", 1, mat_dark, mat_white)
    create_feathered_wing("Wing_R", -1, mat_dark, mat_white)

    # Legs and Feet
    def create_leg(side):
        # Leg stem
        bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.4, location=(0.2 * side, 0, 0.3))
        leg = bpy.context.active_object
        leg.name = f"Leg_{side}"
        leg.data.materials.append(mat_feet)
        
        # Clawed Toes (Front 3, Back 1)
        toe_configs = [
            (0.0, 0, math.radians(-20)),    # Center toe
            (0.1, 0.1, math.radians(-45)),  # Right toe
            (-0.1, 0.1, math.radians(45)),  # Left toe
            (0.0, -0.15, math.radians(180)) # Hallux (back)
        ]
        
        for i, (off_x, off_y, rot_z) in enumerate(toe_configs):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=0.15, 
                                                location=(0.2 * side + off_x, off_y, 0.1),
                                                rotation=(math.radians(-30), 0, rot_z))
            toe = bpy.context.active_object
            toe.name = f"Toe_{side}_{i}"
            toe.data.materials.append(mat_feet)
            
            # Taper the toe to a point
            bm = bmesh.new()
            bm.from_mesh(toe.data)
            for v in bm.verts:
                if v.co.z < 0: # Local bottom of cylinder is tip
                    v.co.x *= 0.3
                    v.co.y *= 0.3
            bm.to_mesh(toe.data)
            bm.free()

    create_leg(1)
    create_leg(-1)

    # Feather detail: Add a displacement modifier to body and head for fluffiness
    def add_feather_detail(obj):
        mod = obj.modifiers.new(name="FeatherNoise", type='DISPLACE')
        tex = bpy.data.textures.new("FeatherTex", type='NOISE')
        tex.noise_scale = 0.04
        mod.texture = tex
        mod.strength = 0.03

    add_feather_detail(body)
    add_feather_detail(head)

    # Parent everything to body for organization and centering
    for obj in bpy.data.objects:
        if obj != body:
            obj.parent = body

if __name__ == "__main__":
    main()
