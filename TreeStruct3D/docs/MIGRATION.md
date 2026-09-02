# Migration from the pre-release layout

TreeStruct3D replaces the internal “Stage 7” experiment label with stable,
responsibility-based names. The generation and validation sequence is unchanged.

The former `StructGen3D3.0` and `validation_test` repositories are now the
`TreeStruct3D/` and `visual_validation/` components of one TreeStruct3D
monorepo. Their committed histories remain reachable from the unified `main`
branch.

## Renamed paths

| Pre-release path | Current path |
| --- | --- |
| `run_stage7.py` | `generate_3d.py` |
| `run_stage7.sh` | `generate_3d.sh` |
| `core/` | `treestruct3d/` |
| `tests/test_stage7_isolation.py` | `tests/test_pipeline_contract.py` |
| `achieve/` | `archive/` |
| `validation_test/` | `visual_validation/` |
| `prompts/text_to_3d_system_prompt.txt` | `prompts/blender_generation_system_prompt.txt` |
| `prompts/structure_extraction_surface_attachment_system_prompt.txt` | `prompts/structure_blueprint_system_prompt.txt` |
| `prompts/structure_extraction_system_prompt.txt` | `prompts/structure_blueprint_baseline_system_prompt.txt` |

Python integrations should import `generate_3d` and `treestruct3d.*`. Shell
automation should invoke `generate_3d.sh`.

## Outputs and schemas

New runs default to `outputs/` inside the repository. To reuse a pre-release
result tree, select it explicitly for both phases:

```bash
./extract_structure.sh \
  --output-dir ../stage_results/stage7_output \
  --instances Bird_seed0

./generate_3d.sh \
  --output-dir ../stage_results/stage7_output \
  --structure-context-dir ../stage_results/stage7_output \
  --instances Bird_seed0
```

New manifests and reports use the `treestruct3d.` schema namespace. The
pre-release blueprint schema `stage7-structure-blueprint/v2` is still accepted
when loading existing `structure.json` files. New blueprints use
`treestruct3d.structure-blueprint/v2`.

Run logs are now written as `run_log.json` and `pipeline.log`. When
`--resume-existing` is used, the loader also accepts the old `log.json` name.
Render snapshots are stored under `render_history/`.

The preferred validator option is `--validator-root`; the old
`--validation-test-root` spelling remains an alias.

The clearer `--api-timeout` and `--request-delay` names replace `--timeout` and
`--sleep`. Generation uses `--generation-retries`; extraction uses
`--extraction-retries`. All three pre-release spellings remain accepted as
aliases.

## Prompt invariants

The renamed Blender generation prompt is byte-for-byte identical to the
pre-release file. The reproducibility baseline prompt is also byte-for-byte
identical. The active structure-blueprint prompt changes only its schema
identifier, and the generated-program contract changes only the custom part-ID
property name to `treestruct3d_part_id`.
