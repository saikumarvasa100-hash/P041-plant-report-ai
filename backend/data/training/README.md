# Training data (`backend/data/training/`)

## Synthetic vs human-reviewed

- **Synthetic** (`source: "synthetic"`): rendered through the configured provider
  from deterministic inputs. Numbers are grounding-validated per example, but
  these are *silver-standard examples, not ground truth*.
- **Human-reviewed** (`source: "human-reviewed"`): reports written or
  approved by a person. None ship with the repo; add them to use this
  corpus for anything beyond experimentation.

## Intended future fine-tuning usage

`app/services/model_adaptation.py` exposes `prepare_training_dataset`,
`validate_training_dataset`, and `get_training_manifest` — the honest
interface for a future fine-tuning run (external runner, base model,
GPU). Nothing here trains, downloads, or requires CUDA.

## Why the MVP does not train from scratch

192 simulator rows are telemetry, not language-model training data, and
the LLM never needs plant knowledge in weights: it narrates the
`AnalyticsReport` supplied in each prompt. Training would add cost and
risk while weakening the verifiable analytics-then-narration guarantee.
