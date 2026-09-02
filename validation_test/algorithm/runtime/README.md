# Runtime structural probe

`blender_probe.py` is the self-contained Blender runtime analyzer used for
directed parent-child relations, surface contact, shared anchors, and
parameter-perturbation evidence.

The probe was vendored from the project's earlier structural-metric research
implementation. The source snapshot used during that extraction had SHA-256:

```text
1b3c3472018e38d15294d4cddff28610e3f1798d27f8a2b26a7c013f4174b46a
```

The maintained copy in this directory is now the source of truth and may have
changed since that snapshot. It does not import modules from the earlier
research directory, so a clean TreeStruct3D checkout is sufficient.
