import bpy
import bmesh
import math
import random

def clear_scene():
    """Clear the default Blender scene."""
    if "Cube" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
    if "Camera" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Camera"], do_unlink=True)
    if "Light" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Light"], do_unlink=True)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, color):
    """Create a simple material with a base color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_pouch():
    # Dimensions
    width = 1.2
    depth = 0.4
    height = 2.5
    res_x = 48 # Higher resolution for "patterns"
    res_z = 96
    
    mesh = bpy.data.meshes.new("PouchMesh")
    obj = bpy.data.objects.new("FoodPackagingPouch", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    verts_front = []
    verts_back = []
    
    # Generate vertex grids for front and back
    for i in range(res_z + 1):
        z = (i / res_z) * height - (height / 2)
        bulge_z = math.sin(math.pi * (i / res_z)) 
        
        row_front = []
        row_back = []
        for j in range(res_x + 1):
            x_norm = (j / res_x) * 2 - 1 # -1 to 1
            x = x_norm * (width / 2)
            bulge_x = math.cos(math.pi * x_norm / 2)
            
            # Pillow bulge displacement
            offset = depth * 0.5 * (bulge_z * bulge_x)
            
            row_front.append(bm.verts.new((x, offset, z)))
            row_back.append(bm.verts.new((x, -offset, z)))
        verts_front.append(row_front)
        verts_back.append(row_back)

    # Create faces for front and back sheets
    for i in range(res_z):
        for j in range(res_x):
            # Front face
            bm.faces.new((verts_front[i][j], verts_front[i][j+1], 
                          verts_front[i+1][j+1], verts_front[i+1][j]))
            # Back face (reversed winding)
            bm.faces.new((verts_back[i][j], verts_back[i+1][j], 
                          verts_back[i+1][j+1], verts_back[i][j+1]))

    # Side seals - bridging front and back edges
    for i in range(res_z):
        # Left seal (x = -width/2)
        bm.faces.new((verts_front[i][0], verts_back[i][0], 
                      verts_back[i+1][0], verts_front[i+1][0]))
        # Right seal (x = width/2)
        bm.faces.new((verts_front[i][res_x], verts_front[i+1][res_x], 
                      verts_back[i+1][res_x], verts_back[i][res_x]))

    # Top and Bottom seals
    for j in range(res_x):
        # Bottom seal (z = -height/2)
        bm.faces.new((verts_front[0][j], verts_front[0][j+1], 
                      verts_back[0][j+1], verts_back[0][j]))
        # Top seal (z = height/2)
        bm.faces.new((verts_front[res_z][j], verts_back[res_z][j], 
                      verts_back[res_z][j+1], verts_front[res_z][j+1]))

    # --- Geometry Details: Pinching, Crimping and Folds ---
    for v in bm.verts:
        # Side seal pinching
        if abs(v.co.x) >= (width / 2) * 0.98:
            v.co.y *= 0.4
            # Add some slight randomness to make it look "folded"
            v.co.x += random.uniform(-0.01, 0.01)
        
        # Top and Bottom crimping (the zig-zag seals)
        if abs(v.co.z) >= (height / 2) - 0.05:
            wave = 0.03 * math.sin(v.co.x * 40)
            v.co.y += wave
            # Flatten the seals slightly in Z
            if v.co.z > 0:
                v.co.z = (height / 2) + (wave * 0.5)
            else:
                v.co.z = (-height / 2) - (wave * 0.5)

    bm.to_mesh(mesh)
    bm.free()

    # Smooth it out with subdivision
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2

    return obj

def assign_materials(obj):
    colors = {
        "GreenLight": (0.3, 0.8, 0.3, 1.0),
        "GreenDark": (0.1, 0.5, 0.1, 1.0),
        "CoralOrange": (1.0, 0.5, 0.3, 1.0),
        "DarkBrownBlack": (0.12, 0.08, 0.06, 1.0),
        "WhiteStriped": (0.95, 0.95, 0.95, 1.0),
        "BlackStriped": (0.1, 0.1, 0.1, 1.0),
        "TanCream": (0.88, 0.78, 0.65, 1.0)
    }
    
    mats = {}
    for name, color in colors.items():
        mat = create_material(name, color)
        obj.data.materials.append(mat)
        mats[name] = len(obj.data.materials) - 1

    mesh = obj.data
    height = 2.5
    width = 1.2
    
    for face in mesh.polygons:
        center = face.center
        z = center.z
        x = center.x
        
        # Priority 1: Side seams (Tan Cream)
        if abs(x) > (width / 2) * 0.9:
            face.material_index = mats["TanCream"]
            continue
            
        # Vertical Bands logic
        # Green polka-dot area (Top section)
        if z > height * 0.2:
            # Simulate polka dots by checking a grid of the center coordinates
            # We use modulo to alternate between light and dark green
            if (int(center.x * 15) + int(center.z * 15)) % 2 == 0:
                face.material_index = mats["GreenLight"]
            else:
                face.material_index = mats["GreenDark"]
        # Coral Orange middle section
        elif z > -height * 0.3:
            # Occasional white-and-black striped accents near the transitions
            if (z > height * 0.15 and z < height * 0.25) or \
               (z < -height * 0.25 and z > -height * 0.3):
                if int(center.x * 20) % 2 == 0:
                    face.material_index = mats["WhiteStriped"]
                else:
                    face.material_index = mats["BlackStriped"]
            else:
                face.material_index = mats["CoralOrange"]
        # Dark Brown-Black lower zone
        else:
            face.material_index = mats["DarkBrownBlack"]

def main():
    clear_scene()
    pouch_obj = create_pouch()
    assign_materials(pouch_obj)
    
    for poly in pouch_obj.data.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    main()
