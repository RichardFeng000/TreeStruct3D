import bpy
import bmesh
import math
from mathutils import Vector

def clear_scene():
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_principled.inputs['Base Color'].default_value = color
    # Slightly lower roughness for a mushroom-like surface sheen
    node_principled.inputs['Roughness'].default_value = 0.7
    mat.node_tree.links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])
    return mat

def create_mushroom():
    # Materials: Use more saturated colors to prevent "blown-out" white renders
    mat_top = create_material("MushroomTop", (0.75, 0.65, 0.45, 1.0))  # Richer beige-tan
    mat_bottom = create_material("MushroomGills", (0.08, 0.06, 0.04, 1.0)) # Dark chocolate/black

    # 1. Create the main dome
    bm = bmesh.new()
    # Higher resolution for smooth organic ripples
    bmesh.ops.create_uvsphere(bm, u_segments=80, v_segments=40, radius=1.0)
    
    for v in bm.verts:
        # Flatten Z to create a cap shape
        v.co.z *= 0.5
        
        # Calculate polar coordinates for pattern generation
        angle = math.atan2(v.co.y, v.co.x)
        dist = Vector((v.co.x, v.co.y, 0)).length
        
        # Create pronounced "organic wavy line patterns" using modulated sines
        # Combine a radial wave and a spiral wave for more complexity
        wave_pattern = (
            0.07 * math.sin(8 * angle + dist * 4) + 
            0.03 * math.cos(15 * angle - dist * 6)
        )
        v.co.z += wave_pattern
        
        # Subtle outward organic wobble to avoid perfect symmetry
        v.co.x += 0.03 * math.sin(dist * 3 + v.co.z * 5)
        v.co.y += 0.03 * math.cos(dist * 3 - v.co.z * 5)

    # Cut off the bottom of the sphere to make a hollow cap
    verts_to_delete = [v for v in bm.verts if v.co.z < -0.1]
    bmesh.ops.delete(bm, geom=verts_to_delete)
    
    mesh_data = bpy.data.meshes.new("MushroomCapTop")
    bm.to_mesh(mesh_data)
    cap_obj = bpy.data.objects.new("MushroomCap", mesh_data)
    bpy.context.collection.objects.link(cap_obj)
    cap_obj.data.materials.append(mat_top)
    bm.free()

    # 2. Create the Gills (radial plate structure)
    gill_bm = bmesh.new()
    num_gills = 64 # Number of radial plates
    segments_per_gill = 16
    gill_height = 0.25 # Depth of gills

    for i in range(num_gills):
        theta = (i / num_gills) * 2 * math.pi
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        
        # Create a radial strip from center to edge
        verts = []
        for s in range(segments_per_gill + 1):
            r = (s / segments_per_gill) * 0.95 # Slightly inside the cap rim
            # Gills curve slightly downward then outward
            z = -0.1 - (math.sin((s/segments_per_gill)*math.pi) * gill_height)
            
            v = gill_bm.verts.new(Vector((r * cos_t, r * sin_t, z)))
            verts.append(v)
        
        # To give gills volume, create a thin duplicate slightly offset in Z 
        # and bridge them to make actual faces
        verts_bottom = []
        for v in verts:
            verts_bottom.append(gill_bm.verts.new(v.co + Vector((0, 0, -0.01))) )
            
        for s in range(segments_per_gill):
            try:
                # Create the "plate" face for each gill segment
                gill_bm.faces.new([verts[s], verts[s+1], verts_bottom[s+1], verts_bottom[s]])
            except ValueError:
                pass

    gill_mesh_data = bpy.data.meshes.new("MushroomGills")
    gill_bm.to_mesh(gill_mesh_data)
    gill_obj = bpy.data.objects.new("Gills", gill_mesh_data)
    bpy.context.collection.objects.link(gill_obj)
    gill_obj.data.materials.append(mat_bottom)
    gill_bm.free()

    # Join the objects
    bpy.context.view_layer.objects.active = cap_obj
    cap_obj.select_set(True)
    gill_obj.select_set(True)
    bpy.ops.object.join()

    # Smooth shading and final orientation
    cap_obj.location = (0, 0, 0)
    for poly in cap_obj.data.polygons:
        poly.use_smooth = True

if __name__ == "__main__":
    clear_scene()
    create_mushroom()
