import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene objects."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_pine_needle_material():
    """Creates a brownish-tan material for the pine needle."""
    mat = bpy.data.materials.new(name="PineNeedleMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    for node in nodes:
        nodes.remove(node)
    
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Brownish-tan color (RGB)
    bsdf.inputs['Base Color'].default_value = (0.45, 0.35, 0.2, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.7
    
    links = mat.node_tree.links
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def create_pine_needle():
    """Generates a thin, curved pine needle as a mesh."""
    # Parameters
    length = 2.4
    segments = 64
    ring_res = 8  # Low res because it's extremely thin
    max_radius = 0.005
    min_radius = 0.0005
    arc_amplitude = 0.3

    bm = bmesh.new()
    
    verts = []
    for i in range(segments + 1):
        # t goes from -1 to 1
        t = (i / segments) * 2.0 - 1.0
        
        # Position along a gentle arc in XY plane
        x = t * (length / 2.0)
        y = arc_amplitude * (1.0 - t**2) # Parabolic arc
        z = 0
        center = Vector((x, y, z))
        
        # Taper radius: thinner at ends, thicker in middle
        # Using a simple bell-like curve for tapering
        radius = max_radius * (1.0 - abs(t)**2) + min_radius
        
        # Create ring of vertices
        ring = []
        for j in range(ring_res):
            angle = (j / ring_res) * 2.0 * math.pi
            vx = center.x + radius * math.cos(angle) * 0.1 # Slightly flatten the cross section for realism
            vy = center.y + radius * math.sin(angle) * 0.1
            vz = center.z + radius * math.sin(angle) # Make it a circular-ish strand
            # Actually, let's just make a simple circle in the local normal plane (XZ for XY arc)
            # Local axis: The direction of the needle is roughly X. So cross section is YZ.
            # But since the needle arcs in Y, we should orient the ring perpendicular to the tangent.
            
            # Simple approximation for a very thin filament: 
            # Offset along Z and a bit of X/Y depending on tangent
            # For a simple "hair", a small circle in YZ is usually fine if arc is gentle.
            off_x = radius * math.cos(angle) * 0.1 # Small flatten
            off_y = radius * math.sin(angle) * 0.5
            off_z = radius * math.cos(angle) * 0.9 
            # Better: just a small circle perpendicular to the path
            v = bm.verts.new(Vector((center.x + radius * math.cos(angle) * 0.2, center.y, center.z + radius * math.sin(angle))))
            ring.append(v)
        
        verts.append(ring)

    # Create faces between rings
    for i in range(segments):
        ring_a = verts[i]
        ring_b = verts[i+1]
        for j in range(ring_res):
            v1 = ring_a[j]
            v2 = ring_a[(j + 1) % ring_res]
            v3 = ring_b[(j + 1) % ring_res]
            v4 = ring_b[j]
            bm.faces.new((v1, v2, v3, v4))

    # Cap the ends (though they are tiny)
    for end_idx in [0, segments]:
        ring = verts[end_idx]
        bm.faces.new(ring)

    # Finalize mesh
    mesh_data = bpy.data.meshes.new("PineNeedleMesh")
    bm.to_mesh(mesh_data)
    bm.free()

    obj = bpy.data.objects.new("PineNeedle", mesh_data)
    bpy.context.collection.objects.link(obj)
    
    # Material
    mat = create_pine_needle_material()
    obj.data.materials.append(mat)
    
    return obj

def main():
    clear_scene()
    needle = create_pine_needle()
    
    # Position for "rendered from above" view: mostly flat on XY, 
    # with slight natural rotations
    needle.rotation_euler[0] = 0.1 
    needle.rotation_euler[2] = 0.2

if __name__ == "__main__":
    main()
