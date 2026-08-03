import bpy
import bmesh
import math
import random
from mathutils import Vector

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

def create_petal(name, material, size=1.0):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    # Create a petal along the Z axis (extending upwards from 0,0,0)
    res_u, res_v = 10, 15
    verts = []
    for v in range(res_v):
        row = []
        z = (v / (res_v - 1)) * size
        # Width profile: narrow at base, wide middle, tapered tip
        t = v / (res_v - 1)
        w = math.sin(t * math.pi) * 0.3 * size
        for u in range(res_u):
            x = ((u / (res_u - 1)) * 2.0 - 1.0) * w
            # Add a bit of curvature/cup shape to the petal itself
            y = -(x**2) * 2.0 + t * 0.2
            row.append(bm.verts.new(Vector((x, y, z))))
        verts.append(row)

    for v in range(res_v - 1):
        for u in range(res_u - 1):
            try:
                bm.faces.new((verts[v][u], verts[v+1][u], verts[v+1][u+1], verts[v][u+1]))
            except ValueError: pass

    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(material)
    
    # Smooth shading
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    return obj

def create_stamen(brown_mat):
    # Filament
    bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=0.4)
    filament = bpy.context.active_object
    filament.location.z = 0.2
    
    # Anther (tip)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.04, location=(0, 0, 0.4))
    anther = bpy.context.active_object
    
    filament.select_set(True)
    bpy.context.view_layer.objects.active = anther
    bpy.ops.object.join()
    
    anther.data.materials.append(brown_mat)
    return anther

def create_sepal(green_mat):
    mesh = bpy.data.meshes.new("Sepal")
    obj = bpy.data.objects.new("Sepal", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    res = 6
    verts = []
    for v in range(res):
        row = []
        z = (v / (res - 1)) * 0.4
        w = math.sin((v / (res-1)) * math.pi) * 0.15
        for u in range(res):
            x = ((u / (res - 1)) * 2.0 - 1.0) * w
            y = z * 0.5 # slope it slightly
            row.append(bm.verts.new(Vector((x, y, z))))
        verts.append(row)
    for v in range(res - 1):
        for u in range(res - 1):
            try: bm.faces.new((verts[v][u], verts[v+1][u], verts[v+1][u+1], verts[v][u+1]))
            except ValueError: pass
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(green_mat)
    return obj

def main():
    clear_scene()
    
    blue_mat = create_material("Blue", (0.4, 0.7, 1.0, 1.0))
    brown_mat = create_material("Brown", (0.3, 0.2, 0.1, 1.0))
    green_mat = create_material("Green", (0.05, 0.2, 0.05, 1.0))
    
    # Layer configuration: [count, tilt_deg, scale]
    layers = [
        {"count": 6, "tilt": 15, "scale": 0.7}, # Inner
        {"count": 8, "tilt": 35, "scale": 1.0}, # Middle
        {"count": 10, "tilt": 55, "scale": 1.3} # Outer
    ]
    
    for i, layer in enumerate(layers):
        for j in range(layer["count"]):
            p = create_petal(f"Petal_{i}_{j}", blue_mat, size=layer["scale"])
            angle = (2 * math.pi / layer["count"]) * j
            # Rotate petal: first around Z to position it, then X to tilt outwards
            p.rotation_euler[2] = angle
            p.rotation_euler[1] = math.radians(layer["tilt"])
            # Lift layers slightly to prevent absolute clumping at the base
            p.location.z = -0.1 * i

    # Stamens in center
    for _ in range(15):
        s = create_stamen(brown_mat)
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0, 0.12)
        s.location.x = math.cos(angle) * dist
        s.location.y = math.sin(angle) * dist
        s.rotation_euler[0] = random.uniform(-0.3, 0.3)
        s.rotation_euler[1] = random.uniform(-0.3, 0.3)

    # Sepals at base
    sepal_count = 6
    for i in range(sepal_count):
        sep = create_sepal(green_mat)
        angle = (2 * math.pi / sepal_count) * i
        sep.location.z = -0.1
        sep.rotation_euler[2] = angle
        # Tilt sepals downwards and outwards
        sep.rotation_euler[1] = math.radians(130)

if __name__ == "__main__":
    main()
