import bpy
import bmesh
import math

def clear_scene():
    """Clears the default scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_pebble_material():
    """Creates a material for translucent cream stone with soft inner glow."""
    mat = bpy.data.materials.new(name="PebbleMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    for node in nodes:
        nodes.remove(node)
        
    # Principled BSDF for the main surface properties
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    
    # Pale cream color (off-white/warm yellow tint)
    # R=0.98, G=0.96, B=0.88 for a soft cream look
    bsdf.inputs['Base Color'].default_value = (0.98, 0.96, 0.88, 1.0)
    
    # Smooth surface but not glossy like glass
    bsdf.inputs['Roughness'].default_value = 0.25
    
    # Subsurface Scattering for the "translucent" organic look
    # Weight high to allow light penetration
    bsdf.inputs['Subsurface Weight'].default_value = 0.8
    # Radius tuned for a creamy/warm internal scatter
    bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.75, 0.5)
    
    # Soft glowing inner luminescence via Emission
    # Warm cream glow: R=0.95, G=0.9, B=0.75
    bsdf.inputs['Emission Color'].default_value = (0.95, 0.9, 0.75, 1.0)
    bsdf.inputs['Emission Strength'].default_value = 0.6
    
    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    return mat

def create_organic_pebble():
    """Generates a smooth, elongated pebble using low-frequency deformation."""
    # Start with a high-poly ico-sphere for smoothness
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1.0)
    obj = bpy.context.active_object
    obj.name = "OrganicPebble"
    
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    # 1. Initial scale for an elongated flat shape
    scale_x, scale_y, scale_z = 2.2, 1.3, 0.6
    for v in bm.verts:
        v.co.x *= scale_x
        v.co.y *= scale_y
        v.co.z *= scale_z
        
    # 2. Low-frequency organic deformation
    # Instead of random noise, we use sine waves to create smooth "bumps"
    for v in bm.verts:
        # Use coordinates as seeds for smooth displacement
        # X-axis wave for length variation
        dx = math.sin(v.co.x * 0.8) * 0.15
        # Y-axis wave for width variation
        dy = math.cos(v.co.z * 2.0 + v.co.x * 0.5) * 0.1
        # Z-axis wave for thickness variation (flatness)
        dz = math.sin(v.co.x * 1.2 + v.co.y * 0.8) * 0.08
        
        # Taper the ends slightly so it doesn't look like a cylinder
        dist_factor = (1.0 - abs(v.co.x / scale_x))**2
        
        v.co.x += dx * dist_factor
        v.co.y += dy
        v.co.z += dz
    
    bm.to_mesh(obj.data)
    bm.free()
    
    # High-quality smoothing for a river-worn appearance
    subsurf = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    subsurf.levels = 3
    subsurf.render_levels = 4
    
    bpy.ops.object.shade_smooth()
    
    return obj

def main():
    clear_scene()
    
    # Generate the pebble geometry
    pebble = create_organic_pebble()
    
    # Assign the cream-glow material
    mat = create_pebble_material()
    if pebble.data.materials:
        pebble.data.materials[0] = mat
    else:
        pebble.data.materials.append(mat)
        
    # Center the object
    pebble.location = (0, 0, 0)

if __name__ == "__main__":
    main()
