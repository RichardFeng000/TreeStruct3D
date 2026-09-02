import bpy
import bmesh
import math

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_navy_blue_material():
    """Creates a dark navy blue material with ceramic glaze quality."""
    mat = bpy.data.materials.new(name="NavyBluePlate")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Dark Navy Blue color (R, G, B, A)
        bsdf.inputs['Base Color'].default_value = (0.01, 0.02, 0.08, 1.0)
        # Ceramic glaze look: low roughness for shine
        bsdf.inputs['Roughness'].default_value = 0.1
        # Specular IOR Level is used in Blender 4.0+ to control specular intensity
        if 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.5
    return mat

def create_plate():
    """Constructs the dinner plate geometry using BMesh."""
    # Parametric dimensions (in meters)
    outer_radius = 0.15       # 30cm diameter
    base_thickness = 0.008     # Thickness of the main slab
    rim_width = 0.02          # Width of the raised rim border
    rim_height = 0.015        # Height above the well floor
    foot_ring_inner = 0.06     # Inner radius of foot ring
    foot_ring_outer = 0.08     # Outer radius of foot ring
    foot_depth = 0.004         # Extension below base

    bm = bmesh.new()

    # 1. Create the bottom disk (Z=0)
    bmesh.ops.create_circle(bm, radius=outer_radius, segments=64)
    # Fill to create a face
    face_res = bmesh.ops.contextual_create(bm, geom=bm.verts[:])
    bottom_face = face_res['faces'][0]

    # 2. Extrude base thickness (Z=0 to Z=base_thickness)
    extrude_res = bmesh.ops.extrude_face_region(bm, geom=[bottom_face])
    verts_extruded = [v for v in extrude_res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, base_thickness), verts=verts_extruded)

    # Find the new top face (the disk at Z=base_thickness)
    top_face = None
    for f in bm.faces:
        if abs(f.calc_center_median().z - base_thickness) < 0.001:
            top_face = f
            break

    # 3. Inset the top face to separate the well from the rim
    inset_res = bmesh.ops.inset_region(bm, faces=[top_face], thickness=rim_width)
    well_face = inset_res['faces'][0]
    
    # Identify the ring of faces created by the inset (the rim base)
    rim_base_faces = [f for f in bm.faces if f != well_face and abs(f.calc_center_median().z - base_thickness) < 0.001]

    # 4. Extrude the rim faces upward to create the raised border
    res_rim = bmesh.ops.extrude_face_region(bm, geom=rim_base_faces)
    rim_verts = [v for v in res_rim['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, rim_height), verts=rim_verts)

    # 5. Create the ring base (foot) on the underside
    # We go back to the bottom face at Z=0
    bottom_face = None
    for f in bm.faces:
        if abs(f.calc_center_median().z) < 0.001:
            bottom_face = f
            break

    # To create a ring, we inset twice to isolate an annular strip
    # First inset defines the outer edge of the foot ring
    inset_outer_res = bmesh.ops.inset_region(bm, faces=[bottom_face], thickness=outer_radius - foot_ring_outer)
    foot_disk_outer = inset_outer_res['faces'][0]

    # Second inset defines the inner edge of the foot ring
    inset_inner_res = bmesh.ops.inset_region(bm, faces=[foot_disk_outer], thickness=foot_ring_outer - foot_ring_inner)
    foot_disk_inner = inset_inner_res['faces'][0]

    # The region between the inner and outer insets are the foot ring's base faces
    foot_ring_faces = [f for f in bm.faces if f != foot_disk_inner and abs(f.calc_center_median().z) < 0.001]

    # Extrude these narrow annular faces downwards into negative Z
    res_foot = bmesh.ops.extrude_face_region(bm, geom=foot_ring_faces)
    foot_verts = [v for v in res_foot['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, -foot_depth), verts=foot_verts)

    # Convert BMesh to Mesh and Object
    mesh = bpy.data.meshes.new("DinnerPlateMesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("DinnerPlate", mesh)
    bpy.context.collection.objects.link(obj)

    # Visual polish: Smooth shading and Bevel modifier for realistic edges
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.0015
    bevel.segments = 3

    return obj

def main():
    clear_scene()
    
    # Construct geometry
    plate_obj = create_plate()
    
    # Assign material
    material = create_navy_blue_material()
    plate_obj.data.materials.append(material)

if __name__ == "__main__":
    main()
