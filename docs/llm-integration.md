# LLM Integration

## Modes

- **Live** (`LLM_PROVIDER=openai-compatible` + key): real HTTP POST to
  `{LLM_BASE_URL}/chat/completions` with the configured model.
- **Unconfigured**: missing key or bad provider fails loudly (HTTP 500) —
  there is no offline fallback.

`GET /api/v1/reports/status` exposes `{provider, mode, model}`
(`live`/`unconfigured`) for UI badges. It never returns keys.

## Request flow

`POST /api/v1/reports/generate` → simulator data → `analyze_plant` →
`generate_report(analytics, type, settings)` → markdown + `numbers_verified`.

The user prompt embeds the full `AnalyticsReport` JSON. The system prompt
(`services/prompts.py`) orders: use only supplied data, never invent or alter
numbers, mark recommendations as recommendations. Temperature is fixed at 0.2.
Requests are synchronous by design (demo/small-scale); `LLM_TIMEOUT_S`
(default 60s) bounds upstream waits.

## Error handling (no secrets in any message)

| Condition | Result |
|---|---|
| Missing/placeholder key, bad provider | `LLMConfigurationError` → HTTP 500 |
| Timeout | `LLMError` ("timed out after Ns") → HTTP 502 |
| HTTP failure | `LLMError` with status code only → HTTP 502 |
| Malformed/empty response | `LLMError` → HTTP 502 |

Authorization headers and provider bodies are never logged.

## Numerical validation

`services/grounding.py::validate_report_numbers` checks every required figure
(core KPIs, severity counts, per-machine values, first-10 anomaly values) with
boundary-aware matching after thousands-separator normalization. Returns
`{numbers_verified, checked_count, mismatches}`. A mismatch means "not fully
reproduced", not "hallucinated" — live prose often omits figures that fully
enumerated renderers always print.
