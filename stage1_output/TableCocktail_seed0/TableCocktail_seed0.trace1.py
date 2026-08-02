import bpy
import bmesh
import math

def clear_scene():
    """Removes all default objects from the scene."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_table_top():
    """Creates a circular, slightly beveled table top."""
    radius = 0.28  # 56cm diameter
    thickness = 0.04
    height = 1.1   # Total height to the top surface
    
    # Create cylinder for the top
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64, 
        radius=radius, 
        depth=thickness, 
        location=(0, 0, height - (thickness / 2))
    )
    top = bpy.context.active_object
    top.name = "TableTop"

    # Add a small bevel to the edges for realism
    bev = top.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.01
    bev.segments = 3
    
    # Smooth shading
    top.data.polygons.foreach_set("use_smooth", [True] * len(top.data.polygons))
    
    return top

def create_pedestal():
    """Creates the tapered stem and flared base using a BMesh profile."""
    # Profile points (Radius, Z)
    profile = [
        (0.35, 0.0),      # Bottom outer edge
        (0.28, 0.02),     # Slight lift for rounded base effect
        (0.15, 0.15),     # Flare transition
        (0.07, 0.6),      # Mid stem taper
        (0.05, 1.06),     # Top of stem connection
    ]
    
    mesh = bpy.data.meshes.new("PedestalMesh")
    obj = bpy.data.objects.new("Pedestal", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    segments = 64
    angle_step = (2 * math.pi) / segments
    
    # Create rings of vertices based on the profile
    rings = []
    for r, z in profile:
        ring = []
        for s in range(segments):
            angle = s * angle_step
            vx = r * math.cos(angle)
            vy = r * math.sin(angle)
            ring.append(bm.verts.new((vx, vy, z)))
        rings.append(ring)

    # Create faces between rings (the side walls)
    for i in range(len(rings) - 1):
        curr_ring = rings[i]
        next_ring = rings[i+1]
        for s in range(segments):
            s_next = (s + 1) % segments
            bm.faces.new((curr_ring[s], curr_ring[s_next], next_ring[s_next], next_ring[s]))

    # Create center vertices for caps
    v_bottom_center = bm.verts.new((0, 0, profile[0][1]))
    v_top_center = bm.verts.new((0, 0, profile[-1][1]))
    
    # Fill bottom cap (Base)
    bottom_ring = rings[0]
    for s in range(segments):
        s_next = (s + 1) % segments
        bm.faces.new((v_bottom_center, bottom_ring[s_next], bottom_ring[s]))
        
    # Fill top cap (Connection to tabletop)
    top_ring = rings[-1]
    for s in range(segments):
        s_next = (s + 1) % segments
        bm.faces.new((v_top_center, top_ring[s], top_ring[s_next]))

    # Finalize mesh
    bm.to_mesh(mesh)
    bm.free()
    
    # Smooth shading
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
    
    # Add Subdivision Surface for a high-fidelity organic feel
    subdiv = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 2

    return obj

def main():
    clear_scene()
    
    # Generate components
    create_table_top()
    create_pedestal()

if __name__ == "__main__":
    main()
