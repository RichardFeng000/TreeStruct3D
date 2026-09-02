# 3DCodeBench input snapshot

The data in `categories/` was not created by TreeStruct3D. It is a vendored
snapshot of the `3DCodeBench/` evaluation split published in the official
[YipengGao/3DCode Hugging Face dataset](https://huggingface.co/datasets/YipengGao/3DCode).
The benchmark implementation is available from the official
[gaoypeng/3dcodebench repository](https://github.com/gaoypeng/3dcodebench).

## Pinned source

- Dataset repository: `YipengGao/3DCode`
- Dataset subdirectory: `3DCodeBench/`
- Hugging Face revision: `c2bcae4f36d6fe19e794b85695d430ce0210f92d`
- Local snapshot: 212 category directories and 636 upstream files

Every file in the local `categories/` snapshot was verified by Git blob ID and
size against that immutable upstream revision on 2026-09-02. The same metadata
is recorded in [SOURCE.json](SOURCE.json) for automated provenance tooling.

## What TreeStruct3D reads

Each upstream category has this layout:

```text
<Category>_seed0/
├── <Category>_seed0.py
├── prompt_description.txt
└── prompt_instruction.txt
```

| File | Model-facing use in TreeStruct3D |
| --- | --- |
| `prompt_description.txt` | Default natural-language input to both structure extraction and generation |
| `prompt_instruction.txt` | Alternative natural-language input selected with `--prompt-type instruction` |
| `<Category>_seed0.py` | Never read by either model-facing stage; retained only as the upstream reference factory for provenance and evaluation |

The structure blueprint produced by `extract_structure.py` is TreeStruct3D
output, not an additional benchmark input. Generation receives the selected
text prompt plus that separately extracted blueprint.

## Download from the official source

The repository already contains the pinned snapshot, so this step is optional.
To obtain an independent copy directly from Hugging Face:

```bash
python -m pip install -U huggingface_hub
hf download YipengGao/3DCode \
  --repo-type dataset \
  --revision c2bcae4f36d6fe19e794b85695d430ce0210f92d \
  --include "3DCodeBench/*" \
  --local-dir /absolute/path/to/3dcode
```

The resulting input directory is
`/absolute/path/to/3dcode/3DCodeBench/`. Pass that directory to both commands
with `--data-dir`; no files need to be moved into the repository. Omit
`--revision` only when intentionally testing against the latest upstream
version rather than the snapshot used here.

## Licenses and citation

The upstream dataset card states that the benchmark split and captions are
released under the MIT License, while the reference factory scripts retain
[Infinigen's BSD-3-Clause license](https://github.com/princeton-vl/infinigen/blob/main/LICENSE).
These terms are separate from TreeStruct3D's Apache-2.0 license. See the
repository's [third-party notices](../../THIRD_PARTY_NOTICES.md) before
redistributing the benchmark files.

Please cite 3DCodeBench and the relevant Infinigen works when using these
inputs. The official citation is provided on the
[3DCode dataset card](https://huggingface.co/datasets/YipengGao/3DCode#citation).
