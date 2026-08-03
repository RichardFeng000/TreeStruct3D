import bpy
import bmesh
import math

def clear_scene():
    """Clear all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, roughness=0.4):
    """Create a simple principled BSDF material with adjusted settings to avoid overexposure."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Lower the base color slightly to avoid blowing out in high-intensity lighting
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = roughness
        if 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.2
    return mat

def create_plate():
    # Dimensions (meters)
    r_outer = 0.16
    r_inner = 0.11
    h_total = 0.025
    well_depth = 0.012
    
    bm = bmesh.new()
    
    # Create the main circular body starting from z=0
    bmesh.ops.create_circle(bm, cap_ends=True, radius=r_outer, segments=64)
    bm.faces.ensure_lookup_table()
    
    # Extrude up to create height
    face = bm.faces[0]
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    verts_extruded = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts_extruded, vec=(0, 0, h_total))
    
    # Top face inset and extrusion to create the concave well
    bm.faces.ensure_lookup_table()
    top_face = [f for f in bm.faces if abs(f.calc_center_median().z - h_total) < 0.001][0]
    
    # Inset to define the rim width
    inset_width = r_outer - r_inner
    res = bmesh.ops.inset_region(bm, faces=[top_face], thickness=inset_width)
    well_face = res['faces'][0]
    
    # Extrude well downwards
    res_well = bmesh.ops.extrude_face_region(bm, geom=[well_face])
    well_verts = [v for v in res_well['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=well_verts, vec=(0, 0, -well_depth))

    # Create a concave bottom so the base ring is visible from the side
    # We push the center vertices of the bottom face upwards
    bm.faces.ensure_lookup_table()
    bottom_face = [f for f in bm.faces if abs(f.calc_center_median().z) < 0.001][0]
    # To make it concave, we can't just move a face; we need to subdivide or use vertex manipulation
    # For simplicity, let's just bevel the bottom outer edge heavily and push inner vertices up
    bottom_verts = [v for v in bottom_face.verts]
    for v in bottom_verts:
        dist = v.co.length
        if dist < r_outer * 0.8:
            # Push center upwards to create a "dome" on the bottom (concave underside)
            v.co.z += (1.0 - (dist / (r_outer * 0.8))) * 0.01

    # Smooth out all edges via heavy beveling
    bm.edges.ensure_lookup_table()
    all_edges = bm.edges[:]
    bmesh.ops.bevel(bm, geom=all_edges, offset=0.004, segments=2, affect='EDGES')

    mesh = bpy.data.meshes.new("PlateMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("DinnerPlate", mesh)
    bpy.context.collection.objects.link(obj)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

def create_base_ring():
    # The foot of the plate - a small dark ring sitting on z=0
    r_mid = 0.12  # Placed where the concave bottom meets the floor
    r_width = 0.015
    h_ring = 0.004
    
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=False, radius=r_mid, segments=64)
    res = bmesh.ops.extrude_edge_only(bm, edges=bm.edges[:])
    verts_inner = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
    for v in verts_inner:
        # Scale inner radius to create a ring width
        v.co *= (1.0 - (r_width / r_mid))
    
    bmesh.ops.contextual_create(bm, geom=bm.edges[:])
    
    bm.faces.ensure_lookup_table()
    res_z = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    verts_z = [v for v in res_z['geom'] if isinstance(v, bmesh.types.BMVert)]
    # Keep the base on the ground (0 to h_ring)
    bmesh.ops.translate(bm, verts=verts_z, vec=(0, 0, h_ring))

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
    # Adjusted to be slightly darker/more saturated to prevent render blow-out.
    plate_color = (0.5, 0.7, 0.7, 1.0) 
    plate_mat = create_material("PlateMaterial", plate_color, roughness=0.3)
    
    # Dark base ring: dark charcoal gray
    ring_color = (0.05, 0.05, 0.05, 1.0)
    ring_mat = create_material("RingMaterial", ring_color, roughness=0.6)
    
    plate = create_plate()
    plate.data.materials.append(plate_mat)
    
    ring = create_base_ring()
    ring.data.materials.append(ring_mat)

if __name__ == "__main__":
    main()
