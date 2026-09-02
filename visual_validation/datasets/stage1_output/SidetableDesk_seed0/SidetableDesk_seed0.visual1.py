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
    """Create a simple diffuse material using Principled BSDF."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Base Color is input index 0 in the Principled BSDF node
        bsdf.inputs[0].default_value = color
    return mat

def create_box(name, size, location, material):
    """Helper to create a scaled cube with a specific material."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    # Apply scale for clean geometry and materials
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    return obj

def create_leg(name, start_pos, end_pos, radius, material):
    """Creates a slender cylinder leg between two points."""
    direction = end_pos - start_pos
    length = direction.length
    midpoint = (start_pos + end_pos) / 2
    
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=16, 
        radius=radius, 
        depth=length, 
        location=midpoint
    )
    leg = bpy.context.active_object
    leg.name = name
    
    # Align cylinder's Z axis to the direction vector
    up = Vector((0, 0, 1))
    rot_quat = up.rotation_difference(direction.normalized())
    leg.rotation_mode = 'QUATERNION'
    leg.rotation_quaternion = rot_quat
    
    leg.data.materials.append(material)
    return leg

def main():
    clear_scene()
    
    # --- Parameters ---
    top_dims = (0.5, 0.5, 0.03)  # Width, Depth, Thickness
    table_height = 0.5           # Height to top surface
    splay_angle = 12             # Degrees outward flare
    shelf_z = 0.12               # Absolute height of shelf from ground
    leg_radius = 0.018           # Slender leg thickness
    leg_inset = 0.05             # Inset from table edge for legs
    
    # --- Materials (Two-Tone) ---
    # Saturated wood brown and very dark charcoal to ensure contrast in renders
    wood_mat = create_material("WoodTop", (0.4, 0.2, 0.1, 1.0))
    dark_mat = create_material("DarkFrame", (0.05, 0.05, 0.05, 1.0))
    
    # --- Tabletop ---
    top_center_z = table_height - (top_dims[2] / 2)
    create_box(
        "TableTop", 
        top_dims, 
        location=(0, 0, top_center_z), 
        material=wood_mat
    )
    
    # Calculate leg endpoints
    offset = (top_dims[0] / 2) - leg_inset
    splay_dist = math.tan(math.radians(splay_angle)) * (table_height - top_dims[2])
    
    corners = [
        ( offset,  offset),
        (-offset,  offset),
        (-offset, -offset),
        ( offset, -offset)
    ]
    
    leg_endpoints = [] # Store for shelf intersection
    for i, (cx, cy) in enumerate(corners):
        # Leg top point: underside of the tabletop
        p_start = Vector((cx, cy, table_height - top_dims[2]))
        # Leg bottom point: pushed outward based on splay angle
        splay_dir = Vector((cx, cy, 0)).normalized()
        p_end = Vector((cx + splay_dir.x * splay_dist, cy + splay_dir.y * splay_dist, 0))
        
        create_leg(f"Leg_{i}", p_start, p_end, leg_radius, dark_mat)
        leg_endpoints.append((p_start, p_end))

    # --- Lower Shelf ---
    # Calculate points where the shelf intersects the angled legs at height shelf_z
    shelf_pts = []
    for p_start, p_end in leg_endpoints:
        # Parametric t along the leg line segment: z(t) = start.z + t * (end.z - start.z)
        t = (shelf_z - p_start.z) / (p_end.z - p_start.z)
        p_interp = p_start + t * (p_end - p_start)
        shelf_pts.append(p_interp)
    
    # Create shelf geometry using BMesh
    mesh = bpy.data.meshes.new("LowerShelf")
    obj = bpy.data.objects.new("LowerShelf", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    thickness = 0.015
    # Create top and bottom vertices for the shelf slab
    v_top = [bm.verts.new(p + Vector((0, 0, thickness/2))) for p in shelf_pts]
    v_bot = [bm.verts.new(p - Vector((0, 0, thickness/2))) for p in shelf_pts]
    
    # Create faces (Top and Bottom)
    bm.faces.new(v_top) 
    bm.faces.new([v_bot[3], v_bot[2], v_bot[1], v_bot[0]]) # Correct winding for bottom face
    
    # Create side faces connecting top and bottom slabs
    for i in range(4):
        next_i = (i + 1) % 4
        bm.faces.new([v_top[i], v_top[next_i], v_bot[next_i], v_bot[i]])

    bmesh.ops.recalc_face_normals(bm)
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(dark_mat)

if __name__ == "__main__":
    main()
