# Third-party notices

TreeStruct3D includes or derives from the following third-party projects. Their
licenses remain applicable to the corresponding material.

## 3DCodeBench software

- Project: [3DCodeBench](https://github.com/gaoypeng/3dcodebench)
- Upstream license file: Apache License 2.0
- Use: baseline generation behavior, rendering utilities, and the preserved
  Blender generation system prompt

TreeStruct3D documents its modifications and attribution in the repository
[NOTICE](NOTICE).

## 3DCode dataset and benchmark split

- Dataset: [YipengGao/3DCode](https://huggingface.co/datasets/YipengGao/3DCode)
- Included subset: `3DCodeBench/` at revision
  `c2bcae4f36d6fe19e794b85695d430ce0210f92d`
- Local files: `TreeStruct3D/benchmark/categories/` and the corresponding
  fixtures under `visual_validation/datasets/benchmark/categories/`
- Use: natural-language benchmark inputs and reference Blender factories

The upstream dataset card licenses the benchmark split and text prompts under
MIT. It states that the reference factory scripts retain the BSD-3-Clause
license of [Infinigen](https://github.com/princeton-vl/infinigen). These data
licenses remain applicable to the vendored files and are not replaced by
TreeStruct3D's Apache-2.0 project license.

## Three.js

- Project: [Three.js](https://github.com/mrdoob/three.js)
- Revision represented by the vendored core build: r166
- License: MIT
- Files: `visual_validation/frontend/vendor/three.module.min.js`,
  `GLTFLoader.js`, `BufferGeometryUtils.js`, and `OrbitControls.js`

The vendored core build retains its upstream SPDX license header. The Three.js
MIT license is available in the upstream project repository.
