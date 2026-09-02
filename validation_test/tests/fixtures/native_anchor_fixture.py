import bpy
from mathutils import Matrix, Vector


PART_PARAMS = {
    "root": {"scale": 1.0},
    "leaf": {"scale": 1.0},
}


def make_box(part_id, length, half_width=0.25):
    vertices = [
        (x, y, z)
        for x in (0.0, length)
        for y in (-half_width, half_width)
        for z in (-half_width, half_width)
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
    obj["stage7_part_id"] = part_id
    bpy.context.scene.collection.objects.link(obj)
    return obj


def local_anchor_world(obj, local_anchor):
    return obj.matrix_world @ Vector(local_anchor)


def attach_child_to_parent_at_shared_anchor(
    parent_obj, child_obj, parent_anchor_local, child_anchor_local
):
    parent_anchor_world = local_anchor_world(parent_obj, parent_anchor_local)
    child_anchor_world = local_anchor_world(child_obj, child_anchor_local)
    correction = parent_anchor_world - child_anchor_world
    child_obj.matrix_world = Matrix.Translation(correction) @ child_obj.matrix_world
    aligned_child_world = child_obj.matrix_world.copy()
    child_obj.parent = parent_obj
    child_obj.matrix_world = aligned_child_world
    assert (
        local_anchor_world(parent_obj, parent_anchor_local)
        - local_anchor_world(child_obj, child_anchor_local)
    ).length <= 1e-5


root_scale = float(PART_PARAMS["root"]["scale"])
leaf_scale = float(PART_PARAMS["leaf"]["scale"])
root = make_box("root", root_scale, 0.25 * root_scale)
leaf = make_box("leaf", 0.5 * leaf_scale, 0.2 * leaf_scale)
root_anchor = Vector((root_scale, 0.25 * root_scale, 0.25 * root_scale))
leaf_anchor = Vector((0.0, 0.2 * leaf_scale, 0.2 * leaf_scale))
attach_child_to_parent_at_shared_anchor(root, leaf, root_anchor, leaf_anchor)
