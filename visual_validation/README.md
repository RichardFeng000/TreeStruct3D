# TreeStruct3D Visual Validation Toolkit

This directory contains TreeStruct3D's visual validation and interactive
inspection component. It analyzes generated Blender Python programs, executes
automated structural probes, exports GLB previews, and visualizes part
hierarchies and shared anchors in a local browser interface.

`visual_validation/` is not a separate product or Git repository. Its public
name is the **TreeStruct3D Visual Validation Toolkit**. See the
[repository overview](../README.md) for the complete generation-and-validation
workflow.

## Capabilities

- Static analysis of Python definitions, calls, and candidate part relations
- Blender runtime observation of semantic parts and parent-child attachments
- Contact and geometry-derived shared-anchor checks
- Independent parent and child parameter perturbations through `PART_PARAMS`
- Local Three.js preview with part highlighting and structure overlays
- Multi-dataset comparison, failed-case marking, and issue classification

## Layout

```text
visual_validation/
├── frontend/                 browser interface and vendored Three.js modules
├── algorithm/                analysis, local service, and Blender export code
│   ├── runtime/              self-contained Blender structural probe
│   └── archive/              inactive audit and QA utilities
├── datasets/                 committed evaluation sources and assets
├── tests/                    offline regression tests
├── archive/                  historical reports and inspection artifacts
└── *.sh                      command-line launchers
```

The committed image, PDF, Blender, and GLB assets are managed with Git LFS.

## Requirements

- Python 3.9 or newer
- Blender 5.0 for live previews and runtime probes
- A modern browser
- Node.js only for the frontend JavaScript regression test

Blender is resolved in this order:

1. `TREESTRUCT3D_BLENDER`
2. the monorepo's local `tools/Blender-5.0.app` installation
3. the standard macOS Blender application path
4. `blender` on `PATH`

## Launch the inspector

From the repository root:

```bash
./visual_validation/start_model_playground.sh
```

Or launch the component directly:

```bash
cd visual_validation
./run_model_playground.sh
```

To inspect one or more explicit datasets or TreeStruct3D output directories:

```bash
./visual_validation/run_dataset.sh TreeStruct3D/outputs
./visual_validation/run_dataset.sh \
  TreeStruct3D/outputs/first_run \
  TreeStruct3D/outputs/second_run
```

Arguments may be dataset directories, individual seed directories, canonical
Python files, or names found under `visual_validation/datasets/` and
`TreeStruct3D/outputs/`. The first selected dataset becomes the initial browser
source.

The service binds to `127.0.0.1` and starts at port `8765`. If that port is in
use, `run_dataset.sh` selects the next free port through `8799`.

## Generated-program protocol

TreeStruct3D programs expose editable values through the module-level literal
dictionary `PART_PARAMS`. The inspector changes those source values, executes
the complete program from an empty Blender scene, and then re-evaluates the
geometry and attachments.

Generated Mesh objects use the custom property `treestruct3d_part_id` for
semantic identity. The validator still reads the pre-release
`stage7_part_id` property so historical artifacts remain inspectable, but new
programs and fixtures must use `treestruct3d_part_id`.

A shared anchor passes only when its authored parent and child endpoints remain
real evaluated Mesh samples and stay aligned in the default run, the parent
perturbation, and the child perturbation. Visual proximity alone is not accepted
as shared-anchor evidence.

## Review annotations

The browser can mark the current model as a failed case. Marks are stored in
`failed_cases.json` inside the selected dataset. The issue-classification panel
stores review decisions in `problem_classifications.json` in the same location.
These files belong to the reviewed dataset and should be committed only when
they are intended release annotations.

## Tests

From the repository root:

```bash
(cd visual_validation && python -m unittest discover -s tests -v)
```

The unit suite does not start Blender. Runtime checks are separate and require
an explicit Blender 5.0 installation.

More interface details are documented in
[MODEL_PLAYGROUND.md](MODEL_PLAYGROUND.md).
