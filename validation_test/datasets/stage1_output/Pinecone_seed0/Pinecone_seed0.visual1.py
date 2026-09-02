import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_scale_geometry():
    """
    Creates a curved, woody scale mesh template.
    The scale is oriented such that its base is at the origin (0,0,0) 
    and it extends along the Y axis.
    """
    bm = bmesh.new()
    
    # Define points for a curved "petal" shape
    # x: width, y: length, z: height/curvature
    # Bottom base (attached to core)
    v0 = bm.verts.new((0, 0, 0))
    v1 = bm.verts.new((0.2, 0, 0))
    v2 = bm.verts.new((-0.2, 0, 0))
    
    # Middle section (widest and most curved)
    v3 = bm.verts.new((0.4, 0.4, 0.1))
    v4 = bm.verts.new((-0.4, 0.4, 0.1))
    v5 = bm.verts.new((0.3, 0.6, 0.2))
    v6 = bm.verts.new((-0.3, 0.6, 0.2))
    
    # Tip (tapering)
    v7 = bm.verts.new((0, 1.1, 0.3))
    
    # Thickness / Bottom side of the scale to make it "woody" and solid
    v8 = bm.verts.new((0, 0, -0.05))
    v9 = bm.verts.new((0.3, 0.4, -0.05))
    v10 = bm.verts.new((-0.3, 0.4, -0.05))
    v11 = bm.verts.new((0, 0.7, 0.1))

    # Faces for the top surface (the "shell")
    bm.faces.new([v0, v2, v4])
    bm.faces.new([v0, v4, v3])
    bm.faces.new([v0, v3, v1])
    bm.faces.new([v3, v4, v6])
    bm.faces.new([v3, v6, v5])
    bm.faces.new([v5, v6, v7])
    
    # Faces for the bottom surface (the "meat" of the scale)
    bm.faces.new([v8, v10, v11])
    bm.faces.new([v8, v11, v9])
    bm.faces.new([v9, v11, v7]) # connect to tip
    
    # Closing the sides for volume
    bm.faces.new([v0, v1, v3, v8])
    bm.faces.new([v0, v2, v4, v8])
    bm.faces.new([v1, v3, v5, v9]) # simplified bridge
    bm.faces.new([v2, v4, v6, v10])
    bm.faces.new([v5, v7, v11, v6])

    # Convert BMesh to a temporary mesh for reuse if needed, 
    # but here we just return the BM and free it later or use its data.
    return bm

def generate_pinecone():
    clear_scene()
    
    # Pinecone parameters
    num_scales = 140
    golden_angle = math.radians(137.5)
    height = 6.0
    max_radius = 1.8
    
    # Create a template scale BMesh
    temp_bm = create_scale_geometry()
    template_verts = [v.co.copy() for v in temp_bm.verts]
    template_faces = [f.verts[:] for f in temp_bm.faces]
    temp_bm.free()
    
    final_bm = bmesh.new()
    
    for i in range(num_scales):
        # Phyllotaxis spiral distribution
        phi = i * golden_angle
        
        # Normalize Z from 0 to 1 (bottom up)
        z_norm = i / num_scales
        z = z_norm * height - (height / 2.0)
        
        # Ovoid radius calculation: Wider at the bottom, tapering at top and bottom
        # Using a sine-like profile for an egg shape
        radius_profile = math.sin(math.pi * (z_norm + 0.1)) 
        r = max_radius * radius_profile
        if r < 0: r = 0
        
        x = r * math.cos(phi)
        y = r * math.sin(phi)
        pos = Vector((x, y, z))
        
        # Orientation logic
        # Normal points outwards from the center axis (Z is up)
        normal_vec = Vector((x, y, 0)).normalized()
        if normal_vec.length == 0: normal_vec = Vector((1, 0, 0))
        
        # We want the scale to point "down" and "out".
        # Target direction for the Y axis of our template (the length)
        target_dir = (normal_vec * 1.0 + Vector((0, 0, -0.6))).normalized()
        
        # Rotation matrix: align local Y with target_dir
        rot_quat = target_dir.to_track_quat('Y', 'Z')
        rot_mat = rot_quat.to_matrix().to_4x4()
        
        # Apply scaling to make the pinecone look cohesive (scales larger at bottom)
        scale_factor = 0.8 + (1.0 - z_norm) * 0.5
        s_mat = Matrix.Scale(scale_factor, 4)
        
        trans_mat = Matrix.Translation(pos)
        final_mat = trans_mat @ rot_mat @ s_mat
        
        # Add transformed scale to the main mesh
        start_idx = len(final_bm.verts)
        for v_co in template_verts:
            final_bm.verts.new(final_mat @ v_co)
            
        final_bm.verts.ensure_lookup_table()
        for f_indices in template_faces:
            try:
                final_bm.faces.new([final_bm.verts[start_idx + idx] for idx in f_indices])
            except ValueError:
                pass

    # Finalize the mesh
    mesh = bpy.data.meshes.new("Pinecone")
    final_bm.to_mesh(mesh)
    final_bm.free()
    
    obj = bpy.data.objects.new("Pinecone", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Material: Dark Brown, Realistic Natural Appearance
    mat = bpy.data.materials.new(name="PineconeMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Rich dark woody brown
        bsdf.inputs['Base Color'].default_value = (0.08, 0.04, 0.02, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.9
        bsdf.inputs['Specular IOR Level'].default_value = 0.1

    obj.data.materials.append(mat)
    
    # Center the object
    obj.location = (0, 0, 0)

if __name__ == "__main__":
    generate_pinecone()
