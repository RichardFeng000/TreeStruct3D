import bpy
import bmesh
import math

def clear_scene():
    """Clear all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    """Create a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        # Make it look like ceramic/porcelain
        bsdf.inputs['Roughness'].default_value = 0.1
        bsdf.inputs['Specular IOR Level'].default_value = 0.5
    return mat

def create_plate():
    # Dimensions (in meters)
    r_outer = 0.15
    r_inner = 0.12
    h_total = 0.02
    t_bottom = 0.005
    
    bm = bmesh.new()
    
    # Create base disc
    bmesh.ops.create_circle(bm, cap_ends=True, radius=r_outer, segments=64)
    
    # Extrude to create basic thickness (the bottom part of the plate)
    face = bm.faces[0]
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts_extruded, vec=(0, 0, t_bottom))
    
    # Find the new top face (the one that was just extruded)
    top_face = [f for f in bm.faces if abs(f.calc_center_median().z - t_bottom) < 0.001][0]
    
    # Inset to define the rim area and the well center
    # Width of inset is (r_outer - r_inner)
    res = bmesh.ops.inset_individual(bm, faces=[top_face], width=r_outer - r_inner)
    well_face = res['faces'][0] # The inner circular face
    
    # Now find the rim face (the ring created by the inset)
    # All faces that aren't the well face and are at height t_bottom
    rim_faces = [f for f in bm.faces if f != well_face and abs(f.calc_center_median().z - t_bottom) < 0.001]
    
    # Extrude the rim upwards to create the lip
    res = bmesh.ops.extrude_face_region(bm, geom=rim_faces)
    rim_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=rim_verts, vec=(0, 0, h_total - t_bottom))
    
    # Create a subtle dip in the well (concave center)
    res = bmesh.ops.extrude_face_region(bm, geom=[well_face])
    well_verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=well_verts, vec=(0, 0, -0.002))

    # Bevel the top outer edge and inner lip edges for smoothness
    bm.edges.index_set('select', 0)
    for e in bm.edges:
        # Select edges at the very top height
        if abs(e.verts[0].co.z - h_total) < 0.001 or abs(e.verts[1].co.z - h_total) < 0.001:
            e.select = True
    
    bmesh.ops.bevel(bm, geom=bm.edges, offset=0.002, segments=3, affect='EDGES')

    # Finalize mesh
    mesh = bpy.data.meshes.new("PlateMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("DinnerPlate", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def create_base_ring():
    # Dimensions for the dark base ring visible underneath
    r_outer = 0.08
    r_inner = 0.074
    h = 0.003
    
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=r_outer, segments=64)
    
    # Create ring by insetting and removing center
    res = bmesh.ops.inset_individual(bm, faces=[bm.faces[0]], width=r_outer - r_inner)
    center_face = res['faces'][0]
    bm.faces.remove(center_face)
    
    # Extrude to give it some height (downwards since the plate sits at z=0 and goes up)
    edges = bm.edges[:]
    res = bmesh.ops.extrude_edge_only(bm, edges=edges)
    verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, -h))
    
    # Close the ring gaps
    bmesh.ops.contextual_create(bm, geom=res['geom'])

    mesh = bpy.data.meshes.new("BaseRingMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("BaseRing", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def main():
    clear_scene()
    
    # Materials
    # Pale blue-gray (mint-tinted): RGB approx (0.78, 0.84, 0.84)
    plate_mat = create_material("PlateMaterial", (0.78, 0.84, 0.84, 1.0))
    # Dark base ring: almost black/dark gray
    ring_mat = create_material("RingMaterial", (0.05, 0.05, 0.05, 1.0))
    
    # Plate body
    plate = create_plate()
    plate.data.materials.append(plate_mat)
    
    # Base ring
    ring = create_base_ring()
    ring.data.materials.append(ring_mat)

if __name__ == "__main__":
    main()
