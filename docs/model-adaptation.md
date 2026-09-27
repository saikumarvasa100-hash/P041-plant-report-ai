# Model Adaptation (future fine-tuning path)

## Dataset structure

One JSONL line per example (`backend/data/training/report_examples.jsonl`):

```json
{"report_type": "daily", "analytics": {...}, "target_report": "...",
 "source": "synthetic", "seed": 7}
```

Generate more with `scripts/generate_training_dataset.py` (seeds × machines ×
types); every line is grounding-validated before writing.

## Synthetic vs human-reviewed

- `synthetic`: provider-rendered from deterministic inputs, numbers
  grounding-validated per example. Silver standard.
- `human-reviewed`: written/approved by a person. None ship; required before any
  real training claim. `validate_training_dataset` refuses synthetic-only corpora
  as training-ready.

## Future fine-tuning workflow

1. `generate_dataset` → 2. `prepare_training_dataset` (valid/invalid split) →
3. `get_training_manifest` → 4. external runner + base model + GPU (out of scope).

## Why no training in the MVP

192 simulator rows are telemetry, not LM training data. The LLM narrates the
`AnalyticsReport` supplied per prompt, so no plant knowledge belongs in weights.
Training would cost more and weaken the verifiable analytics-then-narration
guarantee. **The project does not claim to have trained an LLM.**
