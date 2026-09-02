import bpy
import bmesh
import math
from mathutils import Vector, Matrix

def clear_scene():
    """Removes all default objects from the scene."""
    if "Cube" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
    if "Camera" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Camera"], do_unlink=True)
    if "Light" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Light"], do_unlink=True)
    # Ensure all other mesh/material data is cleared if necessary
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)

def create_metallic_teal_material():
    """Creates a dark teal-green metallic glossy material."""
    mat = bpy.data.materials.new(name="DarkTealMetallic")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")

    # Dark Teal Green: RGB approximately (0.0, 0.2, 0.2)
    # In Blender Principled BSDF: Base Color is usually index 0
    bsdf.inputs['Base Color'].default_value = (0.01, 0.15, 0.15, 1.0)
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.12
    return mat

def create_rosette():
    """Creates the circular wall-mount rosette."""
    # Params
    radius = 0.04
    thickness = 0.01
    segments = 64

    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=radius, segments=segments)
    # Extrude along Y (wall normal)
    # Since create_circle is on XY plane by default, we'll rotate or extrude correctly.
    # Let's use a standard cylinder creation via bmesh for clarity
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=radius, radius2=radius, depth=thickness)
    
    # Bevel the edges of the rosette to make it look finished/cast
    edges = [e for e in bm.edges if e.is_boundary or any(f.normal.dot(Vector((0,1,0))) > 0.9 for f in e.link_faces)]
    # Actually, simpler to just bevel the circular rims
    for edge in bm.edges:
        if abs(edge.verts[0].co.y - thickness/2) < 0.001 or abs(edge.verts[0].co.y + thickness/2) < 0.001:
            edge.select = True
    
    bmesh.ops.bevel(bm, geom=bm.edges, offset=0.003, segments=2, affect='EDGES')
    
    # Finalize mesh
    mesh = bpy.data.meshes.new("RosetteMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("Rosette", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Shift so the back face is at Y=0 (flush with wall)
    obj.location.y = thickness / 2
    return obj

def create_rod(name, angle_deg, length=0.18, radius=0.01):
    """Creates a cylindrical rod extending from origin at a specific angle."""
    segments = 32
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=radius, radius2=radius, depth=length)
    
    # Bevel the end tip of the rod
    end_face = None
    for f in bm.faces:
        if f.normal.dot(Vector((0, 0, 1))) > 0.9: # Assuming cone is created along Z
            end_face = f
            break
    
    if end_face:
        # Select edges of the end face
        for e in end_face.edges:
            e.select = True
        bmesh.ops.bevel(bm, geom=bm.edges, offset=0.002, segments=2, affect='EDGES')

    mesh = bpy.data.meshes.new(name + "Mesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    # The rod is created along Z axis by default in bmesh.ops.create_cone depth direction
    # We want it to extend horizontally (X-Z plane relative to the wall Y).
    # Rotate from Z to X, then rotate around Y for angle.
    obj.rotation_euler[0] = math.radians(90) # Align Z axis with X axis
    obj.rotation_euler[1] = math.radians(angle_deg)
    
    # Offset so it starts from center and extends outwards
    # The cone is centered at origin, so we move it by length/2 along its local transformed axis
    # Local Z was the length. Now that it's rotated:
    # New direction = rotation * Vector((0,0,1))
    rot_mat = obj.matrix_world.to_quaternion().to_matrix()
    direction = rot_mat @ Vector((0, 0, length/2))
    obj.location += direction
    
    return obj

def main():
    clear_scene()
    
    # Material
    teal_mat = create_metallic_teal_material()
    
    # Create components
    rosette = create_rosette()
    
    # Two rods at different angles (e.g., 0 degrees and 45 degrees)
    rod1 = create_rod("Rod_1", 0)
    rod2 = create_rod("Rod_2", 45)
    
    # Assign material
    for obj in [rosette, rod1, rod2]:
        if obj.data.materials:
            obj.data.materials[0] = teal_mat
        else:
            obj.data.materials.append(teal_mat)

    # Join them into a single object for cleanliness
    bpy.ops.object.select_all(action='DESELECT')
    rosette.select_set(True)
    rod1.select_set(True)
    rod2.select_set(True)
    bpy.context.view_layer.objects.active = rosette
    bpy.ops.object.join()
    
    # Rename final object
    rosette.name = "BathroomHardwareFixture"

if __name__ == "__main__":
    main()
