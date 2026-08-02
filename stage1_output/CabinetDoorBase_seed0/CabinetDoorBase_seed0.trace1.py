import bpy
import bmesh
import math

def setup_scene():
    """Clears the default Blender scene."""
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_cabinet_door():
    """
    Creates a tall, narrow cabinet door panel with vertical edge detailing.
    Dimensions: Height=2.1m, Width=0.4m, Thickness=0.02m
    """
    # Parameters
    width = 0.4
    height = 2.1
    depth = 0.02
    border_width = 0.03  # The width of the outer frame detail
    inset_depth = 0.005   # How far the center panel is recessed
    groove_width = 0.004  # Width of vertical grooves
    groove_depth = 0.002  # Depth of vertical grooves

    # Create BMesh
    bm = bmesh.new()

    # Create the main slab (the door) as a box centered at origin
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale to dimensions manually in BMESH
    for v in bm.verts:
        v.co.x *= (width / 2)
        v.co.y *= (depth / 2)
        v.co.z *= (height / 2)

    # Identify the front face (+Y direction)
    front_face = None
    for f in bm.faces:
        if f.normal.y > 0.9:
            front_face = f
            break

    if front_face:
        # Use inset_region for the center panel (replaces invalid inset_individual)
        # offset is the width of the border created around the face
        res = bmesh.ops.inset_region(bm, faces=[front_face], thickness=0, offset=border_width, use_boundary=True)
        inner_face = res['faces'][0]
        
        # Extrude inner face backwards (into the door) to create depth
        bmesh.ops.translate(bm, verts=inner_face.verts, vec=(0, -inset_depth, 0))

        # Create vertical edge detailing (grooves) on the sides of the recessed panel
        # Identify edges of the inner face that are vertical
        inner_edges = [e for e in inner_face.edges]
        vertical_edges = [e for e in inner_edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1.0]

        for edge in vertical_edges:
            # Bevel the edge to create a small rectangular strip for the groove
            # Offset here is total width of bevel
            bmesh.ops.bevel(bm, geom=[edge], offset=groove_width/2, segments=1, affect='EDGES')
            
            # Find the newly created faces from the bevel to extrude them as grooves
            # We search for faces that share the original edge's vertices and are thin
            for f in bm.faces:
                if any(v in edge.verts for v in f.verts) and f != inner_face:
                    # Ensure we only target the small bevel strip face
                    # Checking if it is narrow (small distance between vertices in X direction)
                    coords = [v.co for v in f.verts]
                    dx = abs(coords[0].x - coords[1].x) if len(coords) > 1 else 1.0
                    if dx < border_width:
                        bmesh.ops.translate(bm, verts=f.verts, vec=(0, -groove_depth, 0))

    # Final geometry cleanup and creation
    mesh = bpy.data.meshes.new("CabinetDoorPanel")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("CabinetDoorPanel", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Apply a subtle Bevel Modifier to the whole object for realism (rounding corners)
    bevel_mod = obj.modifiers.new(name="EdgeRounding", type='BEVEL')
    bevel_mod.width = 0.002
    bevel_mod.segments = 3
    bevel_mod.limit_method = 'ANGLE'
    bevel_mod.angle_limit = 0.785398 # 45 degrees

    # Center the object's origin
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

if __name__ == "__main__":
    setup_scene()
    create_cabinet_door()
