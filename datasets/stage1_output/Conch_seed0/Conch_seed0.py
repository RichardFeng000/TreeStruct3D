import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_conch_shell():
    # Spiral parameters for a conch shape
    turns = 4.0
    theta_max = turns * 2 * math.pi
    growth_factor = 0.18  # Logarithmic expansion rate
    z_scale = 0.15        # Vertical spacing
    start_radius = 0.01   # Very tip of the spire
    
    res_theta = 800       # High resolution for smooth curves
    res_phi = 48          # Resolution of cross-section
    
    bm = bmesh.new()
    rings = []

    for i in range(res_theta):
        theta = (i / res_theta) * theta_max
        
        # Logarithmic spiral growth for the path center
        # r = a * e^(b*theta)
        r_path = start_radius * math.exp(growth_factor * theta)
        cx = r_path * math.cos(theta)
        cy = r_path * math.sin(theta)
        # Z also grows to create the spire height
        cz = z_scale * (math.exp(growth_factor * theta) - 1)
        center = Vector((cx, cy, cz))

        # Tube radius also grows exponentially
        tube_radius = start_radius * 0.8 * math.exp(growth_factor * theta)
        
        # Prominent wavy ridges (Varices)
        # We add a strong periodic pulse to the radius every few degrees
        ridge_freq = 8  # Number of major ribs around the shell
        ridge_amp = tube_radius * 0.25
        ribs = math.cos(theta * ridge_freq) * ridge_amp
        
        # Add secondary waviness for a "natural" look
        waviness = math.sin(theta * 40) * (tube_radius * 0.05)
        current_r = tube_radius + ribs + waviness

        # Frame construction for the cross-section ring
        tangent = Vector((-math.sin(theta), math.cos(theta), growth_factor * r_path)).normalized()
        up = Vector((0, 0, 1))
        right = tangent.cross(up).normalized()
        actual_up = right.cross(tangent).normalized()

        ring_verts = []
        for j in range(res_phi):
            phi = (j / res_phi) * 2 * math.pi
            
            # Conch shells are often slightly flattened/oval on the bottom
            scale_x = 1.0
            scale_y = 0.8 + (theta / theta_max) * 0.4 # Flattens as it grows
            
            vx = math.cos(phi) * current_r * scale_x
            vy = math.sin(phi) * current_r * scale_y
            
            # Offset vertices relative to the center
            pos = center + (right * vx) + (actual_up * vy)
            
            # Flare the outer lip of the final whorl for a "wide aperture"
            if i > res_theta * 0.85:
                t = (i - res_theta * 0.85) / (res_theta * 0.15)
                flare_dir = (pos - center).normalized()
                pos += flare_dir * (t * tube_radius * 0.7)

            v = bm.verts.new(pos)
            ring_verts.append(v)
        
        rings.append(ring_verts)

    bm.verts.ensure_lookup_table()

    # Connect the rings to form a mesh surface
    for i in range(len(rings) - 1):
        r1 = rings[i]
        r2 = rings[i+1]
        for j in range(res_phi):
            v1, v2 = r1[j], r1[(j + 1) % res_phi]
            v3, v4 = r2[(j + 1) % res_phi], r2[j]
            
            # Aperture Logic: Leave a gap in the final 15% of the shell's growth
            if i > res_theta * 0.85:
                # Only skip faces that would close the "mouth" of the shell
                # We exclude a specific angular segment (roughly from phi=0 to pi/2)
                if j < res_phi * 0.4:
                    continue
            
            try:
                bm.faces.new((v1, v2, v3, v4))
            except ValueError:
                pass

    mesh = bpy.data.meshes.new("ConchShell")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("ConchShell", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Smoothing and subdivision for a high-quality look
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    return obj

def setup_materials(obj):
    # Define colors
    mat_brown = bpy.data.materials.new(name="ShellBrown")
    mat_brown.use_nodes = True
    mat_brown.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.35, 0.2, 0.1, 1.0)
    
    mat_cream = bpy.data.materials.new(name="ShellCream")
    mat_cream.use_nodes = True
    mat_cream.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.9, 0.85, 0.7, 1.0)
    
    obj.data.materials.append(mat_brown)
    obj.data.materials.append(mat_cream)

    # Create irregular undulating patterns using noise-like functions on vertex positions
    for poly in obj.data.polygons:
        center = Vector((0, 0, 0))
        for v_idx in poly.vertices:
            center += obj.data.vertices[v_idx].co
        center /= len(poly.vertices)
        
        # Undulating pattern based on spiral coordinates (distance + angle)
        dist = center.length
        angle = math.atan2(center.y, center.x)
        # Combine sine waves to create "irregular" stripes
        pattern = math.sin(dist * 8.0 + math.cos(angle * 3.0) * 1.5) + \
                  math.sin(dist * 2.0 - angle * 2.0)
        
        poly.material_index = 0 if pattern > 0 else 1

def main():
    clear_scene()
    shell = create_conch_shell()
    setup_materials(shell)
    
    # Set for three-quarter perspective view
    shell.rotation_euler[0] = math.radians(-20)
    shell.rotation_euler[1] = math.radians(45)

if __name__ == "__main__":
    main()
