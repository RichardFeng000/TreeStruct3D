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
    return mat

def create_bract_mesh():
    """Generates a single leaf-like bract mesh object."""
    bm = bmesh.new()
    
    # Parameters for the leaf shape
    length = 1.4
    width = 0.35
    segments = 12
    
    verts_l = []
    verts_r = []
    
    for i in range(segments + 1):
        t = i / segments
        # Width profile: starts narrow, peaks early (around t=0.3), then tapers to a point
        # Use a combination of sine and linear taper for an organic leaf shape
        w = width * math.sin(math.pi * t) * (1.2 - t) 
        if w < 0: w = 0
        
        # Z is the length of the leaf
        z = t * length
        # Longitudinal curve for organic look - slight bend and offset
        x_offset = 0.3 * (t**2) 
        y_curve = -0.15 * math.sin(math.pi * t)
        
        verts_l.append(bm.verts.new((x_offset - w, y_curve, z)))
        verts_r.append(bm.verts.new((x_offset + w, y_curve, z)))

    # Create faces between the strips
    for i in range(segments):
        try:
            bm.faces.new((verts_l[i], verts_l[i+1], verts_r[i+1], verts_r[i]))
        except ValueError:
            pass

    # Give it thickness via extrusion for a non-zero volume
    # We use the bmesh operator to extrude faces along their normals or a specific axis
    geom = bm.faces[:]
    res = bmesh.ops.extrude_face_region(bm, geom=geom)
    
    # To give it actual thickness, we move the extruded vertices
    # The result of extrude_face_region contains the new geometry in 'geom'
    for v in res['geom']:
        if isinstance(v, bmesh.types.BMVert):
            v.co.y -= 0.03 # Shift slightly on Y to create thickness

    # Close the gap between original and extruded if necessary? 
    # actually extrude_face_region already creates the side faces.
    
    mesh = bpy.data.meshes.new("BractMesh")
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def assemble_veratrum():
    clear_scene()

    # Materials for gradient effect: Dark Green -> Mid Green -> Light Green
    dark_green = create_material("DarkGreen", (0.02, 0.1, 0.02, 1.0))
    mid_green = create_material("MidGreen", (0.05, 0.2, 0.05, 1.0))
    light_green = create_material("LightGreen", (0.15, 0.35, 0.15, 1.0))

    # Central Stem parameters
    stem_radius = 0.18
    stem_height = 7.5
    
    # Create the central stem
    bpy.ops.mesh.primitive_cylinder_add(
        radius=stem_radius, 
        depth=stem_height, 
        location=(0, 0, stem_height / 2)
    )
    stem = bpy.context.active_object
    stem.name = "Stem"
    stem.data.materials.append(dark_green)

    # Create the bract mesh asset (not linked to scene yet)
    bract_mesh = create_bract_mesh()

    # Distribution parameters for a columnar flower stalk (Phyllotaxis)
    num_bracts = 180
    golden_angle = math.pi * (3 - math.sqrt(5)) # approx 137.5 degrees
    z_spacing = stem_height / num_bracts
    
    all_bract_objs = []

    for i in range(num_bracts):
        # Position calculations
        angle = i * golden_angle
        z = i * z_spacing
        
        # Create new object using the shared mesh data to save memory before joining
        bract_obj = bpy.data.objects.new(f"Bract_{i}", bract_mesh)
        bpy.context.collection.objects.link(bract_obj)
        
        # Position on circumference of stem
        bract_obj.location = (math.cos(angle) * stem_radius, math.sin(angle) * stem_radius, z)
        
        # Rotation: align to radial vector and tilt upwards
        # 1. Rotate around Z to face outward from center
        rot_z = Matrix.Rotation(angle, 4, 'Z')
        # 2. Tilt up along the local X axis (relative to its position) so they point mostly up
        # A higher angle makes them more upright/columnar
        rot_tilt = Matrix.Rotation(math.radians(35), 4, 'X')
        
        bract_obj.rotation_mode = 'QUATERNION'
        combined_rot = rot_z @ rot_tilt
        bract_obj.rotation_quaternion = combined_rot.to_quaternion()
        
        # Scale based on height: taper slightly at the top for a natural look
        scale_factor = 1.0 - (i / num_bracts) * 0.4
        bract_obj.scale = (scale_factor, scale_factor, scale_factor)

        # Assign material based on height to simulate gradient
        if i < num_bracts * 0.35:
            mat = dark_green
        elif i < num_bracts * 0.7:
            mat = mid_green
        else:
            mat = light_green
        bract_obj.data.materials.append(mat)
        
        all_bract_objs.append(bract_obj)

    # Join all bracts and stem into one single object for final output
    bpy.ops.object.select_all(action='DESELECT')
    stem.select_set(True)
    for obj in all_bract_objs:
        obj.select_set(True)
    
    bpy.context.view_layer.objects.active = stem
    bpy.ops.object.join()
    
    # Final Polish
    # Set shading to smooth for organic look
    bpy.ops.object.shade_smooth()
    
    # Add a subdivision surface modifier for smoothness
    subdiv = stem.modifiers.new(name="Subdiv", type='SUBSURF')
    subdiv.levels = 1
    subdiv.render_levels = 2

if __name__ == "__main__":
    assemble_veratrum()
