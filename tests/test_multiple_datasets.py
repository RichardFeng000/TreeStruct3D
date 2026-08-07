import argparse
import tempfile
import unittest
from pathlib import Path

from algorithm import model_playground


class MultipleDatasetsTest(unittest.TestCase):
    @staticmethod
    def _seed(root: Path, name: str) -> None:
        seed = root / name
        seed.mkdir(parents=True)
        (seed / f"{name}.py").write_text("value = 1\n", encoding="utf-8")

    def test_multiple_datasets_are_separate_frontend_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage7 = root / "stage7_output"
            stage71 = root / "stage7.1_output"
            benchmark = root / "empty_benchmark"
            benchmark.mkdir()
            self._seed(stage7, "Stage7_seed0")
            self._seed(stage71, "Stage71_seed0")
            args = argparse.Namespace(
                dataset=[stage7, stage71],
                dataset_label=["Stage 7", "Stage 7.1"],
                benchmark=benchmark,
                blender=model_playground.DEFAULT_BLENDER,
                cache_dir=root / "cache",
                render_timeout=60,
            )

            state = model_playground.PlaygroundState(args)

            self.assertEqual(state.default_source, "dataset")
            self.assertEqual(state.source_labels["dataset"], "Stage 7")
            self.assertEqual(state.source_labels["dataset_2"], "Stage 7.1")
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


if __name__ == "__main__":
    unittest.main()
