import json
from pathlib import Path
import subprocess
import unittest


FRONTEND = Path(__file__).resolve().parents[1] / "frontend" / "model_playground.html"


class FrontendHighlightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = FRONTEND.read_text(encoding="utf-8")

    @classmethod
    def _function(cls, name: str, next_name: str) -> str:
        start_marker = f"    function {name}("
        end_marker = f"\n    function {next_name}("
        start = cls.source.index(start_marker)
        end = cls.source.index(end_marker, start)
        return cls.source[start:end].strip()

    def test_child_mesh_does_not_inherit_parent_part_identity(self):
        function_source = self._function(
            "previewMeshNames",
            "previewMeshMatchScore",
        )
        script = f"""
{function_source}
const parent = {{
  name: 'body_whorl',
  geometry: {{name: 'body_whorl_mesh'}},
  userData: {{treestruct3d_part_id: 'body_whorl'}},
  parent: null,
}};
const child = {{
  name: 'spire',
  geometry: {{name: 'spire_mesh'}},
  userData: {{treestruct3d_part_id: 'spire'}},
  parent,
}};
process.stdout.write(JSON.stringify(previewMeshNames(child)));
"""
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
        names = json.loads(completed.stdout)

        self.assertIn("spire", names)
        self.assertIn("spire_mesh", names)
        self.assertNotIn("body_whorl", names)
        self.assertNotIn("body_whorl_mesh", names)

    def test_legacy_part_identity_remains_readable(self):
        function_source = self._function(
            "previewMeshNames",
            "previewMeshMatchScore",
        )
        script = f"""
{function_source}
const mesh = {{
  name: 'legacy_mesh',
  geometry: {{name: 'legacy_geometry'}},
  userData: {{stage7_part_id: 'legacy_part'}},
  parent: null,
}};
process.stdout.write(JSON.stringify(previewMeshNames(mesh)));
"""
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("legacy_part", json.loads(completed.stdout))

    def test_missing_parent_mesh_does_not_fall_back_to_descendants(self):
        matching_source = self._function(
            "matchingPreviewMeshes",
            "previewMaterialClone",
        )

        self.assertNotIn("descendantPartNodes", self.source)
        self.assertNotIn("view.edges", matching_source)
        self.assertIn("return [];", matching_source)

    def test_failed_case_checkbox_is_persisted_through_the_api(self):
        self.assertIn('id="failure-toggle"', self.source)
        self.assertIn("fetch('/api/failures'", self.source)
        self.assertIn("option.dataset.failed", self.source)
        self.assertIn("updateFailureControl();", self.source)

    def test_problem_classifier_modal_has_categories_and_persistence(self):
        self.assertIn('id="problem-classify-button"', self.source)
        self.assertIn('id="problem-modal-backdrop"', self.source)
        self.assertIn('value="missing_shared_anchor"', self.source)
        self.assertIn('value="structure_extract"', self.source)
        self.assertIn('value="regenerate"', self.source)
        self.assertIn("fetch('/api/problem-classifications'", self.source)
        self.assertIn("failed-selected", self.source)
        self.assertIn(".problem-modal-backdrop[hidden] { display: none; }", self.source)


if __name__ == "__main__":
    unittest.main()
