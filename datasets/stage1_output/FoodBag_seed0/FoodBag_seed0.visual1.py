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
    # Dimensions - make it slightly more organic
    width = 1.2
    depth = 0.6 # Increased depth for better pillow effect
    height = 2.5
    res_x = 64 
    res_z = 128
    
    mesh = bpy.data.meshes.new("PouchMesh")
    obj = bpy.data.objects.new("FoodPackagingPouch", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    verts_front = []
    verts_back = []
    
    # Generate vertex grids for front and back with enhanced pillow bulge
    for i in range(res_z + 1):
        z_norm = (i / res_z) * 2 - 1 # -1 to 1
        z = z_norm * (height / 2)
        bulge_z = math.cos(z_norm * math.pi / 2) 
        
        row_front = []
        row_back = []
        for j in range(res_x + 1):
            x_norm = (j / res_x) * 2 - 1 # -1 to 1
            x = x_norm * (width / 2)
            bulge_x = math.cos(x_norm * math.pi / 2)
            
            # Stronger, more natural pillow bulge displacement
            offset = depth * 0.5 * (bulge_z ** 0.7 * bulge_x ** 0.7)
            
            row_front.append(bm.verts.new((x, offset, z)))
            row_back.append(bm.verts.new((x, -offset, z)))
        verts_front.append(row_front)
        verts_back.append(row_back)

    # Create faces for front and back sheets
    for i in range(res_z):
        for j in range(res_x):
            bm.faces.new((verts_front[i][j], verts_front[i][j+1], 
                          verts_front[i+1][j+1], verts_front[i+1][j]))
            bm.faces.new((verts_back[i][j], verts_back[i+1][j], 
                          verts_back[i+1][j+1], verts_back[i][j+1]))

    # Side seals - bridging front and back edges
    for i in range(res_z):
        bm.faces.new((verts_front[i][0], verts_back[i][0], 
                      verts_back[i+1][0], verts_front[i+1][0]))
        bm.faces.new((verts_front[i][res_x], verts_front[i+1][res_x], 
                      verts_back[i+1][res_x], verts_back[i][res_x]))

    # Top and Bottom seals
    for j in range(res_x):
        bm.faces.new((verts_front[0][j], verts_front[0][j+1], 
                      verts_back[0][j+1], verts_back[0][j]))
        bm.faces.new((verts_front[res_z][j], verts_back[res_z][j], 
                      verts_back[res_z][j+1], verts_front[res_z][j+1]))

    # --- Geometry Details: Pinching, Crimping and Folds ---
    for v in bm.verts:
        # Side seal pinching - make them tighter and more irregular
        if abs(v.co.x) >= (width / 2) * 0.95:
            v.co.y *= 0.1 # Tight pinch
            v.co.x += random.uniform(-0.015, 0.015)
            # Add vertical crinkles
            v.co.z += 0.02 * math.sin(v.co.z * 10 + v.co.x * 5)
        
        # Top and Bottom crimping (the zig-zag seals)
        if abs(v.co.z) >= (height / 2) - 0.08:
            wave = 0.04 * math.sin(v.co.x * 50)
            v.co.y += wave
            # Flatten the seals significantly in Z to look like heat-seals
            if v.co.z > 0:
                v.co.z = (height / 2) + (wave * 0.2)
            else:
                v.co.z = (-height / 2) - (wave * 0.2)

    bm.to_mesh(mesh)
    bm.free()

    # Subsurf for smoother pillow look
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2

    return obj

def assign_materials(obj):
    colors = {
        "GreenLight": (0.4, 0.9, 0.4, 1.0),
        "GreenDark": (0.1, 0.6, 0.1, 1.0),
        "CoralOrange": (1.0, 0.45, 0.3, 1.0), # Punchier coral
        "DarkBrownBlack": (0.08, 0.05, 0.03, 1.0),
        "WhiteStriped": (0.9, 0.9, 0.9, 1.0),
        "BlackStriped": (0.05, 0.05, 0.05, 1.0),
        "TanCream1": (0.88, 0.78, 0.65, 1.0), # Tan
        "TanCream2": (0.98, 0.94, 0.88, 1.0)  # Cream
    }
    
    mats = {}
    for name, color in colors.items():
        mat = create_material(name, color)
        obj.data.materials.append(mat)
        mats[name] = len(obj.data.materials) - 1

    mesh = obj.data
    height = 2.5
    width = 1.2
    
    # Polka dot grid setup for the green section
    dot_spacing = 0.4
    dots = []
    for dx in [-0.3, 0.3]:
        for dz in [0.8, 1.2, 1.6]: # Offset within top zone
            dots.append((dx, dz))

    for face in mesh.polygons:
        center = face.center
        z = center.z
        x = center.x
        
        # Priority 1: Side seams (Tan-Cream Stripes)
        if abs(x) > (width / 2) * 0.9:
            # Vertical stripes on the seals
            if int(center.z * 8) % 2 == 0:
                face.material_index = mats["TanCream1"]
            else:
                face.material_index = mats["TanCream2"]
            continue
            
        # Vertical Bands logic
        if z > height * 0.2: # Top Section - Green Polka Dots
            is_dot = False
            for dx, dz in dots:
                dist = math.sqrt((x - dx)**2 + (z - dz)**2)
                if dist < 0.12:
                    is_dot = True
                    break
            face.material_index = mats["GreenDark"] if is_dot else mats["GreenLight"]

        elif z > -height * 0.3: # Middle Section - Coral Orange
            # Occasional white-and-black striped accents near transition zones
            if (z > height * 0.15 and z < height * 0.25) or \
               (z < -height * 0.25 and z > -height * 0.3):
                if int(center.x * 25) % 2 == 0:
                    face.material_index = mats["WhiteStriped"]
                else:
                    face.material_index = mats["BlackStriped"]
            else:
                face.material_index = mats["CoralOrange"]
        
        else: # Lower Section - Dark Brown Black
            face.material_index = mats["DarkBrownBlack"]

def main():
    clear_scene()
    pouch_obj = create_pouch()
    assign_materials(pouch_obj)
    
    for poly in pouch_obj.data.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    main()
