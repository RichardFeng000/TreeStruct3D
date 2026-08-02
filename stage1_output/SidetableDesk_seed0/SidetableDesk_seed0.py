import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clear all objects from the current scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Create a diffuse material using Principled BSDF with explicit Base Color input."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Using named input for maximum compatibility across Blender versions
        bsdf.inputs['Base Color'].default_value = color
    return mat

def main():
    clear_scene()
    
    # --- Parameters ---
    top_w, top_d, top_h = 0.5, 0.5, 0.04  # Tabletop dimensions
    table_height = 0.55                 # Total height to the top surface
    leg_radius = 0.018                  # Slender leg thickness
    splay_angle = 12                    # Outward flare angle in degrees
    shelf_z = 0.15                     # Height of the lower shelf from ground
    leg_inset = 0.06                    # Distance legs are inset from table edges
    
    # --- Materials (Two-Tone) ---
    # Distinct wood brown and almost-black charcoal to ensure contrast
    wood_mat = create_material("WoodTop", (0.3, 0.15, 0.08, 1.0))
    dark_mat = create_material("DarkFrame", (0.02, 0.02, 0.02, 1.0))
    
    # --- Tabletop ---
    # Position the tabletop so its top surface is at table_height
    top_z = table_height - (top_h / 2)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, top_z))
    top_obj = bpy.context.active_object
    top_obj.name = "TableTop"
    top_obj.scale = (top_w, top_d, top_h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    top_obj.data.materials.append(wood_mat)
    
    # --- Legs ---
    # Calculate leg positions and splay
    half_w = top_w / 2
    offset = half_w - leg_inset
    splay_dist = math.tan(math.radians(splay_angle)) * (table_height - top_h)
    
    corners = [
        ( offset,  offset),
        (-offset,  offset),
        (-offset, -offset),
        ( offset, -offset)
    ]
    
    leg_starts = [] 
    leg_ends = []
    for i, (cx, cy) in enumerate(corners):
        # Start at the underside of the tabletop
        p_start = Vector((cx, cy, table_height - top_h))
        # Splay outwards based on corner direction
        splay_dir = Vector((cx, cy, 0)).normalized()
        p_end = Vector((cx + splay_dir.x * splay_dist, cy + splay_dir.y * splay_dist, 0))
        
        leg_starts.append(p_start)
        leg_ends.append(p_end)
        
        # Create the cylinder leg
        direction = p_end - p_start
        length = direction.length
        midpoint = (p_start + p_end) / 2
        
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=16, radius=leg_radius, depth=length, location=midpoint
        )
        leg = bpy.context.active_object
        leg.name = f"Leg_{i}"
        
        # Align Z-axis of cylinder to the leg's direction vector
        up = Vector((0, 0, 1))
        rot_quat = up.rotation_difference(direction.normalized())
        leg.rotation_mode = 'QUATERNION'
        leg.rotation_quaternion = rot_quat
        leg.data.materials.append(dark_mat)

    # --- Lower Shelf ---
    # Intersect legs at height shelf_z to find corners of the slab
    shelf_pts = []
    for start, end in zip(leg_starts, leg_ends):
        t = (shelf_z - start.z) / (end.z - start.z)
        p_interp = start + t * (end - start)
        shelf_pts.append(p_interp)
    
    # Use BMesh to create the shelf slab geometry
    mesh = bpy.data.meshes.new("LowerShelf")
    obj = bpy.data.objects.new("LowerShelf", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    thickness = 0.02
    # Top and bottom vertices for the shelf
    v_top = [bm.verts.new(p + Vector((0, 0, thickness/2))) for p in shelf_pts]
    v_bot = [bm.verts.new(p - Vector((0, 0, thickness/2))) for p in shelf_pts]
    
    # Top and Bottom faces
    bm.faces.new(v_top) 
    bm.faces.new([v_bot[3], v_bot[2], v_bot[1], v_bot[0]]) # Clockwise winding for bottom face
    
    # Side walls connecting top and bottom
    for i in range(4):
        next_i = (i + 1) % 4
        bm.faces.new([v_top[i], v_top[next_i], v_bot[next_i], v_bot[i]])

    bmesh.ops.recalc_face_normals(bm)
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(dark_mat)

if __name__ == "__main__":
    main()
