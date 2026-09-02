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
        # Ceramic look
        bsdf.inputs['Roughness'].default_value = 0.15
        bsdf.inputs['Specular IOR Level'].default_value = 0.5
    return mat

def create_plate():
    # Dimensions (in meters)
    r_outer = 0.15
    r_inner = 0.12
    h_base = 0.005  # Thickness of the bottom slab
    h_lip = 0.01    # Height of the rim lip
    inset_width = r_outer - r_inner
    
    bm = bmesh.new()
    
    # Create base disc (bottom of plate)
    bmesh.ops.create_circle(bm, cap_ends=True, radius=r_outer, segments=64)
    bm.faces.ensure_lookup_table()
    
    # Extrude to create basic thickness
    face = bm.faces[0]
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts_extruded, vec=(0, 0, h_base))
    
    bm.faces.ensure_lookup_table()
    # Find the top face
    top_face = [f for f in bm.faces if abs(f.calc_center_median().z - h_base) < 0.001][0]
    
    # Use inset_region instead of inset_individual to avoid "width" error (it uses 'thickness')
    # thickness is the distance from the edge inwards
    res = bmesh.ops.inset_region(bm, faces=[top_face], thickness=inset_width)
    well_face = res['faces'][0] 
    
    bm.faces.ensure_lookup_table()
    # Identify the rim faces (the ring created by the inset)
    rim_faces = [f for f in bm.faces if f != well_face and abs(f.calc_center_median().z - h_base) < 0.001]
    
    # Extrude the rim upwards to create the lip
    res_lip = bmesh.ops.extrude_face_region(bm, geom=rim_faces)
    lip_verts = [v for v in res_lip['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=lip_verts, vec=(0, 0, h_lip))
    
    # Create a subtle dip in the well (concave center)
    res_well = bmesh.ops.extrude_face_region(bm, geom=[well_face])
    well_verts = [v for v in res_well['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=well_verts, vec=(0, 0, -0.003))

    # Bevel the edges for smoothness
    bm.edges.ensure_lookup_table()
    # Select edges at the very top and outer bottom for rounding
    edge_select = []
    for e in bm.edges:
        z1 = e.verts[0].co.z
        z2 = e.verts[1].co.z
        if abs(z1 - (h_base + h_lip)) < 0.001 and abs(z2 - (h_base + h_lip)) < 0.001:
            edge_select.append(e)
        elif abs(z1 - 0) < 0.001 and abs(z2 - 0) < 0.001:
            # Only outer bottom edges
            if any(v.co.length > r_outer * 0.9 for v in e.verts):
                edge_select.append(e)

    if edge_select:
        bmesh.ops.bevel(bm, geom=edge_select, offset=0.004, segments=3, affect='EDGES')

    # Finalize mesh
    mesh = bpy.data.meshes.new("PlateMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("DinnerPlate", mesh)
    bpy.context.collection.objects.link(obj)
    # Set smooth shading
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

def create_base_ring():
    # Dark base ring visible underneath
    r_mid = 0.07
    r_thick = 0.004
    h_ring = 0.002
    
    bm = bmesh.new()
    # Create a torus-like thin ring using a circle and extrude/fill
    bmesh.ops.create_circle(bm, cap_ends=False, radius=r_mid, segments=64)
    
    # Extrude inwards to make the thickness of the ring wall
    res = bmesh.ops.extrude_edge_only(bm, edges=bm.edges[:])
    verts_inner = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    # Move inner vertices towards center (simple radial scale)
    for v in verts_inner:
        v.co *= (1.0 - (r_thick / r_mid))
    
    # Bridge the ring faces
    bmesh.ops.contextual_create(bm, geom=bm.edges[:])
    
    # Extrude Z down for height
    bm.faces.ensure_lookup_table()
    res_z = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    verts_z = [v for v in res_z['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts_z, vec=(0, 0, -h_ring))

    mesh = bpy.data.meshes.new("BaseRingMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("BaseRing", mesh)
    bpy.context.collection.objects.link(obj)
    # The ring sits at the bottom (z=0). 
    # Since we extruded from 0 to -h_ring, it stays under the plate's base.
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

def main():
    clear_scene()
    
    # Pale blue-gray (mint-tinted): RGB approx (0.78, 0.84, 0.84)
    plate_mat = create_material("PlateMaterial", (0.78, 0.84, 0.84, 1.0))
    # Dark base ring: almost black/dark gray
    ring_mat = create_material("RingMaterial", (0.05, 0.05, 0.05, 1.0))
    
    # Create the plate body
    plate = create_plate()
    plate.data.materials.append(plate_mat)
    
    # Create the base ring
    ring = create_base_ring()
    ring.data.materials.append(ring_mat)

if __name__ == "__main__":
    main()
