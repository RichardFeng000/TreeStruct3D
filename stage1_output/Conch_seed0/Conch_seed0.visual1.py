import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_conch_shell():
    # Spiral parameters
    turns = 5.0
    theta_max = turns * 2 * math.pi
    growth_rate = 0.16  # How fast the shell expands outwards
    z_step = 0.08       # Vertical distance between whorls
    start_radius = 0.02 # Tip size
    
    res_theta = 600     # Longitudinal resolution
    res_phi = 64        # Radial resolution
    
    bm = bmesh.new()
    rings = []

    for i in range(res_theta):
        theta = (i / res_theta) * theta_max
        
        # Logarithmic spiral for the path of the center
        r_path = start_radius * math.exp(growth_rate * theta)
        cx = r_path * math.cos(theta)
        cy = r_path * math.sin(theta)
        cz = z_step * theta
        center = Vector((cx, cy, cz))

        # The thickness of the shell tube grows as it spirals
        tube_base_radius = start_radius * 0.7 * math.exp(growth_rate * theta)
        
        # Create prominent wavy ridges (varices)
        # We use a sine wave tied to theta for spiral ribs and another for "waviness"
        ridge_amplitude = tube_base_radius * 0.25
        # Frequency of major ribs
        ribs_count = 6
        rib_factor = math.sin(theta * ribs_count) 
        # Add a secondary undulating ripple
        ripple = math.sin(theta * 30.0) * (ridge_amplitude * 0.2)
        current_radius = tube_base_radius + (rib_factor * ridge_amplitude) + ripple

        # Calculate the local orientation frame for the cross-section ring
        # Tangent to the spiral path in XY plane roughly
        tangent = Vector((-math.sin(theta), math.cos(theta), 0)).normalized()
        normal = Vector((cx, cy, 0)).normalized() if r_path > 0.01 else Vector((1, 0, 0))
        binormal = tangent.cross(normal).normalized()
        normal = binormal.cross(tangent).normalized()

        ring_verts = []
        for j in range(res_phi):
            phi = (j / res_phi) * 2 * math.pi
            
            # Flatten the cross-section slightly into an oval
            scale_x = 1.0 + (theta / theta_max) * 0.4
            scale_y = 1.0
            
            vx = math.cos(phi) * current_radius * scale_x
            vy = math.sin(phi) * current_radius * scale_y
            
            # Offset vertices to create the "hollow" effect for the aperture later
            pos = center + (normal * vx) + (binormal * vy)
            
            # Flare the outer lip of the final whorl
            if i > res_theta * 0.8:
                t = (i - res_theta * 0.8) / (res_theta * 0.2)
                lip_flare = t * tube_base_radius * 0.6
                pos += (Vector((vx, vy, 0)).normalized() * lip_flare)

            v = bm.verts.new(pos)
            ring_verts.append(v)
        
        rings.append(ring_verts)

    bm.verts.ensure_lookup_table()

    # Connect rings into faces
    for i in range(len(rings) - 1):
        r1 = rings[i]
        r2 = rings[i+1]
        for j in range(res_phi):
            v1, v2 = r1[j], r1[(j + 1) % res_phi]
            v3, v4 = r2[(j + 1) % res_phi], r2[j]
            # Only create face if it's not the "opening" part of the final whorls
            # We leave a gap for the aperture in the last 20% of the spiral
            if i > res_theta * 0.8:
                # Gap logic: exclude vertices in a specific angular range (the aperture)
                if j > res_phi * 0.5 and j < res_phi * 0.8:
                    continue
            
            try:
                bm.faces.new((v1, v2, v3, v4))
            except ValueError:
                pass

    # Create the mesh object
    mesh = bpy.data.meshes.new("ConchShell")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("ConchShell", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Smooth the result
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    return obj

def setup_materials(obj):
    # Create colors
    mat_brown = bpy.data.materials.new(name="ShellBrown")
    mat_brown.use_nodes = True
    mat_brown.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.3, 0.18, 0.1, 1.0)
    
    mat_cream = bpy.data.materials.new(name="ShellCream")
    mat_cream.use_nodes = True
    mat_cream.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.95, 0.88, 0.75, 1.0)
    
    obj.data.materials.append(mat_brown)
    obj.data.materials.append(mat_cream)

    # Assign materials based on undulating patterns (coord-based)
    for poly in obj.data.polygons:
        center = Vector((0, 0, 0))
        for v_idx in poly.vertices:
            center += obj.data.vertices[v_idx].co
        center /= len(poly.vertices)
        
        # Use a combination of distance and angle to create organic stripes
        dist = center.length
        angle = math.atan2(center.y, center.x)
        pattern = math.sin(dist * 5.0 + math.cos(angle * 4.0) * 2.0)
        poly.material_index = 0 if pattern > 0 else 1

def main():
    clear_scene()
    shell = create_conch_shell()
    setup_materials(shell)
    
    # Position for a professional three-quarter view
    shell.rotation_euler[0] = math.radians(-30)
    shell.rotation_euler[1] = math.radians(45)
    shell.location = (0, 0, 0)

if __name__ == "__main__":
    main()
