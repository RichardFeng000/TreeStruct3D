import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.8):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_valve(name, is_top=True):
    # Higher resolution sphere for smoother rings and colors
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=1.0)
    obj = bpy.context.active_object
    obj.name = name

    # Flatten and stretch to a clam oval shape (X: width, Y: length/hinge axis, Z: height)
    # Clams are typically flatter and longer
    obj.scale = (0.7, 1.4, 0.35)
    bpy.ops.object.transform_apply(scale=True)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    
    # Hinge is at the back (positive Y)
    hinge_pos = Vector((0, 1.4, 0))
    
    # Cut in half and create growth ring ridges
    # Keep only one hemisphere
    z_limit = -0.05 if is_top else 0.05
    verts_to_delete = [v for v in bm.verts if (is_top and v.co.z < z_limit) or (not is_top and v.co.z > z_limit)]
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')

    # Concentric growth ring displacement centered at the hinge point
    for v in bm.verts:
        dist = (v.co - hinge_pos).length
        # Create a sequence of ridges and valleys
        ridge = math.sin(dist * 15.0) * 0.03 
        # Add some organic irregularity
        noise = math.cos(v.co.x * 10.0 + v.co.z * 10.0) * 0.01
        normal = v.co.normalized()
        v.co += normal * (ridge + noise)

    bm.to_mesh(obj.data)
    bm.free()

    # Solidify to give the shell thickness
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.03
    solid.offset = -1 if is_top else 1
    bpy.ops.object.modifier_apply(modifier="Solidify")

    # Shift geometry so hinge point (the pivot) is at the local origin
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for v in bm.verts:
        v.co -= hinge_pos
    bm.to_mesh(obj.data)
    bm.free()

    bpy.ops.object.shade_smooth()
    return obj

def assign_materials(obj, is_top=True):
    mat_cream = create_material("OuterCream", (0.95, 0.92, 0.8, 1.0), 0.7)
    mat_brown = create_material("OuterBrown", (0.4, 0.3, 0.2, 1.0), 0.7)
    mat_inner = create_material("InnerDark", (0.15, 0.12, 0.1, 1.0), 0.3)

    obj.data.materials.append(mat_cream)
    obj.data.materials.append(mat_brown)
    obj.data.materials.append(mat_inner)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    
    # The hinge point is now at (0,0,0)
    for face in bm.faces:
        center = face.calc_center_median()
        
        # Determine if it's the interior surface
        # Based on normals relative to the shell center
        if is_top:
            is_interior = face.normal.z > 0.1
        else:
            is_interior = face.normal.z < -0.1

        if is_interior:
            face.material_index = 2 # Dark interior
        else:
            # concentric rings in color based on distance from hinge origin
            dist = center.length
            if math.sin(dist * 15.0) > 0:
                face.material_index = 0 # Cream
            else:
                face.material_index = 1 # Brown

    bm.to_mesh(obj.data)
    bm.free()

def main():
    clear_scene()

    # Create and setup valves
    top_valve = create_valve("TopValve", is_top=True)
    assign_materials(top_valve, is_top=True)

    bottom_valve = create_valve("BottomValve", is_top=False)
    assign_materials(bottom_valve, is_top=False)

    # Rotate to partially open the shell (pivot is at hinge 0,0,0)
    top_valve.rotation_euler[0] = math.radians(-25) 
    bottom_valve.rotation_euler[0] = math.radians(25)

    # Center assembly relative to world origin
    # Offset by half the length since pivot is at one end (Y=1.4)
    offset = Vector((0, -0.7, 0))
    top_valve.location = offset
    bottom_valve.location = offset

if __name__ == "__main__":
    main()
