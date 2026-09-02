import bpy
import bmesh
import math

def clear_scene():
    """Clears the default scene objects."""
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.4):
    """Creates a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['Specular IOR Level'].default_value = 0.5
    return mat

def create_step(name, location, size, material):
    """Creates a single cantilevered step."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Create a cube as the base for the step
    bmesh.ops.create_cube(bm, size=1.0)
    
    # Scale geometry directly in bmesh to ensure modifiers work on original scale
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
        
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    obj.data.materials.append(material)
    
    # Bevel for a high-end architectural look
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.005
    bevel.segments = 3
    
    return obj

def create_supporting_wall(name, size, location, material):
    """Creates the architectural wall that supports the cantilevered steps."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    
    for v in bm.verts:
        v.co.x *= size[0] # Thickness
        v.co.y *= size[1] # Length
        v.co.z *= size[2] # Height
        
    bm.to_mesh(mesh)
    bm.free()
    
    obj.location = location
    obj.data.materials.append(material)
    
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.01
    bevel.segments = 2
    
    return obj

def main():
    clear_scene()
    
    # Configuration
    num_steps = 15
    step_width = 1.0      # Total width of step
    step_depth = 0.3      # Tread depth (Y)
    step_thickness = 0.06 # Thickness (Z)
    riser_height = 0.18   # Vertical gap
    
    # Dark Navy Blue Color (RGBA) - Deep, saturated navy
    navy_blue_color = (0.01, 0.03, 0.12, 1.0)
    step_mat = create_material("NavyBlueStep", navy_blue_color)
    
    # Total run calculation to size the wall correctly
    total_run = (num_steps - 1) * step_depth
    wall_thickness = 0.3
    wall_height = num_steps * riser_height + 1.0
    wall_length = total_run + 1.0 # Add some margin at start and end
    
    # Wall positioned so that the steps are embedded on one side
    # We center the wall's Y coordinate around the run of the stairs
    wall_loc = (0, total_run / 2, wall_height / 2)
    wall_size = (wall_thickness, wall_length, wall_height)
    create_supporting_wall("SupportWall", wall_size, wall_loc, step_mat)
    
    # Position the steps so they emerge from one side of the wall.
    # Wall is at X=0 with thickness 0.3 (range -0.15 to 0.15).
    # We want the steps to start slightly inside the wall and project out along +X.
    # Step center should be: (wall_thickness/2) + (step_width/2) - embedded_amount
    embedded_amount = 0.15 # How much of the step is buried in the wall
    x_pos = (wall_thickness / 2) + (step_width / 2) - embedded_amount
    
    for i in range(num_steps):
        # Z: Start from floor, go up
        z_pos = i * riser_height
        # Y: Distribute along the length of the wall
        # Center the whole staircase assembly relative to the world origin if desired, 
        # but here we match the wall's layout.
        y_pos = (i * step_depth) - (total_run / 2) + (total_run/2) # Simple linear progression
        
        # Adjusted y_pos for a cleaner start relative to world origin
        actual_y = i * step_depth
        actual_z = i * riser_height
        
        # Shift the whole assembly so it's centered around Y=0
        center_offset_y = - (total_run / 2)
        loc = (x_pos, actual_y + center_offset_y, actual_z)
        size = (step_width, step_depth, step_thickness)
        
        create_step(f"Step_{i}", loc, size, step_mat)

    # Reposition wall to align with the centered steps
    # The logic above centers steps around Y=0. Wall must follow.
    wall = bpy.data.objects["SupportWall"]
    wall.location = (0, 0, wall_height / 2)

if __name__ == "__main__":
    main()
