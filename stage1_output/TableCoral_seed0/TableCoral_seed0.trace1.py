import bpy
import bmesh
import random
import math
from mathutils import Vector

def clear_scene():
    """Clears all objects from the current scene."""
    if "Cube" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
    if "Camera" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Camera"], do_unlink=True)
    if "Light" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Light"], do_unlink=True)
    # Also delete any other remaining objects to be sure
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_coral_material():
    """Creates a procedural material for the coral with sandy beige and olive-green variations."""
    mat = bpy.data.materials.new(name="CoralMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    for node in nodes:
        nodes.remove(node)
        
    output = nodes.new('ShaderNodeOutputMaterial')
    principled = nodes.new('ShaderNodeBsdfPrincipled')
    noise = nodes.new('ShaderNodeTexNoise')
    color_ramp = nodes.new('ShaderNodeValToRGB')
    
    noise.inputs['Scale'].default_value = 12.0
    noise.inputs['Detail'].default_value = 16.0
    
    # sandy beige, warm tan, olive green
    color_ramp.color_ramp.elements[0].position = 0.35
    color_ramp.color_ramp.elements[0].color = (0.88, 0.82, 0.7, 1.0) # Sandy Beige
    
    element_mid = color_ramp.color_ramp.elements.new(0.65)
    element_mid.color = (0.75, 0.65, 0.5, 1.0) # Warm Tan
    
    color_ramp.color_ramp.elements[2].position = 0.85
    color_ramp.color_ramp.elements[2].color = (0.4, 0.45, 0.3, 1.0) # Olive Green
    
    links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], principled.inputs['Base Color'])
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    principled.inputs['Roughness'].default_value = 0.95
    return mat

def create_table_coral():
    """Procedurally generates a table coral geometry."""
    bm = bmesh.new()
    
    # Parameters for the plate
    rings = 12
    segments = 64
    base_radius = 4.0
    thickness = 0.3
    
    # Create a disk of vertices to allow internal projections and better displacement
    verts_map = {} # (ring, seg) -> vert
    for r_idx in range(rings):
        r_scale = r_idx / float(rings - 1)
        for s_idx in range(segments):
            angle = (2 * math.pi * s_idx) / segments
            # Add scallop distortion to the radius
            # Only apply strong distortions to outer rings
            distort = 0.0
            if r_idx > rings // 2:
                weight = (r_idx - rings // 2) / (rings // 2)
                scallop = 0.6 * math.sin(7 * angle) + 0.4 * math.cos(13 * angle)
                jitter = random.uniform(-0.3, 0.3)
                distort = weight * (scallop + jitter)
            
            rad = r_scale * base_radius + distort
            x = math.cos(angle) * rad
            y = math.sin(angle) * rad
            # Add slight organic curvature to the plate surface
            z = 0.15 * (1.0 - r_scale**2) 
            
            v = bm.verts.new(Vector((x, y, z)))
            verts_map[(r_idx, s_idx)] = v

    # Fill faces for the top surface
    bm.verts.ensure_lookup_table()
    for r in range(rings - 1):
        for s in range(segments):
            s_next = (s + 1) % segments
            v1 = verts_map[(r, s)]
            v2 = verts_map[(r, s_next)]
            v3 = verts_map[(r+1, s_next)]
            v4 = verts_map[(r+1, s)]
            try:
                bm.faces.new((v1, v2, v3, v4))
            except:
                pass

    # Extrude the rim downwards to create thickness
    # Identify rim vertices (outermost ring)
    rim_verts = [verts_map[(rings-1, s)] for s in range(segments)]
    
    # Since we want a solid volume, let's extrude the whole top surface
    # But it's easier to just duplicate the disk and flip it if we want a plate.
    # For procedural modeling with modifiers, we can just extrude the boundaries or 
    # create a second set of vertices.
    
    bottom_verts_map = {}
    for r in range(rings):
        for s in range(segments):
            v_top = verts_map[(r, s)]
            v_bot = bm.verts.new(v_top.co + Vector((0, 0, -thickness)))
            bottom_verts_map[(r, s)] = v_bot

    # Bottom faces
    for r in range(rings - 1):
        for s in range(segments):
            s_next = (s + 1) % segments
            v1 = bottom_verts_map[(r, s)]
            v2 = bottom_verts_map[(r, s_next)]
            v3 = bottom_verts_map[(r+1, s_next)]
            v4 = bottom_verts_map[(r+1, s)]
            try:
                bm.faces.new((v2, v1, v4, v3)) # Reversed winding for normal
            except:
                pass

    # Side faces (connecting top and bottom rim)
    for s in range(segments):
        s_next = (s + 1) % segments
        vt1 = verts_map[(rings-1, s)]
        vt2 = verts_map[(rings-1, s_next)]
        vb1 = bottom_verts_map[(rings-1, s)]
        vb2 = bottom_verts_map[(rings-1, s_next)]
        try:
            bm.faces.new((vt1, vt2, vb2, vb1))
        except:
            pass

    # --- Create upright projections (spikes) ---
    num_projections = 30
    for _ in range(num_projections):
        # Randomly pick a point on the top surface
        r_rand = random.randint(0, rings - 1)
        s_rand = random.randint(0, segments - 1)
        seed_v = verts_map[(r_rand, s_rand)]
        
        # Create a small organic mound/projection
        proj_h = random.uniform(0.4, 1.5)
        # Offset for randomness
        offset = Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), proj_h))
        tip_v = bm.verts.new(seed_v.co + offset)
        
        # Connect tip to some surrounding vertices for volume
        # Find neighbors in the map
        for dr in [-1, 0, 1]:
            for ds in [-1, 0, 1]:
                nr, ns = r_rand + dr, (s_rand + ds) % segments
                if 0 <= nr < rings:
                    neighbor_v = verts_map[(nr, ns)]
                    try:
                        bm.faces.new((seed_v, neighbor_v, tip_v))
                    except:
                        pass

    mesh = bpy.data.meshes.new("TableCoralMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("TableCoral", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

def apply_surface_detail(obj):
    """Adds modifiers to create the fine granular polyp texture."""
    # Subdivision for smoother base and better displacement
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3

    # Displacement forgranular look
    displace = obj.modifiers.new(name="Polyps", type='DISPLACE')
    tex = bpy.data.textures.new("PolypTexture", type='STUCCI')
    tex.noise_scale = 0.05
    tex.turbulence = 5.0
    
    displace.texture = tex
    displace.strength = 0.12

def main():
    clear_scene()
    coral_obj = create_table_coral()
    apply_surface_detail(coral_obj)
    coral_mat = create_coral_material()
    coral_obj.data.materials.append(coral_mat)
    coral_obj.location = (0, 0, 0)

if __name__ == "__main__":
    main()
