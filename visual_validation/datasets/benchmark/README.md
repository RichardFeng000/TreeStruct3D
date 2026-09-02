# 3DCodeBench fixtures for visual validation

The 212 category directories under `categories/` mirror the `3DCodeBench/`
evaluation split from the official
[YipengGao/3DCode dataset](https://huggingface.co/datasets/YipengGao/3DCode).
They are not data created by TreeStruct3D.

The three upstream files in each category are byte-identical to the pinned
snapshot used by the generation component:

```text
<Category>_seed0/
├── <Category>_seed0.py
├── prompt_description.txt
└── prompt_instruction.txt
```

This directory may also contain TreeStruct3D-derived validation fixtures, such
as structure-tree artifacts. Those additions are not part of the upstream
3DCodeBench split.

The generation pipeline defaults to
`TreeStruct3D/benchmark/categories/`; this second copy exists for the visual
validation toolkit's self-contained dataset loader. For the immutable upstream
revision, exact download command, model-input boundary, and licenses, see the
canonical [benchmark provenance document](../../../TreeStruct3D/benchmark/README.md).
