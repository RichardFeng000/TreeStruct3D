import bpy
import bmesh
import math

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_navy_blue_material():
    """Creates a dark navy blue material with slight specular quality."""
    mat = bpy.data.materials.new(name="NavyBluePlate")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Dark Navy Blue color (R, G, B, A)
        bsdf.inputs['Base Color'].default_value = (0.01, 0.02, 0.12, 1.0)
        # Ceramic glaze look
        bsdf.inputs['Roughness'].default_value = 0.15
        # Specular IOR Level is the name in Blender 4.0+ for specular strength
        if 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.5
    return mat

def create_plate():
    """Constructs the plate geometry using BMesh."""
    # Parameters (in meters)
    outer_radius = 0.15       # 30cm diameter
    base_thickness = 0.01     # Bottom slab thickness
    rim_width = 0.02          # Width of the raised rim border
    rim_height_extra = 0.015  # Height above the well floor
    foot_ring_radius = 0.06   # Radius of underside foot ring
    foot_ring_depth = 0.005   # How far the foot ring extends down

    bm = bmesh.new()

    # 1. Create base disk at z=0
    bmesh.ops.create_circle(bm, radius=outer_radius, segments=64)
    # Fill the circle to create a face
    faces = bmesh.ops.contextual_create(bm, geom=bm.verts[:])
    bottom_face = faces['faces'][0]

    # 2. Extrude base thickness to create the floor of the plate (Z=0 to Z=base_thickness)
    res = bmesh.ops.extrude_face_region(bm, geom=[bottom_face])
    verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BVVert)]
    bmesh.ops.translate(bm, vec=(0, 0, base_thickness), verts=verts_extruded)

    # Find the new top face (the one created by extrusion at Z=base_thickness)
    top_face = None
    for f in bm.faces:
        if abs(f.calc_center_median().z - base_thickness) < 0.001:
            top_face = f
            break

    # 3. Inset the top face to create a border for the rim and a center well
    # bmesh.ops.inset_region returns 'verts', 'edges', 'faces'
    inset_res = bmesh.ops.inset_region(bm, faces=[top_face], thickness=rim_width)
    well_face = inset_res['faces'][0]
    
    # Identify the rim faces (the ring created by the inset)
    # All faces at Z=base_thickness except the well_face are part of the rim base
    rim_faces = [f for f in bm.faces if f != well_face and abs(f.calc_center_median().z - base_thickness) < 0.001]

    # 4. Create the raised rim border by extruding those ring faces upward
    res_rim = bmesh.ops.extrude_face_region(bm, geom=rim_faces)
    rim_verts_extruded = [v for v in res_rim['geom'] if isinstance(v, bmesh.types.BVVert)]
    bmesh.ops.translate(bm, vec=(0, 0, rim_height_extra), verts=rim_verts_extruded)

    # 5. Create the ring base (underside foot)
    # The bottom face is still at Z=0. Let's find it again to be sure.
    bottom_face = None
    for f in bm.faces:
        if abs(f.calc_center_median().z) < 0.001:
            bottom_face = f
            break
    
    # Inset the bottom face to define the footprint of the ring base
    # thickness for inset is distance from edge, so outer_radius - foot_ring_radius
    inset_foot_res = bmesh.ops.inset_region(bm, faces=[bottom_face], thickness=outer_radius - foot_ring_radius)
    foot_face = inset_foot_res['faces'][0]
    
    # Extrude the foot ring slightly downwards (into negative Z)
    res_foot = bmesh.ops.extrude_face_region(bm, geom=[foot_face])
    foot_verts_extruded = [v for v in res_foot['geom'] if isinstance(v, bmesh.types.BVVert)]
    bmesh.ops.translate(bm, vec=(0, 0, -foot_ring_depth), verts=foot_verts_extruded)

    # Finalize BMesh and create object
    mesh = bpy.data.meshes.new("DinnerPlateMesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("DinnerPlate", mesh)
    bpy.context.collection.objects.link(obj)

    # Smooth shading for a ceramic look
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    # Apply bevel modifier to soften sharp edges
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.002
    bevel.segments = 3

    return obj

def main():
    clear_scene()
    
    # Create geometry
    plate_obj = create_plate()
    
    # Create and assign material
    material = create_navy_blue_material()
    plate_obj.data.materials.append(material)

if __name__ == "__main__":
    main()
