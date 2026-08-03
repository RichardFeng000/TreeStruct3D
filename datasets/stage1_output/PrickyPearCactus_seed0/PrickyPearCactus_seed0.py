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
    start_idx = len(bm.verts)
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=1.0)
    
    # Transform matrix: Rotation then Translation
    rot_mat = Matrix.Rotation(rotation[0], 4, 'X') @ \
              Matrix.Rotation(rotation[1], 4, 'Y') @ \
              Matrix.Rotation(rotation[2], 4, 'Z')
    
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
    
    green_mat = create_material("CactusGreen", (0.2, 0.7, 0.1, 1.0))
    white_mat = create_material("SpineWhite", (0.95, 0.95, 0.95, 1.0))
    
    body_mesh = bpy.data.meshes.new("CactusBody")
    body_obj = bpy.data.objects.new("CactusBody", body_mesh)
    bpy.context.collection.objects.link(body_obj)
    body_obj.data.materials.append(green_mat)
    
    spine_mesh = bpy.data.meshes.new("CactusSpines")
    spine_obj = bpy.data.objects.new("CactusSpines", spine_mesh)
    bpy.context.collection.objects.link(spine_obj)
    spine_obj.data.materials.append(white_mat)
    
    bm_body = bmesh.new()
    bm_spines = bmesh.new()

    # Pad dimensions: Width=1.0, Thickness=0.25 (Flat), Height=1.3
    base_scale = (1.0, 0.25, 1.3)
    num_segments = 7
    current_pos = Vector((0, 0, 0))
    
    # To keep track of the overall orientation to prevent it from just going straight up
    cumulative_rot = Vector((0, 0, 0))
    
    for i in range(num_segments):
        taper = (1.0 - (i * 0.1))
        scale = (base_scale[0] * taper, base_scale[1] * taper, base_scale[2] * taper)
        
        # Add rotation variety so pads branch out organically
        rot_x = cumulative_rot.x + random.uniform(-0.4, 0.4)
        rot_y = cumulative_rot.y + random.uniform(-0.4, 0.4)
        rot_z = cumulative_rot.z + random.uniform(-1.2, 1.2)
        cumulative_rot = Vector((rot_x, rot_y, rot_z))
        
        add_oval_pad(bm_body, current_pos, scale, (rot_x, rot_y, rot_z))
        
        # Determine the top of the pad in local space and transform it to world space
        rot_mat = Matrix.Rotation(rot_x, 4, 'X') @ \
                  Matrix.Rotation(rot_y, 4, 'Y') @ \
                  Matrix.Rotation(rot_z, 4, 'Z')
        # The pad's "top" is along the Z axis (local)
        up_vector = (rot_mat @ Vector((0, 0, 1))).to_3d()
        
        # Move current_pos to the top of this pad for the next segment to grow from.
        # We multiply by scale[2] (height) and use a factor < 1.0 for overlap/fusion.
        current_pos += up_vector * (scale[2] * 0.65)

    bm_body.to_mesh(body_mesh)
    bm_body.free()
    
    # Generate Spines on the surface of the pads
    verts = [v.co for v in body_mesh.vertices]
    normals = [v.normal for v in body_mesh.vertices]
    
    for i in range(len(verts)):
        if random.random() > 0.4: # Distribute spines across surface
            pos = verts[i]
            norm = normals[i]
            # Create clusters (areoles)
            num_spines_per_cluster = random.randint(2, 4)
            for _ in range(num_spines_per_cluster):
                length = random.uniform(0.05, 0.18) if random.random() > 0.3 else random.uniform(0.2, 0.3)
                # Slightly jitter the direction
                jittered_norm = (norm + Vector((random.uniform(-0.3, 0.3), 
                                               random.uniform(-0.3, 0.3), 
                                               random.uniform(-0.3, 0.3)))).normalized()
                add_spine(bm_spines, pos, jittered_norm, length)

    bm_spines.to_mesh(spine_mesh)
    bm_spines.free()
    
    # Center the assembly at Z=0
    bbox = body_obj.bound_box
    min_z = min([v[2] for v in bbox])
    offset_z = -min_z
    body_obj.location.z = offset_z
    spine_obj.location.z = offset_z

if __name__ == "__main__":
    generate_cactus()
