import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from algorithm import model_playground


class MultipleDatasetsTest(unittest.TestCase):
    @staticmethod
    def _seed(root: Path, name: str) -> None:
        seed = root / name
        seed.mkdir(parents=True)
        (seed / f"{name}.py").write_text("value = 1\n", encoding="utf-8")

    def test_validation_turn_metadata_default_is_component_local(self):
        self.assertEqual(
            model_playground.DEFAULT_VALIDATION_TURNS_CSV,
            model_playground.DATASETS_DIR / "validation_turns.csv",
        )

    def test_multiple_datasets_are_separate_frontend_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            primary_output = root / "primary_output"
            comparison_output = root / "comparison_output"
            benchmark = root / "empty_benchmark"
            benchmark.mkdir()
            self._seed(primary_output, "Primary_seed0")
            self._seed(comparison_output, "Comparison_seed0")
            args = argparse.Namespace(
                dataset=[primary_output, comparison_output],
                dataset_label=["Primary run", "Comparison run"],
                benchmark=benchmark,
                blender=model_playground.DEFAULT_BLENDER,
                cache_dir=root / "cache",
                render_timeout=60,
            )

            state = model_playground.PlaygroundState(args)

            self.assertEqual(state.default_source, "dataset")
            self.assertEqual(state.source_labels["dataset"], "Primary run")
            self.assertEqual(state.source_labels["dataset_2"], "Comparison run")
            self.assertEqual(
                next(iter(state.models_by_source["dataset"].values())).source_id,
                "dataset",
            )
            self.assertEqual(
                next(iter(state.models_by_source["dataset_2"].values())).source_id,
                "dataset_2",
            )

    def test_legacy_single_path_namespace_still_works(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = root / "one_dataset"
            benchmark = root / "empty_benchmark"
            benchmark.mkdir()
            self._seed(dataset, "Example_seed0")
            args = argparse.Namespace(
                dataset=dataset,
                dataset_label="Legacy label",
                benchmark=benchmark,
                blender=model_playground.DEFAULT_BLENDER,
                cache_dir=root / "cache",
                render_timeout=60,
            )

            state = model_playground.PlaygroundState(args)

            self.assertEqual(state.source_labels["dataset"], "Legacy label")
            self.assertIn("dataset", state.models_by_source)

    def test_validation_turn_uses_figure_3_per_seed_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = root / "gpt5.5"
            benchmark = root / "empty_benchmark"
            benchmark.mkdir()
            self._seed(dataset, "Bird_seed0")
            args = argparse.Namespace(
                dataset=dataset,
                dataset_label="GPT-5.5",
                benchmark=benchmark,
                blender=model_playground.DEFAULT_BLENDER,
                cache_dir=root / "cache",
                render_timeout=60,
            )

            validation_turns = {("GPT-5.5", "Bird_seed0"): 1}
            with mock.patch.object(
                model_playground,
                "_load_validation_turns",
                return_value=validation_turns,
            ):
                state = model_playground.PlaygroundState(args)

            self.assertEqual(state.validation_turn("dataset", "Bird_seed0"), 1)
            self.assertIsNone(state.validation_turn("dataset", "Missing_seed0"))

    def test_failed_cases_are_persisted_inside_each_dataset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            primary_output = root / "primary_output"
            comparison_output = root / "comparison_output"
            benchmark = root / "empty_benchmark"
            benchmark.mkdir()
            self._seed(primary_output, "Failed_seed0")
            self._seed(comparison_output, "Other_seed0")
            args = argparse.Namespace(
                dataset=[primary_output, comparison_output],
                dataset_label=["Primary run", "Comparison run"],
                benchmark=benchmark,
                blender=model_playground.DEFAULT_BLENDER,
                cache_dir=root / "cache",
                render_timeout=60,
            )
            state = model_playground.PlaygroundState(args)
            model_id = "Failed_seed0/Failed_seed0"

            result = state.set_model_failed("dataset", model_id, True)

            failure_file = primary_output / model_playground.FAILED_CASES_FILENAME
            self.assertEqual(Path(result["file"]), failure_file.resolve())
            self.assertEqual(state.failed_models("dataset"), {model_id})
            self.assertEqual(state.failed_models("dataset_2"), set())
            payload = json.loads(failure_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["dataset"], "Primary run")
            self.assertEqual(payload["failed_cases"], [model_id])

            state.set_model_failed("dataset", model_id, False)
            self.assertEqual(state.failed_models("dataset"), set())

    def test_failed_cases_support_a_single_seed_dataset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            seed = root / "Example_seed0"
            benchmark = root / "empty_benchmark"
            benchmark.mkdir()
            self._seed(root, "Example_seed0")
            args = argparse.Namespace(
                dataset=seed,
                dataset_label="One seed",
                benchmark=benchmark,
                blender=model_playground.DEFAULT_BLENDER,
                cache_dir=root / "cache",
                render_timeout=60,
            )
            state = model_playground.PlaygroundState(args)
            model_id = "Example_seed0/Example_seed0"

            state.set_model_failed("dataset", model_id, True)

            self.assertTrue(
                (seed / model_playground.FAILED_CASES_FILENAME).is_file()
            )

    def test_problem_classification_is_saved_beside_failed_cases(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = root / "dataset"
            benchmark = root / "empty_benchmark"
            benchmark.mkdir()
            self._seed(dataset, "Example_seed0")
            renders = dataset / "Example_seed0" / "renders"
            renders.mkdir()
            (renders / "Image_005.png").write_bytes(b"png")
            args = argparse.Namespace(
                dataset=dataset,
                dataset_label="Dataset",
                benchmark=benchmark,
                blender=model_playground.DEFAULT_BLENDER,
                cache_dir=root / "cache",
                render_timeout=60,
            )
            state = model_playground.PlaygroundState(args)
            model_id = "Example_seed0/Example_seed0"
            state.set_model_failed("dataset", model_id, True)

            result = state.set_problem_classification(
                "dataset",
                model_id,
                "minor_fix",
                ["missing_shared_anchor", "structure_extract"],
                "共享锚点没有抽取出来",
            )

            classification_file = (
                dataset / model_playground.PROBLEM_CLASSIFICATIONS_FILENAME
            )
            payload = json.loads(classification_file.read_text(encoding="utf-8"))
            record = payload["cases"][model_id]
            self.assertEqual(record["resolution"], "minor_fix")
            self.assertEqual(
                record["issues"],
                ["missing_shared_anchor", "structure_extract"],
            )
            self.assertEqual(result["failed_count"], 1)
            self.assertEqual(result["classified_count"], 1)
            self.assertTrue(result["cases"][0]["classified"])
            self.assertIn("/api/case-render?", result["cases"][0]["renders"][0])


if __name__ == "__main__":
    unittest.main()
