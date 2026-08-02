import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_basin():
    """Creates a rectangular kitchen sink basin with rounded interior edges and a flat rim."""
    # Dimensions
    width = 0.6
    depth = 0.4
    height = 0.25  # Deeper as requested
    wall_thickness = 0.03
    inner_rounding = 0.04

    # Outer Shell
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, height / 2))
    basin = bpy.context.active_object
    basin.name = "KitchenSinkBasin"
    basin.scale = (width, depth, height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Inner Cavity for Boolean subtraction
    inner_w = width - (wall_thickness * 2)
    inner_d = depth - (wall_thickness * 2)
    inner_h = height + 0.1 # Ensure it cuts through the top completely
    
    # Position inner box so its bottom is at wall_thickness from basin bottom
    # Bottom of outer is 0, so center should be (height/2) + (wall_thickness/2)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, height / 2 + wall_thickness / 2))
    inner_box = bpy.context.active_object
    inner_box.name = "InnerCavity"
    inner_box.scale = (inner_w, inner_d, inner_h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Rounded interior corners for the cutout
    bm = bmesh.new()
    bm.from_mesh(inner_box.data)
    edges_to_bevel = []
    for edge in bm.edges:
        v1, v2 = edge.verts
        if abs(v1.co.x - v2.co.x) < 0.001 and abs(v1.co.y - v2.co.y) < 0.001:
            edges_to_bevel.append(edge)
    bmesh.ops.bevel(bm, geom=edges_to_bevel, offset=inner_rounding, segments=8, affect='EDGES')
    bm.to_mesh(inner_box.data)
    bm.free()

    # Boolean operation to create the basin cavity
    mod = basin.modifiers.new(name="Cavity", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = inner_box
    bpy.context.view_layer.objects.active = basin
    bpy.ops.object.modifier_apply(modifier="Cavity")
    bpy.data.objects.remove(inner_box, do_unlink=True)

    # Subtle bevel on the top outer rim for realism
    mod_bev = basin.modifiers.new(name="RimBevel", type='BEVEL')
    mod_bev.width = 0.01
    mod_bev.segments = 3
    bpy.ops.object.modifier_apply(modifier="RimBevel")

    return basin

def create_faucet(sink_height):
    """Creates a curved gooseneck faucet with a base and handle."""
    # Mount position on the back rim (Y is positive depth)
    # Sink center is 0, dimensions are width=0.6, depth=0.4, height=sink_height
    base_pos = Vector((0, 0.17, sink_height))

    # 1. Base Cylinder - Sitting exactly on the rim (Z = sink_height)
    # Height is 0.05, center should be at sink_height + 0.025
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.025, depth=0.05, location=base_pos + Vector((0, 0, 0.025)))
    faucet_base = bpy.context.active_object
    faucet_base.name = "FaucetBase"

    # 2. Gooseneck Pipe (Curve)
    curve_data = bpy.data.curves.new('GooseneckPath', type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 0.015
    curve_data.bevel_resolution = 4

    polyline = curve_data.splines.new('BEZIER')
    # Define points for a smooth arch: Start -> Top -> Outward Tip
    points = [
        (0, 0, 0),           # Base of pipe (relative to base_pos)
        (0, -0.05, 0.2),     # Peak height
        (0, -0.18, 0.12)     # Spout end
    ]
    
    polyline.bezier_points.add(len(points) - 1)
    for i, coord in enumerate(points):
        p = polyline.bezier_points[i]
        p.co = Vector(coord)
        if i == 0: # Start vertical
            p.handle_right = p.co + Vector((0, 0, 0.1))
        elif i == 1: # Peak of arc
            p.handle_left = p.co + Vector((0, 0, 0.1))
            p.handle_right = p.co + Vector((0, -0.05, 0))
        else: # End point
            p.handle_left = p.co + Vector((0, -0.05, 0))

    faucet_pipe = bpy.data.objects.new('FaucetPipe', curve_data)
    bpy.context.collection.objects.link(faucet_pipe)
    faucet_pipe.location = base_pos
    
    # Convert pipe to mesh for consistency
    bpy.context.view_layer.objects.active = faucet_pipe
    bpy.ops.object.convert(target='MESH')

    # 3. Handle - A visible lever at the base
    handle_radius = 0.012
    handle_length = 0.06
    # Position handle to one side of the base cylinder
    handle_pos = base_pos + Vector((0.035, 0, 0.025))
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=handle_radius, depth=handle_length, location=handle_pos)
    handle = bpy.context.active_object
    handle.name = "FaucetHandle"
    # Rotate handle to point outward slightly
    handle.rotation_euler[1] = math.radians(45) 

    # Small decorative grip on the handle end
    grip_pos = handle_pos + Vector((0, 0, handle_length/2))
    bpy.ops.mesh.primitive_cube_add(size=0.02, location=grip_pos)
    grip = bpy.context.active_object
    grip.name = "HandleGrip"
    grip.scale = (1, 1, 0.5)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    return [faucet_base, faucet_pipe, handle, grip]

def main():
    clear_scene()
    
    # Dimensions needed for placement
    sink_h = 0.25
    
    basin = create_basin()
    faucet_parts = create_faucet(sink_h)
    
    for part in faucet_parts:
        part.parent = basin

if __name__ == "__main__":
    main()
