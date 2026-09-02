from pathlib import Path
import unittest


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
FRONTEND = FRONTEND_DIR / "model_playground.html"


class FrontendDefaultViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = FRONTEND.read_text(encoding="utf-8")

    def test_project_frontend_html_is_english_only(self):
        for path in sorted(FRONTEND_DIR.glob("*.html")):
            source = path.read_text(encoding="utf-8")
            self.assertIn('<html lang="en">', source, path.name)
            self.assertNotRegex(
                source,
                r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]",
                path.name,
            )

    def test_initial_graph_view_is_3d_hierarchy(self):
        self.assertIn("const graphState = {\n      view: 'tree3d',", self.source)

    def test_every_seed_load_prefers_3d_hierarchy(self):
        start = self.source.index("    function initializeGraph(data) {")
        end = self.source.index("\n    function formatValue(", start)
        initialize_graph = self.source[start:end]
        self.assertIn("if (tree3dSourceView()?.nodes?.length)", initialize_graph)
        self.assertIn("setGraphView('tree3d');", initialize_graph)
        self.assertIn("return;", initialize_graph)

    def test_previous_and_next_buttons_stay_inside_current_dataset(self):
        self.assertIn('id="previous-model-button"', self.source)
        self.assertIn('id="next-model-button"', self.source)
        start = self.source.index("    function selectAdjacentModel(offset) {")
        end = self.source.index("\n    function updateModelOptionAppearance(", start)
        select_adjacent = self.source[start:end]
        self.assertIn("modelSelect.selectedIndex = targetIndex;", select_adjacent)
        self.assertIn("selectModel(modelSelect.value, sourceSelect.value)", select_adjacent)
        self.assertNotIn("sourceSelect.value =", select_adjacent)

    def test_arrow_keys_switch_seeds_outside_editable_controls(self):
        self.assertIn('aria-keyshortcuts="ArrowLeft"', self.source)
        self.assertIn('aria-keyshortcuts="ArrowRight"', self.source)
        self.assertIn("event.key === 'ArrowLeft'", self.source)
        self.assertIn("selectAdjacentModel(-1);", self.source)
        self.assertIn("event.key === 'ArrowRight'", self.source)
        self.assertIn("selectAdjacentModel(1);", self.source)
        self.assertIn("'input, select, textarea, [contenteditable=\"true\"]'", self.source)

    def test_space_toggles_failed_case_outside_interactive_controls(self):
        self.assertIn('aria-keyshortcuts="Space"', self.source)
        self.assertIn("event.code === 'Space'", self.source)
        self.assertIn("failureToggle.checked = !failureToggle.checked;", self.source)
        self.assertIn("saveCurrentFailureMark();", self.source)
        self.assertIn("!event.target.closest?.('button, a')", self.source)

    def test_refresh_restores_current_dataset_and_seed(self):
        self.assertIn("const selectionStorageKey = 'model-playground:last-selection:v1';", self.source)
        self.assertIn("localStorage.getItem(selectionStorageKey)", self.source)
        self.assertIn("localStorage.setItem(", self.source)
        self.assertIn("rememberSelection(sourceId, modelId);", self.source)
        self.assertIn("source.id === remembered?.source", self.source)
        self.assertIn("model.id === preferredModelId", self.source)

    def test_validation_turn_updates_with_the_selected_seed(self):
        self.assertIn('id="validation-turn-value"', self.source)
        self.assertIn("option.dataset.validationTurn = model.validation_turn", self.source)
        self.assertIn("function updateValidationTurn()", self.source)
        self.assertIn("· validation turn ${validationTurn}", self.source)
        self.assertIn("updateValidationTurn();", self.source)

    def test_model_select_keeps_readable_width_with_validation_turn(self):
        self.assertIn("flex-wrap: wrap;", self.source)
        self.assertIn("#model-select {\n      flex: 1 1 300px;\n      min-width: 280px;", self.source)


if __name__ == "__main__":
    unittest.main()
