import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for curve in bpy.data.curves:
        bpy.data.curves.remove(curve)
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)

def create_base_plate():
    """Creates the flat rectangular mounting plate."""
    # Dimensions: 0.2 x 0.1 x 0.015
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    plate = bpy.context.active_object
    plate.name = "BasePlate"
    plate.scale = (0.2, 0.1, 0.015)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Bevel for a polished look
    bev = plate.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.005
    bev.segments = 3
    return plate

def create_main_body():
    """Creates the central vertical stem of the faucet."""
    # Base plate is at Z=0, thickness=0.015. Top surface is at 0.0075.
    # Stem height=0.1, Radius=0.03. Center location = (0, 0, 0.0075 + 0.05)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.1, location=(0, 0, 0.0575))
    body = bpy.context.active_object
    body.name = "FaucetBody"
    return body

def create_gooseneck():
    """Creates the tall curved spout using a Bezier curve converted to mesh."""
    curve_data = bpy.data.curves.new('SpoutCurve', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 0.02  # Thickness of the pipe
    curve_data.bevel_resolution = 10
    
    polyline = curve_data.splines.new('BEZIER')
    # Need 4 points for a smooth gooseneck arc
    polyline.bezier_points.add(3) # Total 4 points (starts with 1)
    
    pts = polyline.bezier_points
    
    # Start at top of main body: Z = 0.0075 + 0.05 = 0.1075
    pts[0].co = Vector((0, 0, 0.1075))
    pts[0].handle_left = Vector((0, 0, 0.08))
    pts[0].handle_right = Vector((0, 0, 0.13))
    
    # Rise up to the high point
    pts[1].co = Vector((0, 0, 0.4))
    pts[1].handle_left = Vector((0, 0, 0.35))
    pts[1].handle_right = Vector((0, 0.1, 0.4)) # Start curving forward (Y axis)

    # Apex of the curve
    pts[2].co = Vector((0, 0.2, 0.42))
    pts[2].handle_left = Vector((0, 0.1, 0.45))
    pts[2].handle_right = Vector((0, 0.3, 0.38))
    
    # End of the spout (pointing down)
    pts[3].co = Vector((0, 0.3, 0.25))
    pts[3].handle_left = Vector((0, 0.3, 0.3))
    pts[3].handle_right = Vector((0, 0.3, 0.2))

    spout_obj = bpy.data.objects.new('Spout', curve_data)
    bpy.context.collection.objects.link(spout_obj)
    
    # Crucial: set active and convert to ensure geometry is generated correctly
    bpy.context.view_layer.objects.active = spout_obj
    bpy.ops.object.convert(target='MESH')
    
    return spout_obj

def create_handle():
    """Creates a sleek lever handle attached to the side of the base."""
    # Handle position relative to center
    pivot_center = Vector((0.04, 0, 0.06))
    
    # Create a single mesh for the handle using bmesh for better connectivity
    bm = bmesh.new()
    
    # Pivot cylinder (vertical)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, diameter=0.03, depth=0.04, matrix=bpy.types.Object.matrix_world @ Vector((0,0,0)).to_matrix().to_4x4() if False else Vector((0,0,0)).to_matrix().to_4x4())
    # Actually simpler to just use primitives and join
    bm.free()
    
    bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=0.05, location=pivot_center)
    pivot = bpy.context.active_object
    pivot.name = "HandlePivot"
    
    # Lever arm (horizontal-ish cylinder)
    arm_pos = Vector((0.07, 0, 0.07))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.1, location=arm_pos)
    arm = bpy.context.active_object
    arm.name = "HandleArm"
    arm.rotation_euler[1] = math.radians(90) 
    arm.rotation_euler[0] = math.radians(-20) # Slight ergonomic angle

    # Join pieces into one handle object
    bpy.ops.object.select_all(action='DESELECT')
    pivot.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = pivot
    bpy.ops.object.join()
    
    # Bevel for smoothness
    mod = pivot.modifiers.new(name="Bevel", type='BEVEL')
    mod.width = 0.003
    mod.segments = 2
    return pivot

def create_aerator():
    """Adds the aerator tip at the end of the spout."""
    # Spout ends at (0, 0.3, 0.25)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.022, depth=0.04, location=(0, 0.3, 0.23))
    aerator = bpy.context.active_object
    aerator.name = "Aerator"
    mod = aerator.modifiers.new(name="Bevel", type='BEVEL')
    mod.width = 0.005
    mod.segments = 4
    return aerator

def main():
    clear_scene()
    
    base = create_base_plate()
    body = create_main_body()
    spout = create_gooseneck()
    handle = create_handle()
    aerator = create_aerator()
    
    # Parent everything to base for cohesion
    for obj in [body, spout, handle, aerator]:
        obj.parent = base

if __name__ == "__main__":
    main()
