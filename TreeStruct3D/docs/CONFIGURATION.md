# Model API configuration

TreeStruct3D treats the YAML selected by `--config` as the only user-facing
source of model API settings. Both model-facing commands load the same schema:

```bash
./extract_structure.sh --config config.local.yaml --instances Bird_seed0
./generate_3d.sh --config config.local.yaml --instances Bird_seed0
```

Start from the complete tracked template:

```bash
cp configs/config.example.yaml config.local.yaml
export TREESTRUCT3D_API_KEY=your-api-key
```

`config.local.yaml` is ignored by Git. Keep the environment-variable reference
in the YAML instead of writing a reusable credential directly into the file.
The `${TREESTRUCT3D_API_KEY}` value is resolved when the configuration is
loaded; an unset or empty variable is reported as a missing required key.

## Field reference

| Field | Required | Default if omitted | Meaning |
| --- | --- | --- | --- |
| `api_format` | Yes | — | Request and response protocol. See the supported values below. |
| `api_url` | Yes | — | Complete endpoint used for model requests. |
| `api_key` | Yes | — | Literal credential or a whole-value `${ENVIRONMENT_VARIABLE}` reference. |
| `model` | Yes | — | Provider model identifier used by both pipeline phases. |
| `max_output_tokens` | No | `null` | Shared output-token cap; `null` omits the provider field. |
| `reasoning_effort` | No | `null` | Shared provider-specific reasoning or thinking level. |
| `api_timeout_seconds` | No | `0` | Foreground API wall-clock limit; `0` means no client-side limit. |
| `api_retries` | No | `0` | Retries for transport failures known to be safe to repeat. |
| `extraction_retries` | No | `2` | Additional structure attempts after exhausted safe API retries or invalid output. |
| `generation_retries` | No | `2` | Additional initial code attempts after exhausted safe API retries or invalid code. |
| `request_delay_seconds` | No | `0.0` | Delay between completed benchmark instances. |
| `structure_max_output_tokens` | No | `null` | Structure-extraction token override; `null` inherits the shared value. |
| `structure_reasoning_effort` | No | `null` | Structure-extraction reasoning override. |
| `code_max_output_tokens` | No | `null` | Initial code-generation token override. |
| `code_reasoning_effort` | No | `null` | Initial code-generation reasoning override. |
| `structure_repair_max_output_tokens` | No | `null` | Structural-repair token override; `null` inherits the code value. |
| `structure_repair_reasoning_effort` | No | `null` | Structural-repair reasoning override. |
| `openai_background` | No | `true` | Submit resumable background responses when using `openai_responses`. |
| `openai_poll_interval` | No | `5.0` | Seconds between background-response polls. |
| `openai_request_timeout` | No | `60` | Per-request timeout used to submit and poll a background response. |

The complete template declares every field explicitly. The loader validates
required values, numeric ranges, booleans, supported protocols, and unresolved
credential placeholders before any model request is submitted. Unsupported
keys are reported and ignored so older private profiles remain diagnosable.

## Supported protocols

Change the required provider block at the top of `config.local.yaml`; leave the
shared policy and phase overrides below it in place.

### LM Studio responses

```yaml
api_format: lmstudio_responses
api_url: http://127.0.0.1:1234/api/v1/chat
api_key: ${TREESTRUCT3D_API_KEY}
model: your-loaded-model-id
```

### OpenAI Responses-compatible endpoint

```yaml
api_format: openai_responses
api_url: https://api.openai.com/v1/responses
api_key: ${TREESTRUCT3D_API_KEY}
model: your-model-id
```

This protocol is the only one that reads the three `openai_*` settings.
When background mode is enabled, `openai_request_timeout` limits each submit or
poll HTTP operation; the durable poll loop can continue beyond the foreground
`api_timeout_seconds` value until the provider returns a terminal status.

### OpenAI Chat Completions-compatible endpoint

```yaml
api_format: openai_chat_completions
api_url: https://your-provider.example/v1/chat/completions
api_key: ${TREESTRUCT3D_API_KEY}
model: your-model-id
```

### Gemini generateContent endpoint

```yaml
api_format: gemini_generate_content
api_url: https://generativelanguage.googleapis.com/v1beta/models/your-model-id:generateContent
api_key: ${TREESTRUCT3D_API_KEY}
model: your-model-id
```

## Configuration boundary

`--config` selects the file. Model identity, API timeout, transport retries,
phase-level model attempts, and inter-instance request delay have no
command-line overrides. This keeps one reproducible request policy across
structure extraction, generation, structural repair, and visual feedback.

`api_retries` governs safe transport retries inside every model-facing phase.
`extraction_retries` and `generation_retries` govern another complete initial
attempt after the transport policy is exhausted or model output is invalid.
Render, structural-validation, and visual-repair limits remain ordinary
pipeline options because they do not configure the model API.
