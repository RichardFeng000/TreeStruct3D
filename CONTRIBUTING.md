# Contributing to TreeStruct3D

TreeStruct3D is reproducibility-oriented research software. Contributions
should be focused, deterministic, and explicit about changes to public formats
or experimental behavior.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r TreeStruct3D/requirements.txt
(cd TreeStruct3D && python -m unittest discover -s tests -v)
(cd validation_test && python -m unittest discover -s tests -v)
```

The unit suites must remain offline: they may not call model APIs or launch
Blender. Document separate manual checks for changes that require either
service.

## Prompt and pipeline freeze policy

The model-facing prompts and the active pipeline sequence are frozen. Do not
change prompt wording, prompt assembly, retry order, validation order, or
model-facing contracts as an incidental part of refactoring.

A deliberate behavioral change requires a narrowly scoped proposal, updated
contract tests, migration notes for affected artifacts, and new experiment
results that are not mixed with results from the frozen protocol.

Path and protocol-name migrations should retain readers for existing artifacts
when practical. Prompt hash tests must continue to pass.

## Naming

Follow [TreeStruct3D/docs/NAMING.md](TreeStruct3D/docs/NAMING.md). Active code
uses responsibility-based names rather than internal stage numbers or temporary
labels such as `new`, `latest`, or `final`.

The directory `validation_test/` is a compatibility path. In prose, refer to
that component as the **TreeStruct3D Structural Validation Toolkit** or the
**structural validator**.

## Credentials, data, and generated files

Never commit API keys, local configuration, raw provider responses, caches, or
unreviewed generated output. Use
`TreeStruct3D/configs/config.example.yaml` for documented configuration fields
and environment-variable placeholders for credentials.

Large tracked assets must use the existing Git LFS policy. Do not add generated
datasets or model outputs to LFS merely to bypass normal review.

## Pull requests

Before opening a pull request:

1. Run both offline unit suites from their component directories.
2. Confirm that public names and saved fields follow the naming guide.
3. Preserve benchmark identifiers and upstream provenance.
4. Check that no credentials or local absolute paths were introduced.
5. Document user-facing behavior and migration implications.
