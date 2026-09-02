from pathlib import Path
import copy
import sys
import tempfile
import unittest


ALGORITHM_DIR = Path(__file__).resolve().parents[1] / "algorithm"
sys.path.insert(0, str(ALGORITHM_DIR))

import model_playground  # noqa: E402


class NativePartParameterTest(unittest.TestCase):
    def test_literal_protocol_creates_native_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "model.py"
            source.write_text(
                "PART_PARAMS = {\n"
                '    "root": {"scale": 1.0},\n'
                '    "leaf": {"scale": 1.0, "segments": 8},\n'
                "}\n",
                encoding="utf-8",
            )
            params = model_playground._native_part_params(source)
            controls = model_playground._native_part_controls(source)

        self.assertEqual(sorted(params), ["leaf", "root"])
        ids = {control["id"] for control in controls}
        self.assertIn("part_param|root|scale", ids)
        self.assertIn("part_param|leaf|segments", ids)
        scale = next(
            control for control in controls if control["id"] == "part_param|root|scale"
        )
        self.assertEqual(scale["parameter_mode"], "native_rebuild")
        self.assertEqual(scale["visibility_id"], "part_object_visible|root|root")

    def test_parameter_invariance_downgrades_failed_shared_edge(self):
        view = {
            "nodes": [
                {"id": "root", "dimensions": [1.0, 1.0, 1.0]},
                {"id": "leaf", "dimensions": [0.5, 0.5, 0.5]},
            ],
            "edges": [
                {
                    "parent": "root",
                    "child": "leaf",
                    "relation": "DIRECTED",
                    "shared_anchor": True,
                }
            ],
            "summary": {"shared_anchor_edges": 1},
        }
        variants = {
            "root": {
                "nodes": [
                    {"id": "root", "dimensions": [1.35, 1.35, 1.35]},
                    {"id": "leaf", "dimensions": [0.5, 0.5, 0.5]},
                ],
                "edges": [
                    {"parent": "root", "child": "leaf", "shared_anchor": False}
                ],
            },
            "leaf": {
                "nodes": [
                    {"id": "root", "dimensions": [1.0, 1.0, 1.0]},
                    {"id": "leaf", "dimensions": [0.675, 0.675, 0.675]},
                ],
                "edges": [
                    {"parent": "root", "child": "leaf", "shared_anchor": True}
                ],
            },
        }
        result = model_playground.PlaygroundState._apply_native_parameter_invariance(
            view,
            variants,
        )
        edge = result["edges"][0]
        self.assertFalse(edge["shared_anchor"])
        self.assertTrue(edge["parameter_invariance_failed"])
        self.assertEqual(result["summary"]["shared_anchor_edges"], 0)

    def test_parameter_invariance_ignores_incidental_contact_edges(self):
        view = {
            "nodes": [
                {"id": "root", "dimensions": [1.0, 1.0, 1.0]},
                {"id": "leaf", "dimensions": [0.5, 0.5, 0.5]},
                {"id": "nearby", "dimensions": [0.4, 0.4, 0.4]},
            ],
            "edges": [
                {
                    "parent": "root",
                    "child": "leaf",
                    "relation": "DIRECTED",
                    "shared_anchor": True,
                },
                {
                    "parent": "leaf",
                    "child": "nearby",
                    "relation": "UNDIRECTED_CONTACT",
                    "shared_anchor": False,
                },
            ],
            "summary": {"shared_anchor_edges": 1},
        }
        variants = {
            "root": {
                "nodes": [
                    {"id": "root", "dimensions": [1.35, 1.35, 1.35]},
                    {"id": "leaf", "dimensions": [0.5, 0.5, 0.5]},
                ],
                "edges": [
                    {"parent": "root", "child": "leaf", "shared_anchor": True}
                ],
            },
            "leaf": {
                "nodes": [
                    {"id": "root", "dimensions": [1.0, 1.0, 1.0]},
                    {"id": "leaf", "dimensions": [0.675, 0.675, 0.675]},
                ],
                "edges": [
                    {"parent": "root", "child": "leaf", "shared_anchor": True}
                ],
            },
            "nearby": {
                "nodes": [
                    {"id": "nearby", "dimensions": [0.54, 0.54, 0.54]},
                ],
                "edges": [],
            },
        }

        result = model_playground.PlaygroundState._apply_native_parameter_invariance(
            view,
            variants,
        )

        self.assertTrue(result["edges"][0]["shared_anchor"])
        self.assertEqual(result["summary"]["shared_anchor_edges"], 1)
        nearby = next(
            item
            for item in result["parameter_invariance"]["results"]
            if item["part_id"] == "nearby"
        )
        self.assertTrue(nearby["passed"])
        self.assertEqual(nearby["affected_edges"], 0)

    def test_parameter_invariance_maps_repeated_instances_to_part_id(self):
        view = {
            "nodes": [
                {
                    "id": "root",
                    "part_id": "root",
                    "dimensions": [1.0, 1.0, 1.0],
                },
                {
                    "id": "leaf",
                    "part_id": "leaf",
                    "dimensions": [0.5, 0.5, 0.5],
                },
                {
                    "id": "leaf.001",
                    "part_id": "leaf",
                    "dimensions": [0.5, 0.5, 0.5],
                },
            ],
            "edges": [
                {
                    "parent": "root",
                    "child": child,
                    "relation": "DIRECTED",
                    "shared_anchor": True,
                }
                for child in ("leaf", "leaf.001")
            ],
            "summary": {"shared_anchor_edges": 2},
        }
        variants = {
            "root": {
                "nodes": [
                    {**node, "dimensions": [1.35, 1.35, 1.35]}
                    if node["id"] == "root"
                    else copy.deepcopy(node)
                    for node in view["nodes"]
                ],
                "edges": copy.deepcopy(view["edges"]),
            },
            "leaf": {
                "nodes": [
                    {**node, "dimensions": [0.675, 0.675, 0.675]}
                    if node["part_id"] == "leaf"
                    else copy.deepcopy(node)
                    for node in view["nodes"]
                ],
                "edges": copy.deepcopy(view["edges"]),
            },
        }

        result = model_playground.PlaygroundState._apply_native_parameter_invariance(
            view,
            variants,
        )

        self.assertEqual(result["summary"]["shared_anchor_edges"], 2)
        self.assertTrue(all(edge["shared_anchor"] for edge in result["edges"]))
        leaf = next(
            item
            for item in result["parameter_invariance"]["results"]
            if item["part_id"] == "leaf"
        )
        self.assertTrue(leaf["passed"])
        self.assertEqual(leaf["instances"], 2)


if __name__ == "__main__":
    unittest.main()
