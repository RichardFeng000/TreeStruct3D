# TreeStruct3D naming and terminology

This document defines the names used by the public interface, source code, and
saved artifacts. New code should describe a component by its responsibility,
not by the experiment stage in which it was introduced.

## Canonical project name

- Display name: `TreeStruct3D`
- Python package: `treestruct3d`
- Environment-variable prefix: `TREESTRUCT3D_`
- JSON schema namespace: `treestruct3d.`

The repository contains two top-level components. `TreeStruct3D/` is the
generation pipeline; `visual_validation/` is the **TreeStruct3D Visual
Validation Toolkit**. Its automated structural validator is one capability of
the component, not the name of the whole component.

Do not introduce numbered names such as `stage7`, `v2_pipeline`, or `final` for
active components. Use semantic names and reserve version numbers for explicit
file formats or releases.

## Pipeline terms

| Term | Meaning |
| --- | --- |
| structure blueprint | Model-produced JSON plan describing semantic parts and their directed attachments |
| semantic part | One independently constructed unit listed in the blueprint and `PART_PARAMS` |
| root part | The single part with no construction parent |
| attachment | A directed parent-to-child construction relationship |
| shared anchor | A parent surface sample and child surface sample aligned to the same world-space point |
| structure extraction | Text-to-blueprint phase; it does not generate Blender code |
| 3D generation | Blueprint-guided Blender Python generation phase |
| render validation | Syntax, Blender execution, and four-view rendering checks |
| structural validation | Runtime hierarchy, contact, anchor, and parameter-perturbation checks |
| visual validation | Interactive inspection of renders, part hierarchy, shared anchors, and review annotations |
| visual refinement | Render critique performed only after deterministic validation passes |
| run ID | Output directory and canonical generated-program stem for one model/instance run |
| tree-only mechanism | Ablation that keeps the extracted hierarchy and `PART_PARAMS` but uses fixed-coordinate placement instead of shared anchors |

Use “part” for blueprint units and “Mesh object” for concrete Blender objects;
they are related but not interchangeable. Use “attachment” for a declared
directed relationship and “contact” only for observed surface proximity.

## Machine naming

- Python modules, functions, and files use `snake_case`.
- Classes use `PascalCase`; constants use `UPPER_SNAKE_CASE`.
- Command-line options use `--kebab-case`.
- JSON fields use `snake_case`.
- Schema identifiers use `treestruct3d.<artifact>/v<integer>`.
- Benchmark instance IDs keep their upstream 3DCodeBench spelling.

The generated-program interface uses `PART_PARAMS` and the Blender custom
property `treestruct3d_part_id`. `PART_PARAMS` is intentionally uppercase
because it is a module-level protocol constant.

## Legacy identifiers

Pre-release versions used “Stage 7” as an internal experiment label. The old
blueprint schema identifier `stage7-structure-blueprint/v2` remains readable so
existing artifacts do not become invalid. It must not be written by new runs.

Historical research notes and the compatibility test may mention the old label.
Active commands, modules, output schemas, and documentation use TreeStruct3D.
