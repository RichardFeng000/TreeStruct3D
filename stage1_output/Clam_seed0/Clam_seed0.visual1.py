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
        bsdf.inputs['Roughness'].default_value = 0.8
    return mat

def create_valve(name, is_top=True):
    # Start with a UV sphere for basic volume
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0)
    obj = bpy.context.active_object
    obj.name = name

    # Scale to an oval clam shape (X: width, Y: length/hinge axis, Z: height)
    obj.scale = (0.8, 1.3, 0.5)
    bpy.ops.object.transform_apply(scale=True)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    
    # Cut the sphere in half to make a valve
    # We keep the 'top' part of the sphere
    verts_to_delete = [v for v in bm.verts if v.co.z < -0.1]
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')

    # Hinge point is at the back (positive Y)
    hinge_pos = Vector((0, 1.3, 0))
    
    # Create concentric growth ring displacement
    for v in bm.verts:
        dist = (v.co - hinge_pos).length
        # Physical ridges
        ridge = math.sin(dist * 12.0) * 0.05
        # Small noise for organic feel
        noise = (random.random() - 0.5) * 0.03
        normal = v.co.normalized()
        v.co += normal * (ridge + noise)

    bm.to_mesh(obj.data)
    bm.free()

    # Solidify for wall thickness
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.05
    solid.offset = -1 
    bpy.ops.object.modifier_apply(modifier="Solidify")

    # Shift geometry so hinge is exactly at (0,0,0) for rotation
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for v in bm.verts:
        v.co -= hinge_pos
    bm.to_mesh(obj.data)
    bm.free()

    # Smooth shading for organic look
    bpy.ops.object.shade_smooth()

    return obj

def assign_materials(obj, is_top=True):
    mat_cream = create_material("OuterCream", (0.95, 0.9, 0.75, 1.0))
    mat_brown = create_material("OuterBrown", (0.35, 0.25, 0.15, 1.0))
    mat_inner = create_material("InnerDark", (0.1, 0.08, 0.06, 1.0))

    obj.data.materials.append(mat_cream)
    obj.data.materials.append(mat_brown)
    obj.data.materials.append(mat_inner)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    
    # Determine interior vs exterior based on normal direction relative to Z
    for face in bm.faces:
        center = face.calc_center_median()
        # After solidify and the way we sliced, normals pointing 'up' (relative to local) are inner for top valve
        if is_top:
            is_interior = face.normal.z > 0.2
        else:
            is_interior = face.normal.z < -0.2

        if is_interior:
            face.material_index = 2 # Dark interior
        else:
            # Use distance from hinge (origin) to create concentric rings in color
            dist = center.length
            if math.sin(dist * 12.0) > 0:
                face.material_index = 0 # Cream
            else:
                face.material_index = 1 # Brown

    bm.to_mesh(obj.data)
    bm.free()

def main():
    clear_scene()

    # Create Top Valve
    top_valve = create_valve("TopValve", is_top=True)
    assign_materials(top_valve, is_top=True)

    # Create Bottom Valve
    bottom_valve = create_valve("BottomValve", is_top=False)
    
    # Mirror the bottom valve across XY plane
    bm_bot = bmesh.new()
    bm_bot.from_mesh(bottom_valve.data)
    for v in bm_bot.verts:
        v.co.z *= -1
    bm_bot.to_mesh(bottom_valve.data)
    bm_bot.free()
    
    assign_materials(bottom_valve, is_top=False)

    # Rotate to partially open the shell
    # Rotation on X axis because the hinge point (0,0,0) is the pivot
    top_valve.rotation_euler[0] = math.radians(-30) 
    bottom_valve.rotation_euler[0] = math.radians(30)

    # Center the whole assembly at origin
    offset = Vector((0, -0.65, 0))
    top_valve.location = offset
    bottom_valve.location = offset

if __name__ == "__main__":
    main()
