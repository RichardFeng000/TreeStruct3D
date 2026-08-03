import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, metallic=0.0, roughness=0.5, alpha=1.0):
    """Creates a Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Color is expected as (r, g, b, a)
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Metallic'].default_value = metallic
    node_principled.inputs['Roughness'].default_value = roughness
    
    # In Blender 4.0+, Alpha is usually handled via the alpha socket in Principled BSDF or material settings
    if 'Alpha' in node_principled.inputs:
        node_principled.inputs['Alpha'].default_value = alpha
    
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    
    if alpha < 1.0:
        mat.blend_method = 'BLEND'
        
    return mat

def create_glass_panel(name, width, depth, height, pos, rot, glass_mat):
    """Creates a rectangular prism for the glass panels."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=pos, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (width, depth, height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(glass_mat)
    return obj

def create_frame_bar(name, length, thickness, pos, rot, frame_mat):
    """Creates a metallic bar for the corners and edges."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=pos, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (length, thickness, thickness)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(frame_mat)
    return obj

def create_cactus():
    """Procedurally generates a small cactus in a pot."""
    # Materials
    green_mat = create_material("CactusGreen", (0.1, 0.4, 0.1, 1.0), metallic=0.0, roughness=0.8)
    pot_mat = create_material("PotBrown", (0.5, 0.3, 0.2, 1.0), metallic=0.0, roughness=0.9)
    
    # Create Pot
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=0.4, location=(0, 0, 0.2))
    pot = bpy.context.active_object
    pot.name = "CactusPot"
    bm = bmesh.new()
    bm.from_mesh(pot.data)
    for v in bm.verts:
        if v.co.z > 0:
            v.co.x *= 0.8
            v.co.y *= 0.8
    bm.to_mesh(pot.data)
    bm.free()
    pot.data.materials.append(pot_mat)

    # Create Cactus Body
    bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=0.6, location=(0, 0, 0.7))
    body = bpy.context.active_object
    body.name = "CactusBody"
    bm = bmesh.new()
    bm.from_mesh(body.data)
    for v in bm.verts:
        v.co.x += (random.random() - 0.5) * 0.05
        v.co.y += (random.random() - 0.5) * 0.05
    bm.to_mesh(body.data)
    bm.free()
    body.data.materials.append(green_mat)

    # Create Cactus Arms
    arms = [
        (0.2, 0, 0.6, (0, 0, -0.4)), 
        (-0.15, 0.1, 0.8, (0, 0, 0.3))
    ]
    for i, (x, y, z, rot) in enumerate(arms):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.3, location=(x, y, z), rotation=rot)
        arm = bpy.context.active_object
        arm.name = f"CactusArm_{i}"
        arm.data.materials.append(green_mat)

def build_aquarium():
    # Dimensions
    L = 2.0  # Length (X)
    W = 1.0  # Width (Y)
    H = 1.2  # Height (Z)
    T = 0.05 # Glass Thickness
    F = 0.08 # Frame Thickness
    
    # Materials
    glass_mat = create_material("TankGlass", (0.1, 0.2, 0.3, 1.0), metallic=0.1, roughness=0.1, alpha=0.4)
    navy_mat = create_material("FrameNavy", (0.01, 0.05, 0.15, 1.0), metallic=1.0, roughness=0.3)

    # 1. Base Panel
    create_glass_panel("BasePanel", L, W, T, (0, 0, T/2), (0, 0, 0), glass_mat)
    
    # 2. Side Panels
    # Back wall (Y+)
    create_glass_panel("BackWall", L, T, H, (0, W/2, H/2 + T/2), (0, 0, 0), glass_mat)
    # Front wall (Y-)
    create_glass_panel("FrontWall", L, T, H, (0, -W/2, H/2 + T/2), (0, 0, 0), glass_mat)
    # Left wall (X-)
    create_glass_panel("LeftWall", T, W, H, (-L/2, 0, H/2 + T/2), (0, 0, 0), glass_mat)
    # Right wall (X+)
    create_glass_panel("RightWall", T, W, H, (L/2, 0, H/2 + T/2), (0, 0, 0), glass_mat)

    # 3. Frame Trim
    # Vertical corners
    corners = [
        (-L/2, -W/2, H/2), (L/2, -W/2, H/2),
        (-L/2, W/2, H/2), (L/2, W/2, H/2)
    ]
    for i, pos in enumerate(corners):
        # Vertical bars: scale is length on Z axis. 
        # Our create_frame_bar currently scales X as length. Rotate to Z.
        obj = create_frame_bar(f"Corner_{i}", H, F, pos, (0, 0, 0), navy_mat)
        obj.rotation_euler = (0, math.radians(90), 0) # Scale X -> scale Z

    # Horizontal base edges
    # L-edges (X axis)
    create_frame_bar("BaseEdgeL1", L, F, (0, -W/2, 0), (0, 0, 0), navy_mat)
    create_frame_bar("BaseEdgeL2", L, F, (0, W/2, 0), (0, 0, 0), navy_mat)
    # W-edges (Y axis)
    obj1 = create_frame_bar("BaseEdgeW1", W, F, (-L/2, 0, 0), (0, 0, 0), navy_mat)
    obj1.rotation_euler = (0, 0, math.radians(90))
    obj2 = create_frame_bar("BaseEdgeW2", W, F, (L/2, 0, 0), (0, 0, 0), navy_mat)
    obj2.rotation_euler = (0, 0, math.radians(90))

    # Top edges (open top frame)
    # L-edges (X axis)
    create_frame_bar("TopEdgeL1", L, F, (0, -W/2, H), (0, 0, 0), navy_mat)
    create_frame_bar("TopEdgeL2", L, F, (0, W/2, H), (0, 0, 0), navy_mat)
    # W-edges (Y axis)
    obj3 = create_frame_bar("TopEdgeW1", W, F, (-L/2, 0, H), (0, 0, 0), navy_mat)
    obj3.rotation_euler = (0, 0, math.radians(90))
    obj4 = create_frame_bar("TopEdgeW2", W, F, (L/2, 0, H), (0, 0, 0), navy_mat)
    obj4.rotation_euler = (0, 0, math.radians(90))

    # Interior: Cactus plant on the left side
    bpy.ops.object.select_all(action='DESELECT')
    create_cactus()
    for obj in bpy.data.objects:
        if "Cactus" in obj.name:
            obj.location.x -= L/4 
            obj.location.z += T

def main():
    clear_scene()
    build_aquarium()

if __name__ == "__main__":
    main()
