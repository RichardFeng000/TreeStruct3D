# Stage 7

This is an isolated Stage 7 project built from the 3DCodeBench text-to-3D
pipeline. It does not import or invoke StructGen3D and does not inherit any
Stage 2--6 prompts or generated outputs.

The baseline runner, rendering utilities, prompts, and benchmark inputs are
derived from [3DCodeBench](https://github.com/gaoypeng/3dcodebench), with local
changes for a separate structure-extraction phase, chronological flow logging,
and a pinned Blender 5.0 runtime. Runtime structural validation is supplied by the
sibling `../validation_test` project. The upstream Apache-2.0 license is
included in `LICENSE`.

## Active task prompts

- Structure extraction uses only
  `prompts/structure_extraction_surface_attachment_system_prompt.txt`.
- The previous extraction prompt remains unchanged at
  `prompts/structure_extraction_system_prompt.txt` as the reproducible baseline.
- Blender Python generation uses only
  `prompts/text_to_3d_system_prompt.txt`, copied unchanged from 3DCodeBench.
- No Stage 7 extra prompt is inserted into initial generation or repair user
  messages. The validated extraction JSON is supplied directly as ordinary
  user context; it is not a system prompt and does not use RAG.

## Pipeline

1. Extract and locally validate `<instance>/structure.json` using
   `structure_extraction_surface_attachment_system_prompt.txt`.
2. Load `benchmark/categories/<instance>/prompt_description.txt` and the
   validated structure JSON.
3. Send the original description plus structure JSON as one ordinary user
   message, while generation uses the unchanged `text_to_3d_system_prompt.txt`.
4. Generate a complete Blender 5.0 Python script.
5. Reject responses that fail Python syntax parsing.
6. Execute and render the script with the pinned Blender 5.0 binary.
7. Only after a render failure, send the traceback back for repair.
8. After every valid render, run `validation_test`'s Blender probe and score
   the parent/child tree, contact, anchor alignment, and explicitly authored
   shared anchors.
9. Send deterministic structural failures back for structural repair, then
   re-run Blender and `validation_test` before accepting the replacement.
10. Only after render and structural validation both pass, run visual feedback.
11. Re-run both Blender and `validation_test` after every visual code change.

The original 3DCodeBench system-prompt file is not modified by structural
validation. Structural diagnostics are supplied only in the user-side repair
request for the failed candidate.

No reference Python factory is read by the runner.

## Configuration

Both `run_stage7.py` and `extract_structure.py` now load their default local
configuration from:

```text
configs/gemma_4_31b.yaml
```

Local YAML files under `configs/` are ignored by Git because they contain API
credentials. To create another configuration, duplicate one of your local YAML
files and change its endpoint, model, and key. Select it explicitly, for example:

```bash
./run_stage7.sh --config configs/gemma_4_e2b.yaml ...
./extract_structure.sh --config configs/gemma_4_e2b.yaml ...
```

`--model` still overrides only the model ID after loading the selected YAML;
the endpoint, credential, and output-token settings continue to come from that
configuration file.

Native OpenAI Responses configurations use background mode by default whenever
the caller provides a response artifact path. The initial POST immediately
stores its response ID in a neighboring `*.background.json` sidecar, then the
runner polls the retrieve endpoint with short GET requests. Restarting the same
run resumes that ID instead of submitting and billing a duplicate task. Optional
YAML controls are:

```yaml
openai_background: true
openai_poll_interval: 5
openai_request_timeout: 60
```

`openai_request_timeout` applies to each short POST or GET connection, not to
the total model runtime. This mechanism applies only to `api_format:
openai_responses`; other providers keep their existing request behavior.

TokenPony's OpenAI-compatible Kimi K3 configuration is available at
`configs/kimi_k3.yaml`. Fill in `api_key`, then select it explicitly:

```bash
./extract_structure.sh \
  --config configs/kimi_k3.yaml \
  --output-prefix kimi_k3_ \
  --instances Chameleon_seed0 \
  --overwrite

./run_stage7.sh \
  --config configs/kimi_k3.yaml \
  --output-prefix kimi_k3_ \
  --instances Chameleon_seed0 \
  --overwrite
```

With `--output-prefix kimi_k3_`, the benchmark and structure input remain
`Chameleon_seed0`, while the result is written as
`../stage_results/stage7_output/kimi_k3_Chameleon_seed0/` with the canonical
`kimi_k3_Chameleon_seed0.py`. Its manifest remains inside that seed as
`run_manifest.json`, so an existing model run is not overwritten.
Use the same `--output-suffix '(1)'` on extraction and generation to keep a
second run as `kimi_k3_Chameleon_seed0(1)` without overwriting the first run.

The configuration uses `api_format: openai_chat_completions`, so Stage 7 sends
the `messages` and `stream: false` body expected by
`https://api.tokenpony.cn/v1/chat/completions`. The existing Gemma configuration
continues to use `api_format: lmstudio_responses` and its original request body.
For Kimi K3, structure extraction keeps high reasoning, while Blender code
generation uses low visible reasoning and a larger code-token allowance so the
response budget is spent on executable Python rather than an exposed design
diary. Model API timeout `0` means no client-side time limit.

## Structure extraction phase

Structure extraction is currently a separate pre-generation experiment. It
reads only `prompt_description.txt`, asks a planning model for one connected
parent/child blueprint, validates the tree locally, and saves JSON/Markdown.
It does not read benchmark Python. The validated JSON is then injected into
Blender-code generation as ordinary user context.

Run one extraction with the strongest model available in the configured API:

```bash
./extract_structure.sh \
  --model google/gemma-4-31b \
  --output-prefix gemma4_31b_ \
  --instances Chameleon_seed0 \
  --overwrite
```

All extraction artifacts are written only inside the model-specific Stage 7
seed directory. No `stage7_structure_extraction*` directory is created beside
`stage7_output`:

- `../stage_results/stage7_output/<prefix><instance>/structure_extraction/structure.json`
- `../stage_results/stage7_output/<prefix><instance>/structure_extraction/structure.md`
- `../stage_results/stage7_output/<prefix><instance>/structure_extraction/extraction_log.json`
- `../stage_results/stage7_output/<prefix><instance>/structure_extraction/structure_catalog.jsonl`

The extractor rejects missing parents, missing primary attachments, cycles,
unknown part ids, mismatched parent declarations, and incomplete anchor pairs.
Blueprint schema v2 also rejects a required shared attachment unless it has a
unique `shared_anchor_id`, the exact world-space equality invariant, and a rule
for recomputing both endpoints after geometry parameters change.

The unchanged 3DCodeBench generation system prompt is not extended. Instead,
the ordinary user message and structural-repair message carry one shared-anchor
implementation contract. It requires real retained Mesh connection samples,
explicit parent/child local anchors, world-space equality before parenting, and
recomputation on every full-script execution. The neutral helper pattern is
recognized by `validation_test` as an authored anchor pair; comments, proximity,
and `child.location` guesses are explicitly rejected.

Generated Stage7 scripts also implement the category-neutral native parameter
protocol `PART_PARAMS`. Concrete part ids are selected by the model rather than
prescribed by the prompt. The web editor replaces only literal values in this
dictionary, executes the complete source from an empty Blender 5.0 scene,
rebuilds geometry, recomputes both anchor endpoints, and then aligns and parents
children. Structural validation reruns every concrete part at scale `1.35` one
at a time. A relation is confirmed as a shared anchor only when the default
run, the parent-size perturbation, and the child-size perturbation all retain
real Mesh endpoint vertices and world-space equality.

## Run one smoke case

```bash
./run_stage7.sh \
  --model google/gemma-4-e2b \
  --instances Bird_seed0 \
  --overwrite \
  --render-samples 16 \
  --render-resolution 256
```

`run_stage7.sh` requires the matching extraction at
`../stage_results/stage7_output/<prefix><instance>/structure_extraction/structure.json`.
It revalidates that file before sending any generation request. Use the same
`--output-prefix` for extraction and generation.

All generated results are stored centrally under
`../stage_results/stage7_output/`.

Structural validation is enabled by default and resolves its evaluator from
`../validation_test`. Useful controls are:

```bash
--validation-test-root ../validation_test
--min-structure-score 85
--max-structure-retries 2
--structure-timeout 180
```

Important outputs:

- `../stage_results/stage7_output/<prefix><instance>/run_manifest.json`: prompt provenance.
- `../stage_results/stage7_output/<prefix><instance>/flow.log`: chronological flow.
- `../stage_results/stage7_output/<prefix><instance>/log.json`: structured history.
- `../stage_results/stage7_output/<instance>/structural_probe_attempt*.raw.json`:
  complete `validation_test` observations.
- `../stage_results/stage7_output/<instance>/structural_score_attempt*.json`:
  machine-readable score and exact error list.
- `../stage_results/stage7_output/<instance>/structural_score_attempt*.md`:
  concise readable report.
- `../stage_results/stage7_output/<instance>/renders/`: latest four renders.

The `stage7_output` root contains seed directories only; every run-specific
artifact remains inside its corresponding seed.
