import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    """Clears the default scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color, transmission=0.0, roughness=0.5):
    """Creates a simple Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    node_principled.inputs['Base Color'].default_value = color
    node_principled.inputs['Roughness'].default_value = roughness
    
    if 'Transmission Weight' in node_principled.inputs:
        node_principled.inputs['Transmission Weight'].default_value = transmission
    elif 'Transmission' in node_principled.inputs:
        node_principled.inputs['Transmission'].default_value = transmission

    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_shade():
    """Creates the fabric shade with folds and scallops, oriented correctly (narrow top, wide bottom)."""
    res_theta = 128
    res_z = 60
    top_radius = 0.15
    bottom_radius = 0.45
    height = 0.7
    fold_count = 24
    fold_amplitude = 0.03
    scallop_count = 16
    scallop_amplitude = 0.05
    
    bm = bmesh.new()
    
    verts = []
    for iz in range(res_z):
        z_norm = iz / (res_z - 1) # 0 to 1
        # Lamp hangs down: top is at z=0, bottom is at z=-height
        curr_z = -z_norm * height
        
        r_base = top_radius + (bottom_radius - top_radius) * z_norm
        
        # Draped folds increase in strength toward the bottom (z_norm -> 1)
        fold_strength = (z_norm**1.2) * fold_amplitude
        
        ring_verts = []
        for it in range(res_theta):
            theta = (it / res_theta) * 2 * math.pi
            r_folded = r_base + math.sin(theta * fold_count) * fold_strength
            
            x = r_folded * math.cos(theta)
            y = r_folded * math.sin(theta)
            z = curr_z
            
            # Scalloping at the bottom edge (iz == res_z - 1)
            if iz == res_z - 1:
                z += math.cos(theta * scallop_count) * scallop_amplitude
                
            ring_verts.append(bm.verts.new(Vector((x, y, z))))
        verts.append(ring_verts)

    for iz in range(res_z - 1):
        for it in range(res_theta):
            v1 = verts[iz][it]
            v2 = verts[iz][it + 1] if it < res_theta - 1 else verts[iz][0]
            v3 = verts[iz+1][it + 1] if it < res_theta - 1 else verts[iz+1][0]
            v4 = verts[iz+1][it]
            bm.faces.new((v1, v2, v3, v4))

    mesh = bpy.data.meshes.new("ShadeMesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new("LampShade", mesh)
    bpy.context.collection.objects.link(obj)
    
    mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    mod.levels = 2
    mod.render_levels = 3
    
    return obj

def create_hardware():
    """Creates the suspension rod and wire frames."""
    dark_mat = create_material("HardwareMat", (0.02, 0.02, 0.02, 1.0), roughness=0.3)
    
    # Vertical Rod - extending from top of shade upwards to ceiling
    # Top of shade is at z=0. Center the rod at z=0.5 so it goes from 0 to 1.
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=1.0, location=(0, 0, 0.5))
    rod = bpy.context.active_object
    rod.name = "SuspensionRod"
    rod.data.materials.append(dark_mat)
    
    # Top Wire Frame (at the narrow top of the shade)
    bpy.ops.mesh.primitive_torus_add(
        location=(0, 0, 0), 
        major_radius=0.15, 
        minor_radius=0.006, 
        major_segments=64, 
        minor_segments=16
    )
    top_ring = bpy.context.active_object
    top_ring.name = "TopWireFrame"
    top_ring.data.materials.append(dark_mat)
    
    # Bottom Wire Frame (at the wide bottom of the shade)
    bpy.ops.mesh.primitive_torus_add(
        location=(0, 0, -0.7), 
        major_radius=0.45, 
        minor_radius=0.006, 
        major_segments=64, 
        minor_segments=16
    )
    bottom_ring = bpy.context.active_object
    bottom_ring.name = "BottomWireFrame"
    bottom_ring.data.materials.append(dark_mat)

def main():
    clear_scene()
    
    shade_mat = create_material(
        "ShadeMat", 
        (1.0, 0.85, 0.9, 1.0), # Soft pinkish-white
        transmission=0.4, 
        roughness=0.7
    )
    
    create_hardware()
    shade_obj = create_shade()
    shade_obj.data.materials.append(shade_mat)
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for poly in obj.data.polygons:
                poly.use_smooth = True

if __name__ == "__main__":
    main()
