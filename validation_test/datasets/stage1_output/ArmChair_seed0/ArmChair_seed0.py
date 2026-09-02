import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_upholstered_part(name, size, location, rotation=(0, 0, 0), bevel_width=0.1, subdiv_level=2):
    """Creates a boxy part with beveled edges and subdivision for an upholstered look."""
    # Create cube of size 1 (extents -0.5 to 0.5)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    
    # Scale to target dimensions (since original size is 1x1x1)
    obj.scale = Vector((size[0], size[1], size[2]))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Add Bevel Modifier for rounded corners
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = bevel_width
    bevel.segments = 5
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = math.radians(30)
    
    # Add Subdivision Surface Modifier for softness
    subdiv = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subdiv.levels = subdiv_level
    subdiv.render_levels = subdiv_level
    
    # Set shading to smooth
    bpy.ops.object.shade_smooth()
    
    return obj

def create_armchair():
    clear_scene()
    
    # Dimensions
    sw, sd, sh = 1.0, 1.0, 0.4  # Seat Width, Depth, Height
    bw, bt, bh = sw, 0.3, 1.2   # Backrest Width, Thickness, Height
    aw, ad, ah = 0.25, sd, 0.7  # Armrest Width, Depth, Height (height is total height from ground)
    fw, fd, fh = sw, 1.2, 0.3   # Footrest Width, Depth, Height
    
    # 1. The Seat Cushion
    # Center Z at sh/2 so the bottom is on the floor
    seat = create_upholstered_part(
        "Seat", 
        (sw, sd, sh), 
        (0, 0, sh / 2), 
        bevel_width=0.15
    )
    
    # 2. The Backrest
    # Positioned at the back of the seat (Y = -sd/2). 
    # Center Y = -sd/2 + bt/2. Center Z = sh + bh/2.
    back_rot = math.radians(-10) # Slight recline
    back_loc = (0, -sd / 2 + bt / 2, sh + bh / 2)
    create_upholstered_part(
        "Backrest", 
        (bw, bt, bh), 
        back_loc, 
        rotation=(back_rot, 0, 0), 
        bevel_width=0.15
    )

    # 3. The Armrests (Left and Right)
    # Bottom of armrest starts at the floor or seat base; usually they wrap from ground up.
    # Center X = +/- (sw/2 - aw/2). Center Y = 0. Center Z = ah / 2.
    arm_l_loc = (-sw / 2 + aw / 2, 0, ah / 2)
    create_upholstered_part(
        "Armrest_L", 
        (aw, ad, ah), 
        arm_l_loc, 
        bevel_width=0.15
    )
    
    arm_r_loc = (sw / 2 - aw / 2, 0, ah / 2)
    create_upholstered_part(
        "Armrest_R", 
        (aw, ad, ah), 
        arm_r_loc, 
        bevel_width=0.15
    )
    
    # 4. The Footrest/Ottoman extension
    # Positioned in front of the seat (Y = sd/2).
    # Center Y = sd/2 + fd/2. Center Z = fh / 2.
    foot_loc = (0, sd / 2 + fd / 2, fh / 2)
    create_upholstered_part(
        "Footrest", 
        (fw, fd, fh), 
        foot_loc, 
        bevel_width=0.15
    )

    # Add "puffiness" to the seat top face via BMesh
    bpy.context.view_layer.objects.active = seat
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(seat.data)
    for face in bm.faces:
        # Find the top face (normal pointing up)
        if face.normal.z > 0.9:
            # Slightly inflate the center of the cushion
            center = face.calc_center_median()
            for v in face.verts:
                v.co += Vector((0, 0, 0.08))
    bmesh.update_edit_mesh(seat.data)
    bpy.ops.object.mode_set(mode='OBJECT')

if __name__ == "__main__":
    create_armchair()
