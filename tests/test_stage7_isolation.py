from pathlib import Path
import tempfile
import unittest

import extract_structure
import run_stage7


ROOT = Path(__file__).resolve().parents[1]


class Stage7IsolationTest(unittest.TestCase):
    def test_default_config_is_loaded_from_configs_directory(self):
        self.assertEqual(
            run_stage7.DEFAULT_CONFIG,
            ROOT / "configs" / "gemma_4_31b.yaml",
        )
        self.assertEqual(extract_structure.DEFAULT_CONFIG, run_stage7.DEFAULT_CONFIG)

    def test_output_prefix_changes_only_output_instance_name(self):
        self.assertEqual(
            run_stage7.output_instance_name("Chameleon_seed0", "kimi_k3_"),
            "kimi_k3_Chameleon_seed0",
        )
        self.assertEqual(
            run_stage7.output_instance_name("Chameleon_seed0", ""),
            "Chameleon_seed0",
        )
        self.assertEqual(
            run_stage7.output_instance_name(
                "Chameleon_seed0",
                "kimi_k3_",
                "(1)",
            ),
            "kimi_k3_Chameleon_seed0(1)",
        )
        with self.assertRaises(ValueError):
            run_stage7.output_instance_name("Chameleon_seed0", "../unsafe/")
        with self.assertRaises(ValueError):
            run_stage7.output_instance_name("Chameleon_seed0", "", "../unsafe/")

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
            run_stage7.clear_generation_artifacts(out_dir)
            self.assertTrue((extraction / "structure.json").is_file())
            self.assertTrue(background.is_file())
            self.assertFalse((out_dir / "old.py").exists())
            self.assertFalse((out_dir / "renders").exists())

    def test_generation_uses_only_original_text_to_3d_system_prompt(self):
        self.assertEqual(
            run_stage7.DEFAULT_SYSTEM_PROMPT,
            ROOT / "prompts" / "text_to_3d_system_prompt.txt",
        )
        source = (ROOT / "run_stage7.py").read_text(encoding="utf-8")
        self.assertNotIn("stage7_extra_prompt", source)
        self.assertNotIn("structure_extraction_system_prompt", source)
        base_prompt = run_stage7.DEFAULT_SYSTEM_PROMPT.read_text(encoding="utf-8")
        self.assertEqual(
            run_stage7.sha256_text(base_prompt),
            "c2abed528a5271f887e1147f1509eb2988160e9775940c7bd013955f1f79b4b9",
        )

    def test_extraction_uses_new_surface_attachment_system_prompt(self):
        self.assertEqual(
            extract_structure.DEFAULT_EXTRACTION_PROMPT,
            ROOT
            / "prompts"
            / "structure_extraction_surface_attachment_system_prompt.txt",
        )
        baseline = ROOT / "prompts" / "structure_extraction_system_prompt.txt"
        self.assertTrue(baseline.is_file())
        self.assertEqual(
            run_stage7.sha256_text(baseline.read_text(encoding="utf-8")),
            "4d769ebfde0eda792d21896e98bacbc1686ae398a4750dd9a34127bd3152e8c5",
        )
        source = (ROOT / "extract_structure.py").read_text(encoding="utf-8")
        self.assertNotIn("stage7_extra_prompt", source)
        self.assertNotIn("text_to_3d_system_prompt", source)

    def test_runner_has_no_structgen_import_or_old_prompt(self):
        source = (ROOT / "run_stage7.py").read_text(encoding="utf-8")
        self.assertNotIn("from StructGen3D", source)
        self.assertNotIn("import StructGen3D", source)
        for old_prompt in (
            "stage5_full_constraints.txt",
            "stage6_connection_first_constraints.txt",
        ):
            self.assertNotIn(old_prompt, source)

    def test_model_can_be_overridden_without_changing_provider_config(self):
        parser_source = (ROOT / "run_stage7.py").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument(\n        "--model"', parser_source)
        self.assertIn('config["model"] = args.model', parser_source)

    def test_default_outputs_are_centralized_under_stage_results(self):
        expected = ROOT.parent / "stage_results" / "stage7_output"
        self.assertEqual(run_stage7.DEFAULT_OUTPUT_DIR, expected)
        self.assertEqual(run_stage7.DEFAULT_STRUCTURE_CONTEXT_DIR, expected)
        self.assertEqual(extract_structure.DEFAULT_EXTRACTION_OUTPUT, expected)

    def test_validation_test_is_the_default_structural_evaluator(self):
        self.assertEqual(
            run_stage7.DEFAULT_VALIDATION_TEST_ROOT,
            ROOT.parent / "validation_test",
        )
        source = (ROOT / "run_stage7.py").read_text(encoding="utf-8")
        self.assertIn("validate_with_structure_repair", source)
        self.assertIn("blender_probe.py", source)

    def test_stage7_extra_prompt_is_not_in_the_runner(self):
        source = (ROOT / "run_stage7.py").read_text(encoding="utf-8")
        self.assertNotIn("--stage7-extra-prompt", source)
        self.assertNotIn("--stage7-prompt", source)
        self.assertNotIn("stage7_system_prompt.txt", source)
        self.assertIn("compose_generation_user_prompt", source)


if __name__ == "__main__":
    unittest.main()
