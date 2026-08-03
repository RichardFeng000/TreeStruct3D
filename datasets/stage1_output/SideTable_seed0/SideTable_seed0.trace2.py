import bpy
import bmesh
import math

def clear_scene():
    """Clears the default Blender scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_table_top():
    """Creates the square flat top with rounded corners using BMesh beveling."""
    size = 0.4  # 40cm width/depth
    thickness = 0.025 # 2.5cm thickness
    corner_radius = 0.04 # 4cm rounding
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    top = bpy.context.active_object
    top.name = "TableTop"
    
    # Scale to target dimensions
    top.scale[0] = size / 2
    top.scale[1] = size / 2
    top.scale[2] = thickness / 2
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Use BMesh to bevel the vertical corners
    bm = bmesh.new()
    bm.from_mesh(top.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    
    # Find 4 vertical edges (Z-aligned)
    vertical_edges = []
    for edge in bm.edges:
        v1 = edge.verts[0].co
        v2 = edge.verts[1].co
        if abs(v1.x - v2.x) < 0.001 and abs(v1.y - v2.y) < 0.001:
            vertical_edges.append(edge)
    
    # Apply bevel to corners for rounded look
    bmesh.ops.bevel(bm, 
                   geom=vertical_edges, 
                   offset=corner_radius, 
                   segments=12, 
                   affect='EDGES')
    
    bm.to_mesh(top.data)
    bm.free()
    
    return top

def create_leg(name, position):
    """Creates a thin cylindrical leg with a flared circular base."""
    shaft_radius = 0.012 # 1.2cm
    base_bottom_radius = 0.035 # 3.5cm
    base_top_radius = shaft_radius
    base_height = 0.02 # 2cm flare height
    shaft_height = 0.48 # 48cm height
    
    # Create the flared base (Cone)
    bpy.ops.mesh.primitive_cone_add(
        vertices=32, 
        radius1=base_bottom_radius, 
        radius2=base_top_radius, 
        depth=base_height, 
        location=(position[0], position[1], base_height / 2)
    )
    base = bpy.context.active_object
    base.name = f"{name}_Base"
    
    # Create the shaft (Cylinder)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32, 
        radius=shaft_radius, 
        depth=shaft_height, 
        location=(position[0], position[1], base_height + (shaft_height / 2))
    )
    shaft = bpy.context.active_object
    shaft.name = f"{name}_Shaft"
    
    # Join the parts into one object
    bpy.ops.object.select_all(action='DESELECT')
    base.select_set(True)
    shaft.select_set(True)
    bpy.context.view_layer.objects.active = shaft
    bpy.ops.object.join()
    
    return shaft

def main():
    clear_scene()
    
    # 1. Create Table Top
    top = create_table_top()
    
    # 2. Define Leg positions (Two legs, symmetrically placed)
    leg_offset = 0.12 # Distance from center to each leg
    positions = [
        (leg_offset, 0, 0),
        (-leg_offset, 0, 0)
    ]
    
    total_leg_height = 0.5 # 0.48 shaft + 0.02 base
    
    for i, pos in enumerate(positions):
        create_leg(f"Leg_{i+1}", pos)
        
    # Position the top on top of the legs
    top.location.z = total_leg_height + (0.025 / 2)
    
    # Final Polish: Smoothing and Normals
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            # Set all polygons to smooth shading
            for poly in obj.data.polygons:
                poly.use_smooth = True
            
            # Use Weighted Normal modifier for better surface look if available, 
            # otherwise just standard smoothing is applied via use_smooth.
            mod = obj.modifiers.new(name="WeightedNormal", type='WEIGHTED_NORMAL')
            # Set the weighted normal to keep flat surfaces flat and corners smooth
            obj.data.use_auto_smooth = False # Compatible with Blender 5.0 logic where auto-smooth is moved/changed

if __name__ == "__main__":
    main()
