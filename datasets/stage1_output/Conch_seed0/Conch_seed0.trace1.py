import bpy
import bmesh
import math
import random
from mathutils import Vector

def clear_scene():
    """Removes all default objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_conch_shell():
    """Procedurally generates a conch shell with geometric ridges and aperture."""
    # Parameters for the logarithmic spiral
    turns = 4.5
    theta_max = turns * 2 * math.pi
    growth_factor = 0.18  # Controls how fast the shell expands
    z_growth = 0.1        # Vertical growth of the spire
    base_radius = 0.1     # Initial size at the tip
    
    # Resolution settings
    res_theta = 400       # Number of segments along the spiral path
    res_phi = 60          # Number of vertices in each cross-section ring
    
    bm = bmesh.new()
    
    # Store rings to connect them later
    rings = []
    
    for i in range(res_theta):
        theta = (i / res_theta) * theta_max
        
        # 1. Calculate the center of the current whorl cross-section
        r_center = base_radius * math.exp(growth_factor * theta)
        cx = r_center * math.cos(theta)
        cy = r_center * math.sin(theta)
        cz = z_growth * theta
        center = Vector((cx, cy, cz))
        
        # 2. Determine the radius of the cross-section tube
        tube_radius = base_radius * 0.8 * math.exp(growth_factor * theta)
        
        # Add wavy ridges (Varices)
        ridge_strength = 0.15 * tube_radius
        ridge_mod = math.sin(theta * 6.0) * ridge_strength 
        undulation = math.sin(theta * 25.0) * (ridge_strength * 0.3)
        current_r = tube_radius + ridge_mod + undulation

        # 3. Create a local coordinate system for the ring (TNB frame)
        # Tangent to the spiral path
        tangent = Vector((
            -r_center * math.sin(theta) + growth_factor * base_radius * math.exp(growth_factor * theta) * math.cos(theta), 
            r_center * math.cos(theta) + growth_factor * base_radius * math.exp(growth_factor * theta) * math.sin(theta), 
            z_growth
        )).normalized()
        
        # Normal (pointing roughly away from center axis)
        normal = Vector((cx, cy, 0)).normalized()
        if normal.length < 0.1:
            normal = Vector((1, 0, 0))
            
        binormal = tangent.cross(normal).normalized()
        normal = binormal.cross(tangent).normalized()
        
        # 4. Generate the ring of vertices
        ring_verts = []
        for j in range(res_phi):
            phi = (j / res_phi) * 2 * math.pi
            
            # Shape the cross-section: make it slightly oval/flattened as it grows
            oval_factor = 1.0 + (theta / theta_max) * 0.6
            
            vx = math.cos(phi) * current_r * oval_factor
            vy = math.sin(phi) * current_r
            
            pos = center + (normal * vx) + (binormal * vy)
            
            # Special handling for the aperture: flaring the lip
            if i > res_theta * 0.85:
                t = (i - res_theta * 0.85) / (res_theta * 0.15)
                lip_expansion = t * 0.5 * tube_radius
                pos += normal * lip_expansion
                
            # Siphonal canal extension
            if i > res_theta * 0.92 and j > res_phi * 0.7 and j < res_phi * 0.9:
                t = (i - res_theta * 0.92) / (res_theta * 0.08)
                pos += tangent * (t * 0.6)

            v = bm.verts.new(pos)
            ring_verts.append(v)
        
        rings.append(ring_verts)
        
    bm.verts.ensure_lookup_table()
    
    # 5. Connect the rings with faces
    for i in range(len(rings) - 1):
        ring_a = rings[i]
        ring_b = rings[i+1]
        for j in range(res_phi):
            v1 = ring_a[j]
            v2 = ring_a[(j + 1) % res_phi]
            v3 = ring_b[(j + 1) % res_phi]
            v4 = ring_b[j]
            
            try:
                bm.faces.new((v1, v2, v3, v4))
            except ValueError:
                pass

    # 6. Handle the aperture opening (cut a gap)
    last_ring = rings[-1]
    start_gap = int(res_phi * 0.6)
    end_gap = int(res_phi * 0.9)
    
    faces_to_remove = []
    for f in bm.faces:
        # If face is connected to the last ring and within gap indices
        if any(v in last_ring[start_gap : end_gap] for v in f.verts):
            # Check if it's part of the very end sections
            if any(v in rings[-1] for v in f.verts) or any(v in rings[-2] for v in f.verts):
                faces_to_remove.append(f)
    
    bmesh.ops.delete(bm, geom=faces_to_remove, context='FACES')

    # Create the object
    mesh = bpy.data.meshes.new("ConchShell")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("ConchShell", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Subdivision Surface for smoothness
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3
    
    # Smooth shading
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    return obj

def setup_materials(obj):
    """Adds basic material colors to simulate brown-and-cream patterns."""
    mat_brown = bpy.data.materials.new(name="ShellBrown")
    mat_brown.use_nodes = True
    mat_brown.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.35, 0.2, 0.1, 1.0)
    
    mat_cream = bpy.data.materials.new(name="ShellCream")
    mat_cream.use_nodes = True
    mat_cream.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.9, 0.85, 0.7, 1.0)
    
    obj.data.materials.append(mat_brown)
    obj.data.materials.append(mat_cream)
    
    # Procedurally assign material indices to polygons based on coordinates
    # Fix: Use obj.data.vertices[v].co instead of v.co
    for poly in obj.data.polygons:
        center = Vector((0, 0, 0))
        for v_idx in poly.vertices:
            center += obj.data.vertices[v_idx].co
        center /= len(poly.vertices)
        
        dist = center.length
        angle = math.atan2(center.y, center.x)
        
        # Pattern formula for undulating stripes/spots
        pattern = math.sin(dist * 6.0) + math.cos(angle * 10.0) + math.sin(center.z * 8.0)
        if pattern > 0:
            poly.material_index = 0
        else:
            poly.material_index = 1

def main():
    clear_scene()
    conch = create_conch_shell()
    setup_materials(conch)
    
    # Rotate for three-quarter view perspective
    conch.rotation_euler[0] = math.radians(-20)
    conch.rotation_euler[1] = math.radians(45)

if __name__ == "__main__":
    main()
