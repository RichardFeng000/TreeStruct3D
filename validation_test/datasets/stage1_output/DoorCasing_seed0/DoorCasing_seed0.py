import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene of all objects."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_white_material():
    """Creates a simple clean white material."""
    mat = bpy.data.materials.new(name="WhiteCasingMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.98, 0.98, 0.98, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.4
    return mat

def create_door_casing():
    # --- Parameters ---
    door_w = 0.9      # Width of the opening (~36 inches)
    door_h = 2.1      # Height of the opening (~84 inches)
    jamb_depth = 0.12 # Thickness of the wall/frame depth
    trim_width = 0.07 # Width of the decorative casing on the wall
    trim_thickness = 0.015 # How much the trim sticks out from the wall

    bm = bmesh.new()

    def add_box(x, y, z, dx, dy, dz):
        """Helper to create a box centered at (x+dx/2, y+dy/2, z+dz/2)."""
        # Create 8 vertices
        v0 = bm.verts.new(Vector((x, y, z)))
        v1 = bm.verts.new(Vector((x + dx, y, z)))
        v2 = bm.verts.new(Vector((x + dx, y + dy, z)))
        v3 = bm.verts.new(Vector((x, y + dy, z)))
        v4 = bm.verts.new(Vector((x, y, z + dz)))
        v5 = bm.verts.new(Vector((x + dx, y, z + dz)))
        v6 = bm.verts.new(Vector((x + dx, y + dy, z + dz)))
        v7 = bm.verts.new(Vector((x, y + dy, z + dz)))

        # Create faces
        bm.faces.new((v0, v1, v2, v3)) # bottom
        bm.faces.new((v4, v5, v6, v7)) # top
        bm.faces.new((v0, v1, v5, v4)) # front
        bm.faces.new((v2, v3, v7, v6)) # back
        bm.faces.new((v0, v3, v7, v4)) # left
        bm.faces.new((v1, v2, v6, v5)) # right

    # --- 1. Jambs (The part that goes inside the wall) ---
    # Left Jamb
    add_box(-door_w/2 - jamb_depth, -jamb_depth/2, 0, jamb_depth, jamb_depth, door_h)
    # Right Jamb
    add_box(door_w/2, -jamb_depth/2, 0, jamb_depth, jamb_depth, door_h)
    # Top Jamb (Header)
    add_box(-door_w/2 - jamb_depth, -jamb_depth/2, door_h, 
            door_w + 2*jamb_depth, jamb_depth, jamb_depth * 0.8)

    # --- 2. Decorative Casing (The part on the wall surface) ---
    # We'll use slabs and then apply a bevel modifier for architectural detail.
    # The casing is placed at Y=0, projecting towards Y+
    
    # Left side trim
    add_box(-door_w/2 - trim_width, 0, 0, trim_width, trim_thickness, door_h)
    # Right side trim
    add_box(door_w/2, 0, 0, trim_width, trim_thickness, door_h)
    # Top trim (overlaps the sides)
    add_box(-door_w/2 - trim_width, 0, door_h, 
            door_w + 2*trim_width, trim_thickness, trim_width)

    # Create Mesh and Object
    mesh = bpy.data.meshes.new("DoorCasingMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("DoorCasing", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def finalize_object(obj):
    # Set as active
    bpy.context.view_layer.objects.active = obj
    
    # Add a Bevel Modifier to make the edges look professional/architectural
    bev = obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.005
    bev.segments = 3
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(30)

    # Assign the white material
    mat = create_white_material()
    obj.data.materials.append(mat)

if __name__ == "__main__":
    clear_scene()
    casing_obj = create_door_casing()
    finalize_object(casing_obj)
