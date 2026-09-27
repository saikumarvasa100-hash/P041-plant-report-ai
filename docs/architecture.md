# Plant Report AI — Architecture

## Workflow

Simulated Plant Data
  -> validation/processing (deterministic Python)
  -> KPI calculation (deterministic Python)
  -> trend analysis (deterministic Python)
  -> anomaly detection (deterministic Python)
  -> structured factual summary (JSON, validated)
  -> LLM (natural-language report ONLY, no numeric invention)
  -> Web Dashboard (React + Vite)
  -> daily/weekly/monthly reports + PDF/export

## Anti-hallucination rule

- Numerical KPIs and anomaly results MUST be calculated by deterministic Python code.
- The LLM receives structured validated results and renders human-readable narrative.
- The LLM must NOT invent numerical plant facts.

## Backend layout (`backend/app/`)

- `api/` — FastAPI routers (to be added: ingestion, KPIs, reports)
- `core/` — config, settings (env-based), logging
- `models/` — DB models (SQLite now, migratable to PostgreSQL)
- `schemas/` — Pydantic request/response schemas
- `services/` — deterministic analytics + LLM report service
- `main.py` — app entrypoint (health + `api/v1/data` + `api/v1/analytics` routers)

## Analytics engine (Stage 3, deterministic — Python = truth)

- `backend/app/services/analytics.py`: `calculate_plant_kpis`,
  `calculate_machine_kpis`, `analyze_trends` (half-split mean comparison),
  `detect_anomalies` (thresholds + per-machine z-score), `compare_machines`,
  `analyze_plant` -> `AnalyticsReport`.
- Models in `backend/app/schemas/analytics.py` (`PlantKPIs`, `MachineKPIs`,
  `TrendResult`, `Anomaly` with `low/medium/high/critical` severity,
  `AnalyticsReport`).
- Thresholds: `AnalyticsThresholds` (demo values calibrated to the
  simulator; needs real-equipment calibration). Efficiency is only flagged
  when the machine should produce (running/fault).
- API: `GET /api/v1/analytics/sample?machines=4&observations=48&seed=7`.

## Report generation (Stage 4 — AnalyticsReport -> LLM -> Report)

- `backend/app/services/llm.py`: `generate_report()` over the
  `openai-compatible` provider (configurable base URL / model / key,
  timeout + HTTP/malformed/empty handling, no key logging).
- `backend/app/services/prompts.py`: system prompt (10 anti-hallucination
  rules) + `build_user_prompt()` embedding the AnalyticsReport JSON.
- Numeric check: `numbers_preserved()` records whether key figures appear
  verbatim (`numbers_verified` in the response). Limitation: strict
  substring match, so a model that reformats numbers (e.g. "16,183")
  fails the check; live prose that reformats figures is honestly flagged.
- "The LLM is responsible for natural-language generation, while
  numerical analytics and anomaly detection are performed
  deterministically before LLM invocation."
- API: `POST /api/v1/reports/generate` (env-configured provider),
  `GET /api/v1/reports/sample` (configured provider),
  `GET /api/v1/reports/status` (provider/mode badge, no secrets).

## Config

- Secrets via env vars, see `backend/.env.example`.
- `DATABASE_URL` defaults to SQLite file in `backend/data/`.
