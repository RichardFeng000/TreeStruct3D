import bpy
import bmesh
import math

def clear_scene():
    """Clear all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.2):
    """Create a simple principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = roughness
        # Lower specularity to prevent the 'blown out' white look in renders
        if 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.3
    return mat

def create_plate():
    # Dimensions (meters)
    r_outer = 0.16
    r_inner = 0.12
    h_total = 0.02
    well_depth = 0.008
    
    bm = bmesh.new()
    
    # Create the main circular body (the base disc)
    bmesh.ops.create_circle(bm, cap_ends=True, radius=r_outer, segments=64)
    bm.faces.ensure_lookup_table()
    
    # Extrude to create basic height
    face = bm.faces[0]
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts_extruded, vec=(0, 0, h_total))
    
    # Identify the top face (the one at z = h_total)
    bm.faces.ensure_lookup_table()
    top_face = [f for f in bm.faces if abs(f.calc_center_median().z - h_total) < 0.001][0]
    
    # Inset the top face to create the rim area
    inset_width = r_outer - r_inner
    res = bmesh.ops.inset_region(bm, faces=[top_face], thickness=inset_width)
    well_face = res['faces'][0]
    
    # Extrude the well face DOWNWARDS into the plate to create a concave center
    res_well = bmesh.ops.extrude_face_region(bm, geom=[well_face])
    well_verts = [v for v in res_well['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=well_verts, vec=(0, 0, -well_depth))

    # Bevel the top outer edge and bottom outer edge for smoothness
    bm.edges.ensure_lookup_table()
    edge_select = []
    for e in bm.edges:
        z1, z2 = e.verts[0].co.z, e.verts[1].co.z
        # Top rim edge
        if abs(z1 - h_total) < 0.001 and abs(z2 - h_total) < 0.001:
            if any(v.co.length > r_outer * 0.9 for v in e.verts):
                edge_select.append(e)
        # Bottom edge
        elif abs(z1 - 0) < 0.001 and abs(z2 - 0) < 0.001:
            if any(v.co.length > r_outer * 0.9 for v in e.verts):
                edge_select.append(e)

    if edge_select:
        bmesh.ops.bevel(bm, geom=edge_select, offset=0.005, segments=3, affect='EDGES')

    mesh = bpy.data.meshes.new("PlateMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("DinnerPlate", mesh)
    bpy.context.collection.objects.link(obj)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

def create_base_ring():
    # The "foot" of the plate - a small dark ring underneath
    r_mid = 0.08
    r_thick = 0.01
    h_ring = 0.005 # Height so it's visible from side view
    
    bm = bmesh.new()
    # Create ring geometry using a circle and extrusion
    bmesh.ops.create_circle(bm, cap_ends=False, radius=r_mid, segments=64)
    res = bmesh.ops.extrude_edge_only(bm, edges=bm.edges[:])
    verts_inner = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in verts_inner:
        v.co *= (1.0 - (r_thick / r_mid))
    
    bmesh.ops.contextual_create(bm, geom=bm.edges[:])
    
    # Extrude Z to give it thickness, moving it slightly BELOW z=0 
    # so the plate sits on top of it and it is visible underneath.
    bm.faces.ensure_lookup_table()
    res_z = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    verts_z = [v for v in res_z['geom'] if isinstance(v, bmesh.types.BMVert)]
    # Move the ring from 0 to -h_ring
    bmesh.ops.translate(bm, verts=verts_z, vec=(0, 0, -h_ring))

    mesh = bpy.data.meshes.new("BaseRingMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("BaseRing", mesh)
    bpy.context.collection.objects.link(obj)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

def main():
    clear_scene()
    
    # Pale blue-gray (mint-tinted). 
    # Slightly lower brightness than previous iteration to avoid render blow-out.
    plate_color = (0.7, 0.85, 0.85, 1.0) 
    plate_mat = create_material("PlateMaterial", plate_color, roughness=0.2)
    
    # Dark base ring: nearly black
    ring_color = (0.03, 0.03, 0.03, 1.0)
    ring_mat = create_material("RingMaterial", ring_color, roughness=0.4)
    
    plate = create_plate()
    plate.data.materials.append(plate_mat)
    
    ring = create_base_ring()
    ring.data.materials.append(ring_mat)

if __name__ == "__main__":
    main()
