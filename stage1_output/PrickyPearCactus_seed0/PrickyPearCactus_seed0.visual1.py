import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    """Clear all objects and materials to start fresh."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def create_material(name, color):
    """Create a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def add_oval_pad(bm, center, scale, rotation):
    """Adds a flattened oval pad to the BMesh."""
    # Create sphere and then deform it into an oval
    # We use bmesh ops for local creation at origin, then transform
    start_idx = len(bm.verts)
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=1.0)
    
    # Transform matrix: Scale -> Rotate -> Translate
    rot_mat = Matrix.Rotation(rotation[0], 4, 'X') @ \
              Matrix.Rotation(rotation[1], 4, 'Y') @ \
              Matrix.Rotation(rotation[2], 4, 'Z')
    
    scale_mat = Matrix.Scale(1.0, 4) # Identity since we scale coords manually for precision
    
    for v in bm.verts[start_idx:]:
        # Apply oval scaling (X: width, Y: thickness, Z: height)
        v.co.x *= scale[0]
        v.co.y *= scale[1]
        v.co.z *= scale[2]
        # Rotate and Move to position
        v.co = (rot_mat @ v.co) + center

def add_spine(bm, start_pos, normal, length, radius=0.005):
    """Adds a small cone spine."""
    segments = 4
    # Create base circle for the cone
    perp = Vector((0, 1, 0)) if abs(normal.z) < 0.9 else Vector((0, 0, 1))
    binormal = normal.cross(perp).normalized()
    tangent = normal.cross(binormal).normalized()
    
    base_verts = []
    for i in range(segments):
        angle = (2 * math.pi / segments) * i
        offset = (tangent * math.cos(angle) + binormal * math.sin(angle)) * radius
        base_verts.append(bm.verts.new(start_pos + offset))
    
    tip = bm.verts.new(start_pos + normal * length)
    
    for i in range(segments):
        try:
            bm.faces.new((base_verts[i], base_verts[(i+1)%segments], tip))
        except ValueError:
            pass

def generate_cactus():
    clear_scene()
    
    # Setup materials
    green_mat = create_material("CactusGreen", (0.1, 0.6, 0.1, 1.0))
    white_mat = create_material("SpineWhite", (0.9, 0.9, 0.9, 1.0))
    
    # Create mesh and object for the body
    body_mesh = bpy.data.meshes.new("CactusBody")
    body_obj = bpy.data.objects.new("CactusBody", body_mesh)
    bpy.context.collection.objects.link(body_obj)
    body_obj.data.materials.append(green_mat)
    
    # Create mesh and object for the spines (separate material)
    spine_mesh = bpy.data.meshes.new("CactusSpines")
    spine_obj = bpy.data.objects.new("CactusSpines", spine_mesh)
    bpy.context.collection.objects.link(spine_obj)
    spine_obj.data.materials.append(white_mat)
    
    bm_body = bmesh.new()
    bm_spines = bmesh.new()

    # Growth parameters
    base_scale = (1.0, 0.35, 1.2) # Width, Thickness, Height
    num_segments = 6
    current_pos = Vector((0, 0, 0))
    current_rot = (0, 0, 0)
    
    for i in range(num_segments):
        # Taper scale as it goes up
        taper = (1.0 - (i * 0.12))
        scale = (base_scale[0] * taper, base_scale[1] * taper, base_scale[2] * taper)
        
        # Add randomness to rotation for an organic look
        rot = (
            current_rot[0] + random.uniform(-0.3, 0.3),
            current_rot[1] + random.uniform(-0.3, 0.3),
            current_rot[2] + random.uniform(-0.5, 0.5)
        )
        
        # Add the pad to body BMesh
        add_oval_pad(bm_body, current_pos, scale, rot)
        
        # Calculate next position (top of current pad)
        rot_mat = Matrix.Rotation(rot[0], 4, 'X') @ \
                  Matrix.Rotation(rot[1], 4, 'Y') @ \
                  Matrix.Rotation(rot[2], 4, 'Z')
        up_vector = (rot_mat @ Vector((0, 0, 1))).to_3d()
        # Move to top of the ellipsoid (which has height scale[2])
        current_pos += up_vector * (scale[2] * 0.8) # Overlap slightly
        current_rot = rot

    # Finalize body mesh to access vertices for spines
    bm_body.to_mesh(body_mesh)
    bm_body.free()
    
    # Generate Spines on the surface of the pads
    # We sample vertices from the finalized body mesh
    verts = [v.co for v in body_mesh.vertices]
    normals = [v.normal for v in body_mesh.vertices]
    
    # Densely cover each vertex area with spines/bristles
    for i in range(len(verts)):
        if random.random() > 0.3: # Not every single vert needs a spine cluster
            pos = verts[i]
            norm = normals[i]
            # Each areole has multiple spines (long and short)
            num_spines_per_areole = random.randint(2, 5)
            for _ in range(num_spines_per_areole):
                length = random.uniform(0.02, 0.15) if random.random() > 0.2 else random.uniform(0.2, 0.4)
                # Perturb the normal slightly for each spine in cluster
                spine_norm = (norm + Vector((random.uniform(-0.2, 0.2), 
                                            random.uniform(-0.2, 0.2), 
                                            random.uniform(-0.2, 0.2)))).normalized()
                add_spine(bm_spines, pos, spine_norm, length)

    bm_spines.to_mesh(spine_mesh)
    bm_spines.free()
    
    # Final positioning: Center the whole assembly
    # Move everything so base is at Z=0
    bbox = body_obj.bound_box
    min_z = min([v[2] for v in bbox])
    offset_z = -min_z
    body_obj.location.z = offset_z
    spine_obj.location.z = offset_z

if __name__ == "__main__":
    generate_cactus()
