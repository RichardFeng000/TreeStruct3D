import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_valve(name, is_top=True):
    # Create a sphere and deform it into an oval clam shape
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0)
    obj = bpy.context.active_object
    obj.name = name

    # Scale to create the oval valve shape (Width, Length, Height)
    # X: width, Y: length (hinge axis), Z: height
    obj.scale = (0.8, 1.4, 0.6)
    bpy.ops.object.transform_apply(scale=True)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    
    # Remove the bottom half to make it a shell valve (Z is height)
    # Since we want a bowl shape, keep Z > 0 for top and then mirror/rotate for bottom
    verts_to_delete = [v for v in bm.verts if v.co.z < -0.05]
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')

    # Define hinge point as the back of the oval (Y axis)
    # After scaling sphere radius 1 to Y 1.4, back is at ~1.4
    hinge_pos = Vector((0, 1.4, 0))
    
    # Apply organic growth rings: displacement based on distance from hinge
    for v in bm.verts:
        dist = (v.co - hinge_pos).length
        # Create physical ridges using sine wave
        ridge = math.sin(dist * 15.0) * 0.04
        # Add slight organic irregularity
        noise = (random.random() - 0.5) * 0.02
        normal = v.co.normalized()
        v.co += normal * (ridge + noise)

    bm.to_mesh(obj.data)
    bm.free()

    # Give thickness to the shell
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.06
    solid.offset = -1 # Offset inside
    bpy.ops.object.modifier_apply(modifier="Solidify")

    # Move vertices so that the hinge point is at (0,0,0) for easy rotation
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for v in bm.verts:
        v.co -= hinge_pos
    bm.to_mesh(obj.data)
    bm.free()

    return obj

def assign_materials(obj):
    # Material colors
    mat_cream = create_material("OuterCream", (0.9, 0.85, 0.7, 1.0))
    mat_brown = create_material("OuterBrown", (0.4, 0.3, 0.2, 1.0))
    mat_inner = create_material("InnerDark", (0.2, 0.15, 0.1, 1.0))

    obj.data.materials.append(mat_cream)
    obj.data.materials.append(mat_brown)
    obj.data.materials.append(mat_inner)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    
    # We need to determine if a face is "inside" or "outside".
    # After solidify, we can use the normal relative to the original surface.
    # But since we modified it, let's use distance from origin and normal direction.
    # The hinge point was moved to (0,0,0). 
    # For a valve that is roughly centered on Z=0 (after solidify),
    # faces with normals pointing generally in the -Z direction are "outside" for top valve
    # and +Z for bottom valve. However, it's easier to use the BMesh indices from Solidify
    # or just check normal.z relative to object orientation.

    for face in bm.faces:
        center = face.calc_center_median()
        # The shell is concave on one side and convex on other.
        # For top valve, outside normals point mostly -Z (if it's an upside down bowl) 
        # or +Z depending on construction. Let's use the normal relative to vertex center.
        # A simpler heuristic for this specific geometry:
        # The 'inner' face of a solidified mesh usually has the opposite normal of the outer.
        if face.normal.z > 0.1: # Simplified logic based on current construction
            face.material_index = 2 # InnerDark
        else:
            # Outer rings based on distance from hinge (which is now at 0,0,0)
            dist = center.length
            if math.sin(dist * 15.0) > 0:
                face.material_index = 0 # Cream
            else:
                face.material_index = 1 # Brown

    bm.to_mesh(obj.data)
    bm.free()

def main():
    clear_scene()

    # Create top valve
    top_valve = create_valve("TopValve", is_top=True)
    assign_materials(top_valve)

    # Create bottom valve
    bottom_valve = create_valve("BottomValve", is_top=False)
    
    # Flip the bottom valve to be a mirror of the top
    bm_bot = bmesh.new()
    bm_bot.from_mesh(bottom_valve.data)
    for v in bm_bot.verts:
        v.co.z *= -1 # Mirror across XY plane
    bm_bot.to_mesh(bottom_valve.data)
    bm_bot.free()
    
    # Materials for bottom valve (inverted normal logic)
    assign_materials(bottom_valve)
    # Correct the material index for bottom valve since it's flipped
    bm_bot = bmesh.new()
    bm_bot.from_mesh(bottom_valve.data)
    for face in bm_bot.faces:
        if face.normal.z < -0.1: # Now +Z is inside for the bottom valve
            face.material_index = 2
        else:
            dist = face.calc_center_median().length
            face.material_index = 0 if math.sin(dist * 15.0) > 0 else 1
    bm_bot.to_mesh(bottom_valve.data)
    bm_bot.free()

    # Rotation logic: Rotate around X axis (the hinge axis is Y, but in local space
    # after the shift it's at origin). To make them open like a clam, rotate on X.
    top_valve.rotation_euler[0] = math.radians(-25) 
    bottom_valve.rotation_euler[0] = math.radians(25)

    # Move the assembly to center it at world origin
    # The hinge is currently at (0,0,0). Move everything forward.
    offset = Vector((0, -0.7, 0))
    top_valve.location += offset
    bottom_valve.location += offset

if __name__ == "__main__":
    main()
