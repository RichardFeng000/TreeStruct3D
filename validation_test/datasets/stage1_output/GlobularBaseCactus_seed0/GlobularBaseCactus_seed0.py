import bpy
import bmesh
import math

def clear_scene():
    """Removes all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_globular_cactus():
    """
    Generates a 3D base mesh of a globular cactus with vertical lobed ribs.
    The geometry is created procedurally using bmesh.
    """
    # Parameters for the cactus geometry
    num_ribs = 10              # Number of longitudinal lobes
    rib_amplitude = 0.2        # How pronounced the ribs are
    rib_frequency = num_ribs   # Frequency of sine wave for ribbing
    segments_radial = 64       # Resolution around the circumference
    segments_vertical = 32     # Resolution from bottom to top
    height_scale = 1.2         # Makes it slightly ovoid/tall
    radius_base = 1.0          # Base radius of the cactus
    twist_factor = 0.4         # Adds a slight twist to the ribs for organic feel

    bm = bmesh.new()

    # Create vertices in a grid-like fashion (latitude and longitude)
    # We use a spherical-like distribution but modify the radius based on the angle theta
    verts = []
    for i in range(segments_vertical + 1):
        v_phi = (math.pi * i) / segments_vertical  # Polar angle from 0 to Pi
        z = math.cos(v_phi) * height_scale
        
        # The radius of the slice at this height
        slice_radius = math.sin(v_phi) * radius_base
        
        if i == 0 or i == segments_vertical:
            # Poles: only one vertex needed
            v = bm.verts.new((0, 0, z))
            verts.append([v])
        else:
            row = []
            for j in range(segments_radial):
                theta = (2 * math.pi * j) / segments_radial
                
                # Introduce organic twist based on height
                # v_phi varies from 0 to Pi, we map it to a offset for theta
                current_theta = theta + (v_phi * twist_factor)
                
                # Modulate radius to create the ribs
                # We use a cosine function to create the "bumps" and "valleys"
                modulation = 1.0 + rib_amplitude * math.cos(rib_frequency * current_theta)
                r = slice_radius * modulation
                
                x = r * math.cos(current_theta)
                y = r * math.sin(current_theta)
                
                v = bm.verts.new((x, y, z))
                row.append(v)
            verts.append(row)

    # Create faces between the vertices
    for i in range(segments_vertical):
        curr_row = verts[i]
        next_row = verts[i+1]
        
        if i == 0:
            # Top pole to first ring
            pole = curr_row[0]
            for j in range(segments_radial):
                v1 = next_row[j]
                v2 = next_row[(j + 1) % segments_radial]
                bm.faces.new((pole, v2, v1))
        elif i == segments_vertical - 1:
            # Last ring to bottom pole
            pole = next_row[0]
            for j in range(segments_radial):
                v1 = curr_row[j]
                v2 = curr_row[(j + 1) % segments_radial]
                bm.faces.new((pole, v1, v2))
        else:
            # Mid sections (quads)
            for j in range(segments_radial):
                v1 = curr_row[j]
                v2 = curr_row[(j + 1) % segments_radial]
                v3 = next_row[(j + 1) % segments_radial]
                v4 = next_row[j]
                bm.faces.new((v1, v2, v3, v4))

    # Finish bmesh and create object
    bm.normal_update()
    mesh_data = bmesh.new() # Temporary placeholder for the data block creation process
    
    # Convert BMesh to Mesh
    me = bpy.data.meshes.new("CactusMesh")
    bm.to_mesh(me)
    bm.free()
    
    obj = bpy.data.objects.new("GlobularCactus", me)
    bpy.context.collection.objects.link(obj)
    
    # Set smooth shading for the organic look
    for poly in me.polygons:
        poly.use_smooth = True

    # Add a Subdivision Surface modifier to enhance smoothness and roundness
    subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 3

    return obj

def main():
    clear_scene()
    cactus = create_globular_cactus()
    
    # Center the object at origin (already is, but for safety)
    cactus.location = (0, 0, 0)

if __name__ == "__main__":
    main()
