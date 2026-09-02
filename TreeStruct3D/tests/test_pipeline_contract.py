from pathlib import Path
import tempfile
import unittest
from unittest import mock

import extract_structure
import generate_3d


ROOT = Path(__file__).resolve().parents[1]


class PipelineContractTest(unittest.TestCase):
    def test_default_config_uses_the_conventional_local_filename(self):
        self.assertEqual(
            generate_3d.DEFAULT_CONFIG,
            ROOT / "config.local.yaml",
        )
        self.assertEqual(extract_structure.DEFAULT_CONFIG, generate_3d.DEFAULT_CONFIG)

    def test_output_prefix_changes_only_output_instance_name(self):
        self.assertEqual(
            generate_3d.output_instance_name("Chameleon_seed0", "kimi_k3_"),
            "kimi_k3_Chameleon_seed0",
        )
        self.assertEqual(
            generate_3d.output_instance_name("Chameleon_seed0", ""),
            "Chameleon_seed0",
        )
        self.assertEqual(
            generate_3d.output_instance_name(
                "Chameleon_seed0",
                "kimi_k3_",
                "(1)",
            ),
            "kimi_k3_Chameleon_seed0(1)",
        )
        with self.assertRaises(ValueError):
            generate_3d.output_instance_name("Chameleon_seed0", "../unsafe/")
        with self.assertRaises(ValueError):
            generate_3d.output_instance_name("Chameleon_seed0", "", "../unsafe/")

    def test_rerun_preserves_structure_extraction_and_background_request_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = Path(temporary) / "kimi_k3_Example_seed0"
            extraction = out_dir / "structure_extraction"
            extraction.mkdir(parents=True)
            (extraction / "structure.json").write_text("{}", encoding="utf-8")
            (out_dir / "old.py").write_text("old", encoding="utf-8")
            background = out_dir / "response_initial_attempt1.background.json"
            background.write_text('{"response_id":"resp_test"}', encoding="utf-8")
            (out_dir / "renders").mkdir()
            (out_dir / "renders" / "old.png").write_bytes(b"old")
            generate_3d.clear_generation_artifacts(out_dir)
            self.assertTrue((extraction / "structure.json").is_file())
            self.assertTrue(background.is_file())
            self.assertFalse((out_dir / "old.py").exists())
            self.assertFalse((out_dir / "renders").exists())

    def test_render_attempt_archives_program_and_four_views(self):
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = Path(temporary) / "Example_seed0"
            renders = out_dir / "renders"
            renders.mkdir(parents=True)
            for frame in (5, 15, 25, 35):
                (renders / f"Image_{frame:03d}.png").write_bytes(b"png")
            script = out_dir / "Example_seed0.py"
            script.write_text("value = 1\n", encoding="utf-8")

            result = generate_3d.archive_render_attempt(
                out_dir,
                script,
                {"status": "OK", "n_views_rendered": 4},
            )

            snapshot = out_dir / "render_history" / result["render_snapshot"]
            self.assertEqual(len(list(snapshot.glob("Image_*.png"))), 4)
            self.assertEqual(
                (snapshot / "program.py").read_text(encoding="utf-8"),
                "value = 1\n",
            )

    def test_validation_turn_bundles_program_views_and_score(self):
        with tempfile.TemporaryDirectory() as temporary:
            out_dir = Path(temporary) / "Example_seed0"
            renders = out_dir / "renders"
            renders.mkdir(parents=True)
            for frame in (5, 15, 25, 35):
                (renders / f"Image_{frame:03d}.png").write_bytes(b"png")
            script = out_dir / "Example_seed0.py"
            script.write_text("value = 2\n", encoding="utf-8")
            raw = out_dir / "structural_probe_attempt1.raw.json"
            score = out_dir / "structural_score_attempt1.json"
            markdown = out_dir / "structural_score_attempt1.md"
            raw.write_text("{}\n", encoding="utf-8")
            score.write_text('{"passed": false}\n', encoding="utf-8")
            markdown.write_text("FAIL\n", encoding="utf-8")

            turn_dir = generate_3d.archive_validation_turn(
                out_dir=out_dir,
                script_path=script,
                attempt=1,
                score={"passed": False, "score": 55.0},
                raw_path=raw,
                score_path=score,
                markdown_path=markdown,
            )

            self.assertEqual(len(list((turn_dir / "renders").glob("Image_*.png"))), 4)
            self.assertTrue((turn_dir / "program.py").is_file())
            self.assertIn('"status": "FAIL"', (turn_dir / "turn_manifest.json").read_text())

    def test_generation_uses_only_original_blender_generation_system_prompt(self):
        self.assertEqual(
            generate_3d.DEFAULT_SYSTEM_PROMPT,
            ROOT / "prompts" / "blender_generation_system_prompt.txt",
        )
        source = (ROOT / "generate_3d.py").read_text(encoding="utf-8")
        self.assertNotIn("legacy_additional_prompt", source)
        self.assertNotIn("structure_blueprint_baseline_system_prompt", source)
        base_prompt = generate_3d.DEFAULT_SYSTEM_PROMPT.read_text(encoding="utf-8")
        self.assertEqual(
            generate_3d.sha256_text(base_prompt),
            "c2abed528a5271f887e1147f1509eb2988160e9775940c7bd013955f1f79b4b9",
        )

    def test_extraction_uses_the_active_structure_blueprint_prompt(self):
        self.assertEqual(
            extract_structure.DEFAULT_EXTRACTION_PROMPT,
            ROOT
            / "prompts"
            / "structure_blueprint_system_prompt.txt",
        )
        active_prompt = extract_structure.DEFAULT_EXTRACTION_PROMPT.read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            generate_3d.sha256_text(active_prompt),
            "dba1663b53ad93bab094faa3adb3c83501ae38eb06732f46c04f83c7b8e18afd",
        )
        baseline = ROOT / "prompts" / "structure_blueprint_baseline_system_prompt.txt"
        self.assertTrue(baseline.is_file())
        self.assertEqual(
            generate_3d.sha256_text(baseline.read_text(encoding="utf-8")),
            "4d769ebfde0eda792d21896e98bacbc1686ae398a4750dd9a34127bd3152e8c5",
        )
        source = (ROOT / "extract_structure.py").read_text(encoding="utf-8")
        self.assertNotIn("legacy_additional_prompt", source)
        self.assertNotIn("blender_generation_system_prompt", source)

    def test_runner_has_no_structgen_import_or_old_prompt(self):
        source = (ROOT / "generate_3d.py").read_text(encoding="utf-8")
        self.assertNotIn("from StructGen3D", source)
        self.assertNotIn("import StructGen3D", source)
        for old_prompt in (
            "stage5_full_constraints.txt",
            "stage6_connection_first_constraints.txt",
        ):
            self.assertNotIn(old_prompt, source)

    def test_model_can_be_overridden_without_changing_provider_config(self):
        parser_source = (ROOT / "generate_3d.py").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument(\n        "--model"', parser_source)
        self.assertIn('config["model"] = args.model', parser_source)

    def test_descriptive_cli_names_and_prerelease_aliases_match(self):
        with mock.patch(
            "sys.argv",
            [
                "generate_3d.py",
                "--api-timeout",
                "11",
                "--generation-retries",
                "4",
                "--request-delay",
                "0.5",
                "--validator-root",
                "/tmp/validator",
            ],
        ):
            current = generate_3d.parse_args()
        with mock.patch(
            "sys.argv",
            [
                "generate_3d.py",
                "--timeout",
                "11",
                "--retries",
                "4",
                "--sleep",
                "0.5",
                "--validation-test-root",
                "/tmp/validator",
            ],
        ):
            legacy = generate_3d.parse_args()
        self.assertEqual(current.timeout, legacy.timeout)
        self.assertEqual(current.retries, legacy.retries)
        self.assertEqual(current.sleep, legacy.sleep)
        self.assertEqual(current.validator_root, legacy.validator_root)

    def test_default_outputs_are_local_to_the_project(self):
        expected = ROOT / "outputs"
        self.assertEqual(generate_3d.DEFAULT_OUTPUT_DIR, expected)
        self.assertEqual(generate_3d.DEFAULT_STRUCTURE_CONTEXT_DIR, expected)
        self.assertEqual(extract_structure.DEFAULT_EXTRACTION_OUTPUT, expected)

    def test_structural_validator_uses_the_existing_sibling_checkout_by_default(self):
        self.assertEqual(
            generate_3d.DEFAULT_VALIDATOR_ROOT,
            ROOT.parent / "validation_test",
        )
        source = (ROOT / "generate_3d.py").read_text(encoding="utf-8")
        self.assertIn("validate_with_structure_repair", source)
        self.assertIn("blender_probe.py", source)

    def test_legacy_additional_prompt_is_not_in_the_runner(self):
        source = (ROOT / "generate_3d.py").read_text(encoding="utf-8")
        self.assertNotIn("--stage7-extra-prompt", source)
        self.assertNotIn("--stage7-prompt", source)
        self.assertNotIn("stage7_system_prompt.txt", source)
        self.assertIn("compose_generation_user_prompt", source)

    def test_tree_only_prompt_is_a_clean_attachment_ablation(self):
        blueprint = {
            "root_part_id": "root",
            "parts": [
                {"id": "root", "name": "root", "parent_id": None},
                {"id": "child", "name": "child", "parent_id": "root"},
            ],
            "attachments": [
                {
                    "parent_part_id": "root",
                    "child_part_id": "child",
                    "shared_anchor_required": True,
                }
            ],
        }
        prompt = generate_3d.compose_generation_user_prompt(
            "a two-part object", blueprint, "tree-only"
        )
        self.assertIn("<tree_only_attachment_contract>", prompt)
        self.assertIn("fixed world-coordinate", prompt)
        self.assertIn("<native_part_parameter_contract>", prompt)
        self.assertNotIn("<shared_anchor_implementation_contract>", prompt)

        full_prompt = generate_3d.compose_generation_user_prompt(
            "a two-part object", blueprint, "shared-anchor"
        )
        self.assertIn("<shared_anchor_implementation_contract>", full_prompt)
        self.assertNotIn("<tree_only_attachment_contract>", full_prompt)


if __name__ == "__main__":
    unittest.main()
