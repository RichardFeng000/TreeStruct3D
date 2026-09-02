import bpy
import bmesh
import math
from mathutils import Vector, Matrix

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def get_scale_template():
    """
    Defines a template for a single woody scale of a pinecone.
    Returns a dictionary containing:
    - 'verts': List of local coordinates (Vector)
    - 'faces': List of tuples containing indices of vertices that form faces
    """
    # Define the shape of a curved, thickened scale
    # The scale extends along the Y axis.
    verts = [
        # Top shell points
        Vector((0, 0, 0)),            # 0: Base center
        Vector((0.15, 0, 0)),         # 1: Base right
        Vector((-0.15, 0, 0)),        # 2: Base left
        Vector((0.3, 0.4, 0.1)),      # 3: Mid outer right
        Vector((-0.3, 0.4, 0.1)),     # 4: Mid outer left
        Vector((0.2, 0.8, 0.2)),      # 5: Upper right
        Vector((-0.2, 0.8, 0.2)),     # 6: Upper left
        Vector((0, 1.1, 0.3)),        # 7: Tip
        
        # Bottom shell points (thickness)
        Vector((0, 0, -0.05)),        # 8: Base bottom center
        Vector((0.2, 0.4, -0.05)),    # 9: Mid inner right
        Vector((-0.2, 0.4, -0.05)),   # 10: Mid inner left
        Vector((0, 0.7, 0.1)),        # 11: Upper inner center
    ]
    
    faces = [
        # Top Surface
        (0, 2, 4), (0, 4, 3), (0, 3, 1), # Base to Mid
        (3, 4, 6), (3, 6, 5),            # Mid to Upper
        (5, 6, 7),                      # Upper to Tip
        
        # Bottom Surface
        (8, 10, 11), (8, 11, 9),        # Base to Inner
        (9, 11, 7),                     # Inner to Tip
        
        # Side Walls / Thickness
        (0, 1, 3, 9), (0, 9, 10, 2),    # Bottom thickness
        (1, 3, 5, 9), (2, 4, 6, 10),    # Mid walls
        (5, 7, 11, 6),                   # Top closure (approx)
        (5, 3, 9, 11), (6, 4, 10, 11),  # Side closures
    ]
    
    return {'verts': verts, 'faces': faces}

def generate_pinecone():
    clear_scene()
    
    # Pinecone parameters
    num_scales = 150
    golden_angle = math.radians(137.5)
    height = 5.0
    max_radius = 1.6
    
    template = get_scale_template()
    t_verts = template['verts']
    t_faces = template['faces']
    
    final_bm = bmesh.new()
    
    for i in range(num_scales):
        # Phyllotaxis spiral distribution
        phi = i * golden_angle
        
        # Normalize Z from 0 to 1 (bottom up)
        z_norm = i / num_scales
        z = z_norm * height - (height / 2.0)
        
        # Ovoid radius profile: tapered at ends, bulging in middle/lower-middle
        # Formula for an egg-like shape
        radius_profile = math.sin(math.pi * (z_norm + 0.1))
        r = max_radius * radius_profile
        if r < 0: r = 0
        
        x = r * math.cos(phi)
        y = r * math.sin(phi)
        pos = Vector((x, y, z))
        
        # Orientation logic
        # Scale base is at origin, length is along local Y.
        # We want the scale to point outwards from Z axis and slightly downwards.
        out_vec = Vector((x, y, 0)).normalized()
        if out_vec.length == 0:
            out_vec = Vector((1, 0, 0))
        
        # target_dir is the local Y axis for the scale template
        target_dir = (out_vec * 1.2 + Vector((0, 0, -0.5))).normalized()
        
        # Create rotation matrix to align Local Y with target_dir
        rot_quat = target_dir.to_track_quat('Y', 'Z')
        rot_mat = rot_quat.to_matrix().to_4x4()
        
        # Scaling based on height: larger scales at bottom, smaller at top
        scale_factor = 1.2 - (z_norm * 0.6)
        s_mat = Matrix.Scale(scale_factor, 4)
        
        trans_mat = Matrix.Translation(pos)
        final_mat = trans_mat @ rot_mat @ s_mat
        
        # Record start index for this scale's vertices to build faces correctly
        start_idx = len(final_bm.verts)
        
        # Transform and add template vertices
        for v_co in t_verts:
            final_bm.verts.new(final_mat @ v_co)
            
        final_bm.verts.ensure_lookup_table()
        
        # Add faces using the recorded start index
        for f_indices in t_faces:
            try:
                face_verts = [final_bm.verts[start_idx + idx] for idx in f_indices]
                final_bm.faces.new(face_verts)
            except ValueError:
                # Avoid duplicate faces or invalid geometry errors
                pass

    # Finalize the mesh
    mesh = bpy.data.meshes.new("Pinecone")
    final_bm.to_mesh(mesh)
    final_bm.free()
    
    obj = bpy.data.objects.new("Pinecone", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Material: Dark Brown Woody Appearance
    mat = bpy.data.materials.new(name="PineconeMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Dark, rich brown color
        bsdf.inputs['Base Color'].default_value = (0.06, 0.03, 0.01, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.85
        bsdf.inputs['Specular IOR Level'].default_value = 0.2

    obj.data.materials.append(mat)
    
    # Ensure object is centered at origin
    obj.location = (0, 0, 0)

if __name__ == "__main__":
    generate_pinecone()
