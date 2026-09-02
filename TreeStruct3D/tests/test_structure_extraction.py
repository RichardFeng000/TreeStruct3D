import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import extract_structure
import generate_3d
from treestruct3d.structure_extraction import (
    SCHEMA_VERSION,
    blueprint_markdown,
    extract_json_object,
    validate_blueprint,
)
from treestruct3d.visual_critique import build_critique_user_content


def valid_blueprint():
    return {
        "schema_version": SCHEMA_VERSION,
        "object_name": "neutral assembly",
        "assembly_intent": "single_connected_assembly",
        "coordinate_frame": {
            "up_axis": "+Z",
            "front_axis": "+Y",
            "origin_rule": "root center on the ground plane",
        },
        "root_part_id": "body",
        "parts": [
            {
                "id": "body",
                "name": "Body",
                "role": "root",
                "parent_id": None,
                "quantity": 1,
                "importance": "primary",
                "geometry_summary": "central support volume",
            },
            {
                "id": "appendage",
                "name": "Appendage",
                "role": "attached",
                "parent_id": "body",
                "quantity": 2,
                "importance": "secondary",
                "geometry_summary": "paired tapered appendages",
            },
        ],
        "attachments": [
            {
                "id": "body_to_appendage",
                "parent_part_id": "body",
                "child_part_id": "appendage",
                "connection_type": "shared_anchor",
                "parent_anchor": {
                    "region": "paired side sockets",
                    "position_rule": "derive from current body side surface",
                    "orientation_rule": "outward side normal",
                },
                "child_anchor": {
                    "region": "proximal end",
                    "position_rule": "derive from current appendage base",
                    "orientation_rule": "axis points opposite the parent normal",
                },
                "placement_rule": "align each proximal frame to its side socket",
                "contact_required": True,
                "shared_anchor_required": True,
                "shared_anchor_id": "body_appendage_socket",
                "alignment_invariant": "world(parent_anchor) == world(child_anchor)",
                "recompute_rule": (
                    "derive both anchors from current geometry after parameter "
                    "changes, then realign before parenting"
                ),
                "confidence": 0.95,
            }
        ],
        "symmetry_and_repetition": [
            {"part_ids": ["appendage"], "rule": "mirror across the center plane"}
        ],
        "global_constraints": ["appendages remain attached when body size changes"],
        "floating_part_risks": [
            {
                "part_ids": ["appendage"],
                "risk": "fixed world offsets can detach the appendages",
                "required_fix": "recompute paired body-side anchors",
            }
        ],
        "uncertainties": [],
    }


class StructureExtractionTest(unittest.TestCase):
    def test_valid_connected_blueprint(self):
        blueprint = valid_blueprint()
        self.assertEqual(validate_blueprint(blueprint), [])

    def test_prerelease_blueprint_schema_remains_readable(self):
        blueprint = valid_blueprint()
        blueprint["schema_version"] = "stage7-structure-blueprint/v2"
        self.assertEqual(validate_blueprint(blueprint), [])

    def test_non_root_without_attachment_is_rejected(self):
        blueprint = valid_blueprint()
        blueprint["attachments"] = []
        errors = validate_blueprint(blueprint)
        self.assertTrue(
            any("exactly one attachment" in error for error in errors),
            errors,
        )

    def test_required_shared_anchor_contract_is_enforced(self):
        blueprint = valid_blueprint()
        attachment = blueprint["attachments"][0]
        for field in ("shared_anchor_id", "alignment_invariant", "recompute_rule"):
            broken = json.loads(json.dumps(blueprint))
            broken["attachments"][0].pop(field)
            errors = validate_blueprint(broken)
            self.assertTrue(any(field in error for error in errors), errors)

    def test_contact_and_shared_anchor_flags_must_agree(self):
        blueprint = valid_blueprint()
        attachment = blueprint["attachments"][0]
        attachment["contact_required"] = True
        attachment["shared_anchor_required"] = False
        errors = validate_blueprint(blueprint)
        self.assertTrue(
            any("contact_required" in error for error in errors),
            errors,
        )

    def test_duplicate_parent_attachments_are_rejected(self):
        blueprint = valid_blueprint()
        duplicate = json.loads(json.dumps(blueprint["attachments"][0]))
        duplicate["id"] = "second_parent_to_appendage"
        duplicate["shared_anchor_id"] = "second_parent_appendage_socket"
        blueprint["attachments"].append(duplicate)
        errors = validate_blueprint(blueprint)
        self.assertTrue(any("exactly one attachment" in error for error in errors), errors)

    def test_parent_cycle_is_rejected(self):
        blueprint = valid_blueprint()
        blueprint["parts"][0]["parent_id"] = "appendage"
        errors = validate_blueprint(blueprint)
        self.assertTrue(any("root part parent_id must be null" in error for error in errors))

    def test_json_fence_is_tolerated_but_trailing_prose_is_not(self):
        payload = json.dumps(valid_blueprint())
        parsed = extract_json_object(f"```json\n{payload}\n```")
        self.assertEqual(parsed["root_part_id"], "body")
        with self.assertRaises(ValueError):
            extract_json_object(payload + "\nextra explanation")

    def test_markdown_exposes_tree_and_floating_risk(self):
        rendered = blueprint_markdown(valid_blueprint())
        self.assertIn("`body` → `appendage`", rendered)
        self.assertIn("悬浮风险", rendered)

    def test_valid_extraction_loads_as_generation_user_context(self):
        blueprint = valid_blueprint()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            instance_dir = root / "Example_seed0"
            instance_dir.mkdir()
            path = instance_dir / "structure.json"
            path.write_text(json.dumps(blueprint), encoding="utf-8")
            loaded, loaded_path = generate_3d.load_structure_context(
                root,
                "Example_seed0",
            )
        user_prompt = generate_3d.compose_generation_user_prompt(
            "An example object.",
            loaded,
        )
        self.assertEqual(loaded_path, path)
        self.assertIn("<object_description>", user_prompt)
        self.assertIn("An example object.", user_prompt)
        self.assertIn("<structure_blueprint>", user_prompt)
        self.assertIn('"root": "body"', user_prompt)
        self.assertIn("shared_anchor_implementation_contract", user_prompt)
        self.assertIn("attach_child_to_parent_at_shared_anchor", user_prompt)
        self.assertIn("parent_anchor_world - child_anchor_world", user_prompt)
        self.assertIn("Do not expose planning", user_prompt)
        self.assertIn("Start immediately with valid Blender Python", user_prompt)
        self.assertIn("visual_fidelity_contract", user_prompt)
        self.assertIn("never return default white", user_prompt)
        self.assertIn("build every integrated feature inside its declared owner", user_prompt)
        self.assertIn("<native_part_parameter_contract>", user_prompt)
        self.assertIn("PART_PARAMS", user_prompt)
        self.assertIn('obj["treestruct3d_part_id"]', user_prompt)
        self.assertIn("rebuild that geometry", user_prompt)
        self.assertNotIn('"confidence":', user_prompt)
        self.assertNotIn('"floating_part_risks":', user_prompt)

    def test_extraction_prompt_requires_world_equal_anchor_contract(self):
        prompt = extract_structure.DEFAULT_EXTRACTION_PROMPT.read_text(
            encoding="utf-8"
        )
        self.assertIn("treestruct3d.structure-blueprint/v2", prompt)
        self.assertIn('"shared_anchor_id"', prompt)
        self.assertIn('"alignment_invariant"', prompt)
        self.assertIn('"recompute_rule"', prompt)
        self.assertIn("world(parent_anchor) == world(child_anchor)", prompt)
        self.assertIn("independently placed or independently parameterized", prompt)
        self.assertIn("full category-general authority", prompt)
        self.assertIn("Phase A — Visual and parametric decomposition", prompt)
        self.assertIn("Phase B — Freeze the decomposition", prompt)
        self.assertIn(
            "Phase C — Parent and shared-anchor annotation",
            prompt,
        )
        self.assertIn('"representation_reason"', prompt)
        self.assertIn('"integrated_features"', prompt)
        self.assertIn("face-connected to the part geometry", prompt)
        self.assertIn("real part surfaces must also touch or overlap slightly", prompt)
        self.assertIn("Do not create detached discs", prompt)
        self.assertIn("no visible gap", prompt)
        for category_specific_word in ("chameleon", "torso", "foot", "toe", "pupil"):
            self.assertNotIn(category_specific_word, prompt.lower())

    def test_neutral_prompt_pattern_is_recognized_as_authored_anchor(self):
        contract = generate_3d.SHARED_ANCHOR_IMPLEMENTATION_CONTRACT
        code = "from mathutils" + contract.split("from mathutils", 1)[1].split(
            "\n\n4.", 1
        )[0]
        tree = ast.parse(code)
        probe_path = (
            Path(__file__).resolve().parents[2]
            / "visual_validation"
            / "algorithm"
            / "runtime"
            / "blender_probe.py"
        )
        spec = importlib.util.spec_from_file_location(
            "treestruct3d_test_probe", probe_path
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        attachment = module._attachment_specs(tree)[
            "attach_child_to_parent_at_shared_anchor"
        ]
        self.assertTrue(attachment["authored_anchor"])
        self.assertTrue(attachment["code_directed"])

    def test_structural_repair_repeats_the_same_anchor_contract(self):
        feedback = generate_3d.build_structure_feedback_prompt(
            original_prompt="neutral object",
            previous_code="print('old')",
            score={"score": 0, "issues": []},
            attempt_num=1,
            max_attempts=2,
        )
        self.assertIn("attach_child_to_parent_at_shared_anchor", feedback)
        self.assertIn("Parent size changes", feedback)
        self.assertIn("Do not fake evidence", feedback)

    def test_extraction_is_stored_inside_prefixed_seed(self):
        root = Path("/tmp/treestruct3d_outputs")
        self.assertEqual(
            extract_structure.extraction_output_dir(
                root,
                "Example_seed0",
                "kimi_k3_",
                "(1)",
            ),
            root / "kimi_k3_Example_seed0(1)" / "structure_extraction",
        )

    def test_runner_loads_structure_from_prefixed_seed(self):
        blueprint = valid_blueprint()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            extraction_dir = (
                root / "kimi_k3_Example_seed0" / "structure_extraction"
            )
            extraction_dir.mkdir(parents=True)
            path = extraction_dir / "structure.json"
            path.write_text(json.dumps(blueprint), encoding="utf-8")
            loaded, loaded_path = generate_3d.load_structure_context(
                root,
                "Example_seed0",
                "kimi_k3_Example_seed0",
            )
        self.assertEqual(loaded_path, path)
        self.assertEqual(loaded["root_part_id"], "body")

    def test_invalid_extraction_is_blocked_before_generation(self):
        blueprint = valid_blueprint()
        blueprint["attachments"] = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            instance_dir = root / "Example_seed0"
            instance_dir.mkdir()
            (instance_dir / "structure.json").write_text(
                json.dumps(blueprint),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                generate_3d.load_structure_context(root, "Example_seed0")

    def test_visual_baseline_images_precede_current_renders(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = root / "baseline"
            current = root / "current"
            baseline.mkdir()
            current.mkdir()
            for directory, marker in ((baseline, b"baseline"), (current, b"current")):
                (directory / "Image_005.png").write_bytes(marker)
            content = build_critique_user_content(
                original_user_content="neutral object",
                prev_code="print('ok')",
                render_dir=current,
                iter_num=1,
                max_iter=1,
                baseline_render_dir=baseline,
            )
        self.assertIn("VISUAL QUALITY BASELINE", content[0]["text"])
        self.assertEqual(content[1]["name"], "Baseline_Image_005.png")
        self.assertEqual(content[2]["name"], "Image_005.png")


if __name__ == "__main__":
    unittest.main()
