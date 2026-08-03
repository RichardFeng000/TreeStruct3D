import bpy
import bmesh
import math
from mathutils import Vector, Matrix

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Creates a simple principled BSDF material with a specific color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 0.5
        bsdf.inputs['Specular IOR Level'].default_value = 0.2
    return mat

def create_bract_mesh():
    """Generates a single leaf-like bract mesh object."""
    bm = bmesh.new()
    
    length = 1.8 # Slightly longer for better overlap
    width = 0.45
    segments = 20
    
    verts_l = []
    verts_r = []
    
    for i in range(segments + 1):
        t = i / segments
        # Width profile: wider at base, tapering to a sharp point
        w = width * math.cos((math.pi/2) * t)
        if w < 0: w = 0
        
        z = t * length
        # Slight organic curve outward and upward
        x_offset = 0.1 * math.sin(math.pi * t)
        y_curve = -0.1 * (t**2)
        
        verts_l.append(bm.verts.new((x_offset - w, y_curve, z)))
        verts_r.append(bm.verts.new((x_offset + w, y_curve, z)))

    for i in range(segments):
        try:
            bm.faces.new((verts_l[i], verts_l[i+1], verts_r[i+1], verts_r[i]))
        except ValueError:
            pass

    # Give it a tiny bit of thickness for rendering stability
    geom = bm.faces[:]
    res = bmesh.ops.extrude_face_region(bm, geom=geom)
    for v in res['geom']:
        if isinstance(v, bmesh.types.BMVert):
            v.co.y -= 0.01

    mesh = bpy.data.meshes.new("BractMesh")
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def assemble_veratrum():
    clear_scene()

    # Brighter, more distinct colors to ensure the gradient is visible in render
    dark_green = create_material("DarkGreen", (0.01, 0.12, 0.01, 1.0))
    mid_green = create_material("MidGreen", (0.15, 0.38, 0.15, 1.0))
    light_green = create_material("LightGreen", (0.4, 0.7, 0.2, 1.0))

    stem_radius = 0.15
    stem_height = 8.0
    
    bpy.ops.mesh.primitive_cylinder_add(
        radius=stem_radius, 
        depth=stem_height, 
        location=(0, 0, stem_height / 2)
    )
    stem = bpy.context.active_object
    stem.name = "Stem"
    stem.data.materials.append(dark_green)

    bract_mesh = create_bract_mesh()

    # Increased count for a denser, tighter columnar look
    num_bracts = 140
    golden_angle = math.pi * (3 - math.sqrt(5)) 
    z_spacing = stem_height / num_bracts
    
    all_bract_objs = []

    for i in range(num_bracts):
        angle = i * golden_angle
        z = i * z_spacing
        
        bract_obj = bpy.data.objects.new(f"Bract_{i}", bract_mesh)
        bpy.context.collection.objects.link(bract_obj)
        
        # Place on stem surface
        bract_obj.location = (math.cos(angle) * stem_radius, math.sin(angle) * stem_radius, z)
        
        # Rotation: Face outward and tilt slightly more vertical for tighter column
        rot_z = Matrix.Rotation(angle, 4, 'Z')
        rot_tilt = Matrix.Rotation(math.radians(15), 4, 'X') # Tighter angle than before
        
        bract_obj.rotation_mode = 'QUATERNION'
        combined_rot = rot_z @ rot_tilt
        bract_obj.rotation_quaternion = combined_rot.to_quaternion()
        
        # Scale: Subtle taper towards the top
        scale_factor = 1.0 - (i / num_bracts) * 0.4
        bract_obj.scale = (scale_factor, scale_factor, scale_factor)

        # Material gradient based on height (Base -> Middle -> Tip)
        if i < num_bracts * 0.35:
            mat = dark_green
        elif i < num_bracts * 0.70:
            mat = mid_green
        else:
            mat = light_green
        bract_obj.data.materials.append(mat)
        
        all_bract_objs.append(bract_obj)

    # Join for final output
    bpy.ops.object.select_all(action='DESELECT')
    stem.select_set(True)
    for obj in all_bract_objs:
        obj.select_set(True)
    
    bpy.context.view_layer.objects.active = stem
    bpy.ops.object.join()
    
    bpy.ops.object.shade_smooth()
    subdiv = stem.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 1

if __name__ == "__main__":
    assemble_veratrum()
