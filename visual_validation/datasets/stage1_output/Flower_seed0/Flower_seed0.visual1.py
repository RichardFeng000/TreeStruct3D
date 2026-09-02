import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    return mat

def create_petal_mesh(name, material, scale=1.0, curvature=0.5):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Create a grid for the petal (tapered leaf shape)
    res_u, res_v = 8, 12
    verts = []
    for v in range(res_v):
        row = []
        # normalized coordinate from -1 to 1
        y = (v / (res_v - 1)) * 2.0 - 1.0 
        
        # Shape width: narrow at base (y=-1), wide in middle, rounded tip
        # Using a sine-like curve for the width profile
        w = math.sin((v / (res_v - 1)) * math.pi) * scale * 0.5
        
        for u in range(res_u):
            x = ((u / (res_u - 1)) * 2.0 - 1.0) * w
            
            # Curvature: petal bends upwards and inwards
            # z is the "up" direction of the petal itself before rotation
            z = -(x**2) * curvature + (y + 1.0)**2 * 0.2
            
            row.append(bm.verts.new(Vector((x, y * scale, z))))
        verts.append(row)

    for v in range(res_v - 1):
        for u in range(res_u - 1):
            try:
                bm.faces.new((verts[v][u], verts[v+1][u], verts[v+1][u+1], verts[v][u+1]))
            except ValueError:
                pass

    bm.to_mesh(mesh)
    bm.free()
    
    obj.data.materials.append(material)
    mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
    mod.levels = 2
    return obj

def build_stamen(brown_mat):
    # Create a combined mesh for stamen to avoid too many objects
    mesh = bpy.data.meshes.new("Stamen")
    obj = bpy.data.objects.new("Stamen", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Filament: simple cylinder-like extrusion
    # We'll just use primitive ops and join for simplicity in a helper
    bm.free() 
    
    # Using primitive helpers instead of BMesh for the stamen to ensure it looks solid
    bpy.ops.mesh.primitive_cylinder_add(radius=0.01, depth=0.4)
    filament = bpy.context.active_object
    
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03, location=(0, 0, 0.2))
    anther = bpy.context.active_object
    
    # Join them into one object
    filament.select_set(True)
    bpy.context.view_layer.objects.active = anther
    bpy.ops.object.join()
    
    anther.data.materials.append(brown_mat)
    return anther

def build_sepal(green_mat, angle):
    # Create a small leaf for the sepal
    mesh = bpy.data.meshes.new("Sepal")
    obj = bpy.data.objects.new("Sepal", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    res_u, res_v = 6, 8
    verts = []
    for v in range(res_v):
        row = []
        y = (v / (res_v - 1)) * 0.4
        w = math.sin((v / (res_v - 1)) * math.pi) * 0.2
        for u in range(res_u):
            x = ((u / (res_u - 1)) * 2.0 - 1.0) * w
            z = -(y**2) * 2.0 # Curves downwards
            row.append(bm.verts.new(Vector((x, y, z))))
        verts.append(row)

    for v in range(res_v - 1):
        for u in range(res_u - 1):
            try:
                bm.faces.new((verts[v][u], verts[v+1][u], verts[v+1][u+1], verts[v][u+1]))
            except ValueError:
                pass

    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(green_mat)
    return obj

def main():
    clear_scene()
    
    blue_mat = create_material("PetalBlue", (0.5, 0.8, 1.0, 1.0))
    brown_mat = create_material("StamenBrown", (0.4, 0.2, 0.1, 1.0))
    green_mat = create_material("SepalGreen", (0.1, 0.3, 0.1, 1.0))
    
    # --- Petals in layers for a bowl shape ---
    layers = [
        {"count": 6, "tilt": 15, "scale": 0.6, "z_off": 0.0},  # Inner
        {"count": 8, "tilt": 30, "scale": 0.9, "z_off": -0.1}, # Mid
        {"count": 10, "tilt": 50, "scale": 1.2, "z_off": -0.2} # Outer
    ]
    
    for i, layer in enumerate(layers):
        for j in range(layer["count"]):
            petal = create_petal_mesh(f"Petal_{i}_{j}", blue_mat, scale=layer["scale"])
            
            angle = (2 * math.pi / layer["count"]) * j
            # Rotate petal to face outwards
            petal.rotation_euler[2] = angle
            # Tilt the petal from the base to create the bowl
            petal.rotation_euler[1] = math.radians(layer["tilt"])
            # Position it slightly so they cluster at origin
            petal.location = (0, 0, layer["z_off"])

    # --- Stamens in center ---
    stamen_count = 20
    for i in range(stamen_count):
        s = build_stamen(brown_mat)
        angle = random.uniform(0, 2 * math.pi)
        radius = random.uniform(0, 0.15)
        s.location = (math.cos(angle) * radius, math.sin(angle) * radius, 0.1)
        # Tilt slightly
        s.rotation_euler[0] = random.uniform(-0.3, 0.3)
        s.rotation_euler[1] = random.uniform(-0.3, 0.3)

    # --- Sepals at base ---
    sepal_count = 6
    for i in range(sepal_count):
        angle = (2 * math.pi / sepal_count) * i
        sepal = build_sepal(green_mat, angle)
        # Position them around the bottom
        sepal.location = (0, 0, -0.3)
        sepal.rotation_euler[2] = angle
        sepal.rotation_euler[1] = math.radians(45) # Angle downwards/outwards

if __name__ == "__main__":
    main()
