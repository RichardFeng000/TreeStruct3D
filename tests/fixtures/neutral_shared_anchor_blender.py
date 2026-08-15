import bpy
from mathutils import Matrix, Vector


bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def subdivide_surface_once(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.subdivide(number_cuts=1)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)


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
    child_anchor_world = local_anchor_world(child_obj, child_anchor_local)
    assert (parent_anchor_world - child_anchor_world).length <= 1e-5


bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 0.0, 0.0))
support = bpy.context.object
support.name = "Support"
subdivide_surface_once(support)

bpy.ops.mesh.primitive_cube_add(size=1.0, location=(3.0, 0.0, 0.0))
appendage = bpy.context.object
appendage.name = "Appendage"
subdivide_surface_once(appendage)

support_socket_local = Vector((1.0, 0.0, 0.0))
appendage_base_local = Vector((-0.5, 0.0, 0.0))
attach_child_to_parent_at_shared_anchor(
    parent_obj=support,
    child_obj=appendage,
    parent_anchor_local=support_socket_local,
    child_anchor_local=appendage_base_local,
)
