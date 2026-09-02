# TreeStruct3D

TreeStruct3D generates editable Blender Python programs from natural-language
object descriptions. It first extracts a category-neutral part tree, then asks
a code model to construct the object with explicit parent-child relationships
and geometry-derived shared anchors. Generated programs are rendered, checked
for structural consistency, repaired when necessary, and finally reviewed for
visual quality.

This repository is research code derived from
[3DCodeBench](https://github.com/gaoypeng/3dcodebench). The upstream generation
system prompt is preserved byte-for-byte; TreeStruct3D adds structure extraction,
chronological logging, attachment validation, and repair orchestration.

## Pipeline

1. Read a 3DCodeBench natural-language description.
2. Extract and validate a connected structure blueprint.
3. Supply the description and blueprint to the Blender code model.
4. Parse, execute, and render the generated Blender Python program.
5. Validate its part hierarchy, contact, shared anchors, and parameter changes.
6. Repair render or structural failures and rerun the relevant checks.
7. Apply visual feedback only after render and structural validation pass.

The extraction and generation steps are separate commands. Generation never
reads benchmark reference Python files.

## Requirements

- Python 3.9 or newer
- Blender 5.0
- An API endpoint supported by one of the configuration formats below
- The sibling visual validation toolkit when structural checks are enabled

Install the Python dependency in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

TreeStruct3D looks for Blender in the existing sibling `tools/` checkout, the
standard macOS application path, and `PATH`. Set an explicit executable when
needed:

```bash
export TREESTRUCT3D_BLENDER=/absolute/path/to/blender
```

The monorepo's sibling `../visual_validation` directory is selected by default.
An external visual-validation checkout can be selected explicitly:

```bash
export TREESTRUCT3D_VALIDATOR_ROOT=/absolute/path/to/visual_validation
```

## Configuration

Copy the tracked example and provide credentials through the environment:

```bash
cp configs/config.example.yaml config.local.yaml
export TREESTRUCT3D_API_KEY=your-api-key
```

`config.local.yaml`, every other `configs/*.yaml` file, logs, and generated
outputs are ignored by Git. Never commit provider credentials.

Supported API formats are:

- `lmstudio_responses`
- `openai_responses`
- `openai_chat_completions`
- `gemini_generate_content`

Use `--config PATH` to select another local configuration. Use `--model ID` to
override only its model identifier while retaining the endpoint, API format,
credential, and token settings.

## Quick start

Extract one structure blueprint:

```bash
./extract_structure.sh \
  --instances Bird_seed0 \
  --overwrite
```

Generate and validate its Blender program:

```bash
./generate_3d.sh \
  --instances Bird_seed0 \
  --overwrite \
  --render-samples 16 \
  --render-resolution 256
```

Both commands accept the same `--output-prefix` and `--output-suffix`. Use the
same values for extraction and generation so they address the same result
directory. Run either command with `--help` for the complete interface.

By default, artifacts are written to `outputs/<run-id>/`:

```text
outputs/<run-id>/
├── structure_extraction/
│   ├── extraction_manifest.json
│   ├── extraction_log.json
│   ├── structure.json
│   └── structure.md
├── <run-id>.py
├── run_manifest.json
├── run_log.json
├── pipeline.log
├── renders/
└── structural_score_attempt*.json
```

Existing pre-release output directories remain usable through `--output-dir`
and `--structure-context-dir`. See [the migration guide](docs/MIGRATION.md).

## Prompt stability

The active prompt files have explicit responsibilities:

- `prompts/structure_blueprint_system_prompt.txt` extracts the connected part
  tree and attachment contract.
- `prompts/blender_generation_system_prompt.txt` is the unchanged upstream
  Blender generation system prompt.
- `prompts/visual_critique_*` evaluates render quality after deterministic checks.
- `prompts/structure_blueprint_baseline_system_prompt.txt` is retained only as a
  reproducibility baseline.

Tests pin the unchanged generation and baseline prompt hashes. Pull requests
must not alter prompt behavior implicitly. See the monorepo
[contribution guide](../CONTRIBUTING.md).

## Repository layout

```text
benchmark/categories/   3DCodeBench inputs with stable upstream instance IDs
prompts/                 active and reproducibility prompt files
treestruct3d/            reusable extraction, rendering, and validation modules
extract_structure.py     structure-blueprint command
generate_3d.py           generation, repair, and evaluation command
tests/                   deterministic unit and contract tests
docs/                    terminology, migration, and research notes
archive/                 inactive pre-release material
```

This directory is the generation component of the TreeStruct3D monorepo. See
[the repository-level overview](../README.md) for the integrated generation and
visual-validation layout.

Names used by the public interface and saved artifacts are defined in
[docs/NAMING.md](docs/NAMING.md). Benchmark instance IDs are intentionally not
renamed because they identify upstream data.

## Testing

The unit suite does not call model APIs or start Blender:

```bash
python -m unittest discover -s tests -v
```

Full end-to-end runs can incur API charges and require Blender plus the
structural validator.

## Provenance and license

The benchmark inputs, baseline runner behavior, rendering utilities, and
generation prompt originate from 3DCodeBench and are used under Apache-2.0.
TreeStruct3D's local changes are distributed under the same license; see
[LICENSE](LICENSE).
