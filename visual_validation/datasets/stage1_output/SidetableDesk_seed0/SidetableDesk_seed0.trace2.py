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
    """Create a simple diffuse material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_box(name, size, location, rotation=(0, 0, 0), material=None):
    """Helper to create a scaled cube."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    
    # Apply scale for cleaner geometry/materials
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    if material:
        if len(obj.data.materials) == 0:
            obj.data.materials.append(material)
        else:
            obj.data.materials[0] = material
    return obj

def create_leg(name, start_pos, end_pos, material):
    """Creates a slender leg between two points."""
    direction = end_pos - start_pos
    length = direction.length
    midpoint = (start_pos + end_pos) / 2
    
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=16, 
        radius=0.015, 
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
    
    if material:
        leg.data.materials.append(material)
    
    return leg

def main():
    clear_scene()
    
    # --- Parameters ---
    top_size = (0.5, 0.5, 0.03)  # Width, Depth, Thickness
    table_height = 0.5           # Total height to top surface
    splay_angle = 12             # Degrees outward
    shelf_height = 0.12          # Height of shelf from ground
    leg_inset = 0.04             # Inset from table edge for legs
    
    # --- Materials ---
    wood_mat = create_material("WoodTop", (0.35, 0.2, 0.1, 1.0))   # Warm brown
    dark_mat = create_material("DarkFrame", (0.03, 0.03, 0.03, 1.0)) # Near black
    
    # --- Tabletop ---
    top_z = table_height - (top_size[2] / 2)
    top = create_box(
        "TableTop", 
        top_size, 
        location=(0, 0, top_z), 
        material=wood_mat
    )
    
    # Calculate leg points
    offset = (top_size[0] / 2) - leg_inset
    splay_dist = math.tan(math.radians(splay_angle)) * (table_height - top_size[2])
    
    corners = [
        ( offset,  offset),
        (-offset,  offset),
        (-offset, -offset),
        ( offset, -offset)
    ]
    
    legs_objs = []
    for i, (cx, cy) in enumerate(corners):
        # Leg top point: underside of the table
        p_start = Vector((cx, cy, table_height - top_size[2]))
        # Leg bottom point: pushed outward from center
        splay_dir = Vector((cx, cy, 0)).normalized()
        p_end = Vector((cx + splay_dir.x * splay_dist, cy + splay_dir.y * splay_dist, 0))
        
        leg = create_leg(f"Leg_{i}", p_start, p_end, dark_mat)
        legs_objs.append((leg, p_start, p_end))

    # --- Lower Shelf ---
    # Interpolate to find where the shelf intersects the legs
    t = (table_height - top_size[2] - shelf_height) / (table_height - top_size[2])
    
    shelf_points = []
    for leg, p_start, p_end in legs_objs:
        p_shelf = p_start + (p_end - p_start) * t
        shelf_points.append(p_shelf)
    
    # Create shelf geometry using BMesh manually to avoid extrude_face error
    mesh = bpy.data.meshes.new("LowerShelf")
    obj = bpy.data.objects.new("LowerShelf", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    thickness = 0.015
    
    # Create bottom face and top face vertices
    verts_bottom = [bm.verts.new(p - Vector((0, 0, thickness/2))) for p in shelf_points]
    verts_top = [bm.verts.new(p + Vector((0, 0, thickness/2))) for p in shelf_points]
    
    # Create faces
    bm.faces.new(verts_bottom) # Bottom face (will be flipped by default or we can flip later)
    bm.faces.new([verts_top[3], verts_top[2], verts_top[1], verts_top[0]]) # Top face correct winding
    
    # Create side faces
    for i in range(4):
        next_i = (i + 1) % 4
        bm.faces.new([verts_bottom[i], verts_bottom[next_i], verts_top[next_i], verts_top[i]])

    # Correct face normals
    bmesh.ops.recalc_face_normals(bm)
    
    bm.to_mesh(mesh)
    bm.free()
    
    if len(obj.data.materials) == 0:
        obj.data.materials.append(dark_mat)

if __name__ == "__main__":
    main()
