"""Curated course fixture: geometry-derived face anchors, no runtime AI."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

PART_PARAMS = {'seat': {'width': 1.0, 'scale': 1.0}}
args = sys.argv[sys.argv.index('--') + 1:]
width, broken, destination = float(args[0]), args[1] == '1', Path(args[2])
PART_PARAMS['seat']['width'] = width
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
parts = {}
def box(name, size, location, color):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj['treestruct3d_part_id'] = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (*color, 1)
    mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .65
    obj.data.materials.append(mat)
    parts[name] = obj
    return obj

def bounds(obj):
    vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return (Vector(tuple(min(v[i] for v in vertices) for i in range(3))),
            Vector(tuple(max(v[i] for v in vertices) for i in range(3))))

def face_anchor(obj, uv, top):
    lo, hi = bounds(obj)
    return Vector((lo.x+(hi.x-lo.x)*uv[0], lo.y+(hi.y-lo.y)*uv[1], hi.z if top else lo.z))

def surface_distance(obj, point):
    vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
    tree = BVHTree.FromPolygons(vertices, [list(p.vertices) for p in obj.data.polygons])
    return tree.find_nearest(point)[3]

seat = box('seat', (width, .85, .14), (0, 0, .77), (.21, .49, .55))
bpy.context.view_layer.update()
links = []
for name, uv in [('leg_front_left',(.10,.12)),('leg_front_right',(.90,.12)),('leg_back_left',(.10,.88)),('leg_back_right',(.90,.88)),('backrest',(.5,.90))]:
    is_back = name == 'backrest'
    child = box(name, (width-.12,.12,.62) if is_back else (.10,.10,.70), (0,0,0), (.74,.48,.24))
    bpy.context.view_layer.update()
    parent_anchor = face_anchor(seat, uv, is_back)
    child_uv = (.5,.5)
    child_anchor = face_anchor(child, child_uv, not is_back)
    child.location += parent_anchor - child_anchor
    if broken:
        # Reproduce stale child placement, plus visible separation for backrest.
        child.location.x += 0 if is_back else (uv[0]-.5)*(1-width)
        child.location.z += .16 if is_back else -.12
    bpy.context.view_layer.update()
    actual_child_anchor = face_anchor(child, child_uv, not is_back)
    pd, cd = surface_distance(seat,parent_anchor), surface_distance(child,actual_child_anchor)
    alignment = (parent_anchor-actual_child_anchor).length
    # Axis-aligned fixture: interval intersection measures exact box surface contact.
    a,b = bounds(seat); c,d = bounds(child)
    gaps = [max(a[i]-d[i],c[i]-b[i],0) for i in range(3)]
    contact_gap = sum(g*g for g in gaps)**.5
    on_mesh = pd < 1e-5 and cd < 1e-5
    aligned = alignment < 1e-5
    contact = contact_gap < 1e-5
    links.append(dict(parent='seat',child=name,parent_anchor=list(parent_anchor),child_anchor=list(actual_child_anchor),anchor_on_mesh=on_mesh,alignment_error=alignment,contact_gap=contact_gap,contact=contact,passed=on_mesh and aligned and contact))
destination.mkdir(parents=True,exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(destination/'chair.glb'),export_format='GLB',export_extras=True)
(destination/'validation.json').write_text(json.dumps(dict(width=width,broken=broken,geometry_changed=abs(width-1)>1e-5,seat_bounds=[list(v) for v in bounds(seat)],parts=list(parts),links=links),indent=2))
