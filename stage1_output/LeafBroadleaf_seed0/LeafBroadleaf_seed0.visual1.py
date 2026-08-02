import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Deletes all objects in the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_leaf():
    # Parameters for a broad, ovate leaf
    length = 4.0
    width = 2.8 # Slightly wider to be "broad"
    res_u = 64  # longitudinal resolution
    res_v = 32  # transverse resolution
    
    # Enhanced curvature for visible cupping
    cup_long = 0.4     # Longitudinal arching (bend of the whole leaf)
    cup_trans = 0.5    # Transverse curling (edges curving up)
    ovate_factor = 0.7  # Stronger taper from base to tip
    stem_radius = 0.06
    stem_length = 1.8

    bm = bmesh.new()

    # Generate grid of vertices for the blade
    verts = []
    for i in range(res_u + 1):
        row = []
        # u from -1 to 1 (longitudinal: -1 is base, 1 is tip)
        u = (i / res_u) * 2 - 1 
        
        # Ovate shape function: wide at base, tapering towards the tip
        # Use a combination of ellipse and linear taper for a natural ovate silhouette
        w_factor = math.sqrt(max(0, 1 - u**2)) * (1 + ovate_factor * (-u))
        
        for j in range(res_v + 1):
            # v from -1 to 1 (transverse: left edge to right edge)
            v = (j / res_v) * 2 - 1 
            
            x = u * length * 0.5
            y = v * w_factor * width * 0.5
            
            # Natural curvature: Longitudinal arch (the leaf bows along its axis)
            z_long = cup_long * (u**2 - 1) * (length * 0.1) # Negative so it arches "down" or "up" based on view
            
            # Transverse cupping (edges curve upwards, creating a trough)
            z_trans = cup_trans * (v**2) * (width * 0.15)
            
            # Central vein protrusion: distinct ridge along the center
            vein_bump = 0
            if abs(v) < 0.2:
                # Sharper profile for the vein to be visible in renders
                vein_bump = (1.0 - abs(v)/0.2)**2 * 0.15 * (1.0 - (u+1)*0.3)
            
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
    # Base of leaf is at u = -1, v = 0
    base_vert = verts[0][res_v // 2]
    base_pos = base_vert.co
    
    stem_segments = 12
    stem_rings = 12
    stem_verts = []
    for r in range(stem_rings + 1):
        ring = []
        t = r / stem_rings
        # Stem extends backwards and slightly downwards from the base
        z_off = -t * (stem_length * 0.3)
        x_off = -t * stem_length
        
        for s in range(stem_segments):
            angle = (s / stem_segments) * 2 * math.pi
            # Offset the cylinder so it aligns with the leaf's center line
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

    # Bridge stem to leaf base for continuity
    # We connect the top ring of the stem (index 0) to a small cluster at the leaf base
    for s in range(stem_segments):
        s_next = (s + 1) % stem_segments
        v_stem1 = stem_verts[0][s]
        v_stem2 = stem_verts[0][s_next]
        # Use the center of the leaf base row
        v_leaf1 = verts[0][res_v // 2]
        v_leaf2 = verts[0][res_v // 2 + 1] if res_v // 2 + 1 <= res_v else v_leaf1
        
        try:
            bm.faces.new((v_stem1, v_stem2, v_leaf1))
            bm.faces.new((v_stem2, v_leaf2, v_leaf1))
        except ValueError:
            pass

    # Convert BMesh to Mesh object
    mesh = bpy.data.meshes.new("LeafMesh")
    obj = bpy.data.objects.new("Leaf", mesh)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(mesh)
    bm.free()
    return obj

def apply_modifiers(obj):
    # Enable smooth shading
    for poly in obj.data.polygons:
        poly.use_smooth = True

    # Subdivision Surface for organic smoothness
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3

    # Solidify to give the leaf physical thickness
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.012
    solid.offset = 0

def main():
    clear_scene()
    
    leaf_obj = create_leaf()
    
    if leaf_obj:
        apply_modifiers(leaf_obj)
        # Set rotation for a dynamic three-quarter perspective view
        leaf_obj.rotation_euler = (math.radians(30), 0, math.radians(45))
        leaf_obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
