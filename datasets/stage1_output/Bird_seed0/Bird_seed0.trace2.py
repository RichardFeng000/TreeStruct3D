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
    # A wing is an assembly of layered "feathers" (flattened ellipsoids)
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Create several overlapping feather segments
    for i in range(12):
        # Define a simple elongated shape for each feather
        z_offset = i * 0.06
        # Vertices for a flattened pill-like shape
        # We create a small loop of vertices to make it look like a strip
        verts = []
        for angle in range(0, 361, 45):
            rad = math.radians(angle)
            v = Vector((
                0.2 * side * math.cos(rad),
                0.1 * math.sin(rad),
                z_offset + 0.1 * math.sin(rad)
            ))
            verts.append(bm.verts.new(v))
        
        # Create faces for the feather strip
        for j in range(len(verts)-1):
            bm.faces.new([verts[j], verts[j+1], Vector((0, 0, z_offset)).to_vector()]) # Simplified
    
    # Better approach: use a primitive and scale it per feather
    bm.free()
    bpy.data.meshes.remove(mesh)
    bpy.data.objects.remove(obj)

    # Alternative wing construction using separate mesh objects for better control
    wing_container = bpy.data.collections.new("Wing_" + name) # Not needed, just group them
    
    wing_group = []
    for i in range(10):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0))
        f = bpy.context.active_object
        f.name = f"Feather_{side}_{i}"
        # Scale into a feather shape: flat and long
        f.scale = (0.05 * side, 0.2, 0.1)
        # Position along the body
        f.location = (0.4 * side, 0, 0.6 + i * 0.08)
        f.rotation_euler = (math.radians(-20), math.radians(10 * side), 0)
        
        # Material: mostly dark, some white highlights
        mat = mat_dark if (i % 4 != 0) else mat_white
        f.data.materials.append(mat)
        apply_subsurf(f, 1)
        wing_group.append(f)

    return wing_group

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
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(0, 0, 0.7))
    body = bpy.context.active_object
    body.name = "BirdBody"
    body.scale = (1.1, 0.9, 0.8)
    apply_subsurf(body)
    
    # Assign materials based on position: Chest (Y < 0) vs Back (Y > 0)
    body.data.materials.append(mat_light) # Index 0
    body.data.materials.append(mat_dark)  # Index 1
    
    bm = bmesh.new()
    bm.from_mesh(body.data)
    for f in bm.faces:
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
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.06, radius2=0.01, depth=0.3, 
                                    location=(0, -0.55, 1.35), rotation=(math.radians(90), 0, 0))
    beak = bpy.context.active_object
    beak.name = "Beak"
    # Curve the beak slightly using BMesh
    bm = bmesh.new()
    bm.from_mesh(beak.data)
    for v in bm.verts:
        if v.co.z < 0: # Tip of cone after rotation is on negative Z locally? No, depends on axis.
            # In a default cone rotated (90,0,0), local Z is depth. 
            # The tip is at +depth/2 or -depth/2. Let's just offset the vertex with lowest X coordinate relative to root.
            pass
    # Simpler curvature: scale and move vertices manually based on their current position
    for v in bm.verts:
        if v.co.z < 0: # This depends on how cone was added. Let's use a simple logic.
             v.co.y -= 0.05 * (v.co.z + 0.15) # Arbitrary curvature
    bm.to_mesh(beak.data)
    bm.free()
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
            (0.0, -0.05, math.radians(-20)),    # Center toe
            (0.08, -0.05, math.radians(-45)),   # Right toe
            (-0.08, -0.05, math.radians(45)),   # Left toe
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
            bm = bmesh.new()
            bm.from_mesh(toe.data)
            for v in bm.verts:
                if v.co.z < 0: # Local bottom of cylinder is tip
                    v.co.x *= 0.2
                    v.co.y *= 0.2
            bm.to_mesh(toe.data)
            bm.free()

    create_leg(1)
    create_leg(-1)

    # Parenting for organization
    for obj in bpy.data.objects:
        if obj != body:
            obj.parent = body

if __name__ == "__main__":
    main()
