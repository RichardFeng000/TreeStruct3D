import ast
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


ALGORITHM_DIR = Path(__file__).resolve().parents[1] / "algorithm"
sys.path.insert(0, str(ALGORITHM_DIR))
sys.path.insert(0, str(ALGORITHM_DIR / "runtime"))

import blender_probe  # noqa: E402
from code_structure_tree import SourceStructure  # noqa: E402


class ValidatorRegressionTest(unittest.TestCase):
    def test_structure_omits_helper_formals_and_temporary_objects(self):
        source = '''
def attach_child_to_parent_at_shared_anchor(parent_obj, child_obj, parent_anchor, child_anchor):
    child_obj.parent = parent_obj

def combine_temps_as_part(part_id, temp_objs, material, parent_obj, primary_anchor):
    obj = create_mesh(label=part_id)
    attach_child_to_parent_at_shared_anchor(parent_obj, obj, primary_anchor, (0, 0, 0))
    return obj

def main():
    main_obj = create_mesh(label="main_stem")
    tmp = create_mesh(label="_tmp_offshoot")
    attach_child_to_parent_at_shared_anchor(main_obj, tmp, (0, 0, 0), (0, 0, 0))
    combine_temps_as_part("slim_offshoot", [tmp], None, main_obj, (0, 0, 0))
'''
        tree = ast.parse(source)
        structure = SourceStructure(Path("branch_fixture.py"), source, tree)
        structure.analyze()

        pairs = {(edge.parent, edge.child) for edge in structure.part_edges}
        self.assertEqual(pairs, {("main_stem", "slim_offshoot")})
        self.assertFalse(
            {"tmp", "_tmp_offshoot", "parent_obj", "obj", "{part_id}"}
            & structure.part_nodes
        )

    @staticmethod
    def _mesh(component_sizes_and_areas):
        vertices = []
        edges = []
        polygons = []
        offset = 0
        for size, area in component_sizes_and_areas:
            vertices.extend(SimpleNamespace(index=index) for index in range(offset, offset + size))
            edges.extend(
                SimpleNamespace(vertices=(index, index + 1))
                for index in range(offset, offset + size - 1)
            )
            polygons.append(
                SimpleNamespace(vertices=tuple(range(offset, offset + size)), area=area)
            )
            offset += size
        return SimpleNamespace(vertices=vertices, edges=edges, polygons=polygons)

    def test_tiny_disconnected_anchor_patch_is_not_eligible(self):
        mesh = self._mesh([(8, 6.0), (4, 0.01)])
        self.assertEqual(
            blender_probe._substantial_vertex_indices(mesh),
            set(range(8)),
        )

    def test_repeated_substantial_components_remain_eligible(self):
        mesh = self._mesh([(8, 6.0), (8, 5.5)])
        self.assertEqual(
            blender_probe._substantial_vertex_indices(mesh),
            set(range(16)),
        )


if __name__ == "__main__":
    unittest.main()
