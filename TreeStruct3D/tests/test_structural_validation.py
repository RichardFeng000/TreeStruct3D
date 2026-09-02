from pathlib import Path
import tempfile
import unittest

from core.structural_validation import (
    apply_parameter_invariance_gate,
    native_part_parameter_ids,
    score_structure_report,
)


def valid_two_part_report():
    return {
        "status": "ok",
        "nodes": [
            {"id": "base", "dimensions": [1.0, 1.0, 1.0]},
            {"id": "child", "dimensions": [0.5, 0.5, 0.5]},
        ],
        "edges": [
            {
                "node_a": "base",
                "node_b": "child",
                "relation": "DIRECTED_CODE",
                "parent": "base",
                "child": "child",
                "contact": True,
                "geometric_anchor_aligned": True,
                "shared_anchor": True,
                "shared_anchor_evidence": "authored_anchor_pair",
                "anchor_gap": 0.0,
                "anchor_tolerance": 0.01,
                "declared_directions": [
                    {"parent": "base", "child": "child", "line": 10}
                ],
            }
        ],
    }


class StructuralValidationTest(unittest.TestCase):
    def test_declared_single_part_without_attachments_passes(self):
        report = {
            "status": "ok",
            "nodes": [{"id": "conch_shell", "dimensions": [1.0, 1.0, 1.0]}],
            "edges": [],
        }
        score = score_structure_report(
            report,
            expected_part_ids=["conch_shell"],
            expected_part_count=1,
            expected_attachment_count=0,
        )
        self.assertTrue(score["passed"])
        self.assertEqual(score["score"], 100.0)
        self.assertEqual(score["issues"], [])

    def test_single_part_still_fails_without_matching_blueprint(self):
        report = {
            "status": "ok",
            "nodes": [{"id": "only_part", "dimensions": [1.0, 1.0, 1.0]}],
            "edges": [],
        }
        score = score_structure_report(report)
        self.assertFalse(score["passed"])
        self.assertIn(
            "INSUFFICIENT_PARTS",
            {issue["code"] for issue in score["issues"]},
        )

    def test_blueprint_scoring_ignores_nonsemantic_helper_meshes(self):
        score = score_structure_report(
            valid_two_part_report(),
            expected_part_ids=["base"],
            expected_part_count=1,
            expected_attachment_count=0,
        )
        self.assertTrue(score["passed"])
        self.assertEqual(score["summary"]["nodes"], 1)

    def test_missing_blueprint_part_is_reported(self):
        score = score_structure_report(
            valid_two_part_report(),
            expected_part_ids=["base", "missing_part"],
            expected_part_count=2,
            expected_attachment_count=1,
        )
        self.assertFalse(score["passed"])
        self.assertIn(
            "EXPECTED_PARTS_MISSING",
            {issue["code"] for issue in score["issues"]},
        )

    def test_authored_shared_anchor_passes(self):
        score = score_structure_report(valid_two_part_report())
        self.assertTrue(score["passed"])
        self.assertEqual(score["score"], 100.0)
        self.assertEqual(score["summary"]["confirmed_shared_anchors"], 1)
        self.assertEqual(score["issues"], [])

    def test_transitive_runtime_contact_is_not_a_second_primary_parent(self):
        report = valid_two_part_report()
        report["nodes"].append({"id": "grandchild", "dimensions": [0.2, 0.2, 0.2]})
        report["edges"].append({
            "node_a": "base",
            "node_b": "grandchild",
            "relation": "DIRECTED",
            "parent": "base",
            "child": "grandchild",
            "contact": True,
            "geometric_anchor_aligned": True,
            "shared_anchor": False,
            "shared_anchor_evidence": None,
            "declared_directions": [],
        })
        report["edges"].append({
            "node_a": "child",
            "node_b": "grandchild",
            "relation": "DIRECTED_CODE",
            "parent": "child",
            "child": "grandchild",
            "contact": True,
            "geometric_anchor_aligned": True,
            "shared_anchor": True,
            "shared_anchor_evidence": "authored_anchor_pair",
            "declared_directions": [
                {"parent": "child", "child": "grandchild", "line": 20}
            ],
        })
        score = score_structure_report(
            report,
            expected_part_ids=["base", "child", "grandchild"],
            expected_attachment_pairs=[("base", "child"), ("child", "grandchild")],
            expected_part_count=3,
            expected_attachment_count=2,
        )
        self.assertTrue(score["passed"])
        self.assertEqual(score["score"], 100.0)
        self.assertNotIn(
            "MULTIPLE_PRIMARY_PARENTS",
            {issue["code"] for issue in score["issues"]},
        )

    def test_contact_without_authored_anchor_fails(self):
        report = valid_two_part_report()
        edge = report["edges"][0]
        edge["shared_anchor"] = False
        edge["shared_anchor_evidence"] = None
        score = score_structure_report(report)
        self.assertFalse(score["passed"])
        self.assertIn(
            "UNVERIFIED_SHARED_ANCHOR",
            {issue["code"] for issue in score["issues"]},
        )

    def test_multiple_roots_are_reported(self):
        report = {
            "status": "ok",
            "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
            "edges": [],
        }
        score = score_structure_report(report)
        codes = {issue["code"] for issue in score["issues"]}
        self.assertFalse(score["passed"])
        self.assertIn("NO_DIRECTED_RELATIONS", codes)
        self.assertIn("MULTIPLE_ROOTS", codes)

    def test_probe_error_is_a_zero_score_failure(self):
        score = score_structure_report(
            {"status": "error", "error": "Blender execution failed"}
        )
        self.assertFalse(score["passed"])
        self.assertEqual(score["score"], 0.0)
        self.assertEqual(score["issues"][0]["code"], "PROBE_FAILED")

    def test_literal_native_part_parameter_ids_are_discovered(self):
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "model.py"
            script.write_text(
                'PART_PARAMS = {"root": {"scale": 1.0}, "leaf": {"scale": 1}}\n',
                encoding="utf-8",
            )
            self.assertEqual(native_part_parameter_ids(script), ["leaf", "root"])

    def test_parent_and_child_scale_variants_must_both_pass(self):
        default = valid_two_part_report()
        base_variant = valid_two_part_report()
        base_variant["nodes"][0]["dimensions"] = [1.35, 1.35, 1.35]
        child_variant = valid_two_part_report()
        child_variant["nodes"][1]["dimensions"] = [0.675, 0.675, 0.675]
        gated = apply_parameter_invariance_gate(
            score_structure_report(default),
            default,
            {"base": base_variant, "child": child_variant},
        )
        self.assertTrue(gated["passed"])
        self.assertEqual(gated["parameter_invariance"]["passed_parts"], 2)

        child_variant["nodes"][1]["dimensions"] = [0.5, 0.5, 0.5]
        failed = apply_parameter_invariance_gate(
            score_structure_report(default),
            default,
            {"base": base_variant, "child": child_variant},
        )
        self.assertFalse(failed["passed"])
        self.assertIn(
            "NATIVE_PART_SCALE_UNUSED",
            {issue["code"] for issue in failed["issues"]},
        )

    def test_repeated_group_shape_change_passes_when_union_bounds_stay_fixed(self):
        default = valid_two_part_report()
        default["nodes"][1].update({
            "center": [0.0, 0.0, 0.0],
            "vertex_count": 4,
            "samples": [
                [-1.0, 0.0, 0.0],
                [-0.5, 0.0, 0.0],
                [0.5, 0.0, 0.0],
                [1.0, 0.0, 0.0],
            ],
        })
        child_variant = valid_two_part_report()
        child_variant["nodes"][1].update({
            "center": [0.0, 0.0, 0.0],
            "vertex_count": 4,
            "samples": [
                [-1.0, 0.0, 0.0],
                [-0.7, 0.0, 0.0],
                [0.7, 0.0, 0.0],
                [1.0, 0.0, 0.0],
            ],
        })
        gated = apply_parameter_invariance_gate(
            score_structure_report(default),
            default,
            {"child": child_variant},
        )
        self.assertTrue(gated["passed"])
        result = gated["parameter_invariance"]["results"][0]
        self.assertTrue(result["geometry_changed"])
        self.assertFalse(result["dimensions_changed"])
        self.assertTrue(result["shape_samples_changed"])


if __name__ == "__main__":
    unittest.main()
