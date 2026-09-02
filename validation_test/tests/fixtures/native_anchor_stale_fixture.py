import bpy
from mathutils import Matrix, Vector


PART_PARAMS = {
    "root": {"scale": 1.0},
    "leaf": {"scale": 1.0},
}


def make_box(part_id, length):
    vertices = [
        (x, y, z)
        for x in (0.0, length)
        for y in (-0.25, 0.25)
        for z in (-0.25, 0.25)
    ]
    faces = [
        (0, 1, 3, 2),
        (4, 6, 7, 5),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 2, 6, 4),
        (1, 5, 7, 3),
    ]
    mesh = bpy.data.meshes.new(f"{part_id}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(part_id, mesh)
    obj["treestruct3d_part_id"] = part_id
    bpy.context.scene.collection.objects.link(obj)
    return obj


def local_anchor_world(obj, local_anchor):
    return obj.matrix_world @ Vector(local_anchor)


def attach_child_to_parent_at_shared_anchor(
    parent_obj, child_obj, parent_anchor_local, child_anchor_local
):
    parent_anchor_world = local_anchor_world(parent_obj, parent_anchor_local)
    child_anchor_world = local_anchor_world(child_obj, child_anchor_local)
    child_obj.matrix_world = Matrix.Translation(
        parent_anchor_world - child_anchor_world
    ) @ child_obj.matrix_world
    aligned_child_world = child_obj.matrix_world.copy()
    child_obj.parent = parent_obj
    child_obj.matrix_world = aligned_child_world


root = make_box("root", float(PART_PARAMS["root"]["scale"]))
leaf = make_box("leaf", 0.5 * float(PART_PARAMS["leaf"]["scale"]))
# Deliberate bug: the root endpoint remains at its scale-1 coordinate.
root_anchor = Vector((1.0, 0.25, 0.25))
leaf_anchor = Vector((0.0, 0.25, 0.25))
attach_child_to_parent_at_shared_anchor(root, leaf, root_anchor, leaf_anchor)
