import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Deletes all objects in the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_leaf():
    # Parameters for an ovate leaf
    length = 4.0
    width = 2.5
    res_u = 64  # longitudinal resolution
    res_v = 32  # transverse resolution
    cup_long = 0.15     # Longitudinal curvature (arching)
    cup_trans = 0.25    # Transverse cupping
    ovate_factor = 0.6   # How much it bulges at the base relative to mid-section
    stem_radius = 0.05
    stem_length = 1.5

    bm = bmesh.new()

    # Generate grid of vertices for the blade
    verts = []
    for i in range(res_u + 1):
        row = []
        # u from -1 to 1 (longitudinal)
        u = (i / res_u) * 2 - 1 
        
        # Ovate shape function: wider at base, tapering to tip
        # We use a modified ellipse where the center is shifted towards the base
        # w(u) proportional to sqrt(1 - u^2), but biased
        w_factor = math.sqrt(max(0, 1 - u**2)) * (1 + ovate_factor * (-u))
        
        for j in range(res_v + 1):
            # v from -1 to 1 (transverse)
            v = (j / res_v) * 2 - 1 
            
            x = u * length * 0.5
            y = v * w_factor * width * 0.5
            
            # Natural curvature: Longitudinal bend
            z_long = cup_long * (u**2) * (length * 0.2)
            
            # Transverse cupping (forming a bowl/trough shape)
            z_trans = cup_trans * (v**2) * (width * 0.1)
            
            # Central vein protrusion: slight ridge at v=0
            vein_bump = 0
            if abs(v) < 0.15:
                vein_bump = (1.0 - abs(v)/0.15) * 0.04 * (1.0 - (u+1)*0.5)
            
            z = z_long + z_trans + vein_bump
            
            vert = bm.verts.new(Vector((x, y, z)))
            row.append(vert)
        verts.append(row)

    # Create faces for the blade
    for i in range(res_u):
        for j in range(res_v):
            bm.faces.new((
                verts[i][j], 
                verts[i+1][j], 
                verts[i+1][j+1], 
                verts[i][j+1]
            ))

    # Create the petiole (stem)
    # Stem starts at the base of the leaf: u = -1, v = 0
    base_vert = verts[0][res_v // 2]
    base_pos = base_vert.co
    
    stem_segments = 8
    stem_rings = 12
    stem_verts = []
    for r in range(stem_rings + 1):
        ring = []
        # t is the interpolation along the stem length
        t = r / stem_rings
        z_off = -t * stem_length
        x_off = -t * (stem_length * 0.2) # Slight slant
        
        for s in range(stem_segments):
            angle = (s / stem_segments) * 2 * math.pi
            # The stem is a cylinder extending from the base
            ox = base_pos.x + x_off
            oy = base_pos.y + math.cos(angle) * stem_radius
            oz = base_pos.z + math.sin(angle) * stem_radius + z_off
            
            v_stem = bm.verts.new(Vector((ox, oy, oz)))
            ring.append(v_stem)
        stem_verts.append(ring)

    # Create faces for the stem cylinder
    for r in range(stem_rings):
        for s in range(stem_segments):
            s_next = (s + 1) % stem_segments
            bm.faces.new((
                stem_verts[r][s], 
                stem_verts[r+1][s], 
                stem_verts[r+1][s_next], 
                stem_verts[r][s_next]
            ))

    # Bridge the stem to the leaf base for continuity
    # Connect the first ring of the stem to the central part of the blade base
    for s in range(stem_segments):
        s_next = (s + 1) % stem_segments
        v_stem1 = stem_verts[0][s]
        v_stem2 = stem_verts[0][s_next]
        # Use the central vertices of the base row
        v_leaf1 = verts[0][res_v // 2]
        v_leaf2 = verts[0][res_v // 2 + 1] if res_v // 2 + 1 <= res_v else v_leaf1
        
        # Simple triangle fan to bridge the gap
        try:
            bm.faces.new((v_stem1, v_stem2, v_leaf1))
            bm.faces.new((v_stem2, v_leaf2, v_leaf1))
        except ValueError:
            pass # Avoid duplicate faces

    # Convert BMesh to Mesh object
    mesh = bpy.data.meshes.new("LeafMesh")
    obj = bpy.data.objects.new("Leaf", mesh)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(mesh)
    bm.free()
    return obj

def apply_modifiers(obj):
    # Enable smooth shading for the entire object
    for poly in obj.data.polygons:
        poly.use_smooth = True

    # Subdivision Surface to make it organic and high fidelity
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3

    # Solidify to give the leaf a realistic physical thickness
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.015
    solid.offset = 0

def main():
    clear_scene()
    
    # Create the geometry
    leaf_obj = create_leaf()
    
    if leaf_obj:
        # Apply organic refinements
        apply_modifiers(leaf_obj)
        
        # Set object properties for better presentation (3/4 perspective view)
        # Rotation helps highlight the cupped shape and ovate blade
        leaf_obj.rotation_euler = (math.radians(20), 0, math.radians(45))
        
        # Move it slightly so the stem is visible relative to origin if needed
        leaf_obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
