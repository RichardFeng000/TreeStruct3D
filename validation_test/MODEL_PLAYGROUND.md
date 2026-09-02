# TreeStruct3D model inspector

The model inspector keeps the browser presentation layer separate from Blender
execution and source analysis:

- `frontend/` contains the parameter controls, hierarchy and anchor diagrams,
  and Three.js preview.
- `algorithm/` contains source parsing, parameter injection, task scheduling,
  Blender execution, GLB export, and runtime structural analysis.

The browser never executes Blender Python directly. It sends bounded requests
to a service listening on localhost; that service runs the selected program in
Blender, exports a fresh GLB, and returns it to the preview.

## Start

From the monorepo root:

```bash
./validation_test/start_model_playground.sh
```

To load a specific dataset or seed as the initial source:

```bash
./validation_test/run_dataset.sh validation_test/datasets/stage1_output
./validation_test/run_dataset.sh TreeStruct3D/outputs/Chameleon_seed0
```

Multiple directories can be exposed as independent sources:

```bash
./validation_test/run_dataset.sh first_output second_output
```

Use `MODEL_PLAYGROUND_PORT` to choose a port and
`MODEL_PLAYGROUND_OPEN=0` to suppress automatic browser opening. Use
`TREESTRUCT3D_BLENDER` to select the Blender 5.0 executable.

## Interface

The top toolbar selects a code source and model. The parameter panel edits
supported values, the center panel switches between part hierarchy, definition
tree, and call graph views, and the Three.js panel supports orbit, zoom, reset,
and semantic-part highlighting.

The preview uses Three.js's Y-up coordinate system and begins from an elevated
three-quarter view. Re-centering preserves the user's viewing direction while
adjusting the target and distance to fit the current model.

Source changes are isolated by dataset in the model catalog and cache key, so
models with the same seed name cannot overwrite one another's previews.

## Native parameter editing

TreeStruct3D-generated programs use the top-level literal dictionary
`PART_PARAMS`. For these programs, the inspector edits the literal values and
executes the full source again, allowing geometry and shared anchors to be
recomputed together.

Programs without this protocol remain viewable through legacy approximate
controls, but that mode is not evidence that attachments survive structural
edits. Runtime validation independently perturbs each concrete parent and child
part before accepting a shared anchor.

## Review workflow

The failed-case control persists selections in `failed_cases.json` under the
active dataset. The classification dialog records a resolution and one of the
supported issue categories in `problem_classifications.json`. Both records are
scoped to the selected source.

## Runtime isolation

The runtime probe lives at `algorithm/runtime/blender_probe.py` and imports no
code from directories outside this component. Cache keys include the Blender
version, render-worker version, source content, parameters, and source identity
to prevent stale previews from being reused across incompatible runs.
