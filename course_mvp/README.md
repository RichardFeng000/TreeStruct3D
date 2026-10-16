# TreeStruct3D — CS 549 Assignment 3 MVP

This course slice regenerates a curated chair in Blender after a seat-width edit. Four legs and one backrest follow geometry-derived paired anchors. The browser loads a fresh GLB, synchronizes semantic-part selection, and reports the five declared connections. No cloud API or runtime AI key is required.

## Run from a fresh checkout

1. Install Python 3.9+ and official Blender 5.0. No pip/npm installation or frontend build is needed; Three.js and its loaders are vendored in `visual_validation/frontend/vendor/`.
2. Clone this repository and enter its root.
3. Set `TREESTRUCT3D_BLENDER` to your Blender executable if it is not on PATH. Examples:
   - macOS: `export TREESTRUCT3D_BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"`
   - Linux: `export TREESTRUCT3D_BLENDER=/path/to/blender`
   - Windows PowerShell: `$env:TREESTRUCT3D_BLENDER="C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"`
4. Run `python3 course_mvp/server.py` (Windows: `python course_mvp/server.py`).
5. Open **http://127.0.0.1:8876/course_mvp/** in a modern WebGL browser. Keep the terminal running. Stop with Ctrl+C. If 8876 is occupied, stop the previous instance first.

The default preview is generated automatically. Try **0.8×**, **1.2×**, select parts in the tree or viewport, toggle anchors/default outline, then enable **Deliberately break attachments** and regenerate. Normal cases should show 5/5 passes; the fault control should show 0/5. The backrest width is derived from seat width.

## Validation and evidence

`chair.py` starts from Blender's factory scene, builds six semantic mesh objects, obtains face anchors from actual vertex bounds, and recomputes dependent translations. BVH nearest-surface queries independently verify anchor membership. World-space anchor distances check alignment. For this axis-aligned cuboid fixture, interval separation gives surface contact; this is not a general-purpose arbitrary-mesh contact solver. The default and 0.8×/1.2× states are independently regenerated. Child-parameter perturbation and the research validator's full acceptance protocol are not implemented in this course adapter.

`server.py` limits width to [0.5, 2.0], serializes Blender work, and writes `course_mvp/measurements.jsonl`; every result includes width, bounds, endpoint coordinates, per-link checks and subprocess latency. Latency excludes network/GLB reload, so it is a lower bound on full edit-to-preview latency. Geometry-change flag compares width to default, supported by exported seat bounds; no generic mesh-change metric is claimed.

**Stress test:** choose 1, 100, 500, 1,000 or 2,000 independent chair copies and measure five seconds. Offscreen culling is disabled for the copies so geometry submission increases even outside the camera view. This intentionally stresses draw calls; it does not measure Blender scalability or physically simulate 2,000 chairs. FPS is requestAnimationFrame throughput, not GPU timer-query timing. Record viewport, browser and hardware alongside results. Export raw evidence with **Export FPS evidence**.

**Record 150-second demo** records the actual live WebGL canvas at up to 30 FPS, adds explanatory overlays, and automatically demonstrates edits, failure control and stress load. The recording is saved under `course_mvp/evidence/demo.webm` and also offered as a WebM download. Recording adds overhead, so distinguish recording-time FPS from separate measurements. Convert to MP4 with `ffmpeg -i TreeStruct3D-Assignment3-Demo.webm -c:v libx264 -pix_fmt yuv420p demo.mp4` if needed. Upload to YouTube/Vimeo for the required video link.

## Source layout

- `chair.py`: curated procedural fixture and geometric checks.
- `server.py`: local Python HTTP service and Blender subprocess.
- `index.html`, `app.js`: Three.js viewer, controls, stress measurements and real-time demo recorder.
- Vendored graphics modules: `../visual_validation/frontend/vendor/`.

Generated GLBs, logs and cache directories are ignored by Git. Existing AI-generated research assets remain in `visual_validation/datasets/stage1_output/`; this deterministic course chair is hand-curated with AI coding assistance. This demo does not claim new runtime VLM generation.
