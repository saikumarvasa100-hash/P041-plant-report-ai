# P041 — Automated Report Generation from Plant Data with LLMs

Our system uses deterministic industrial analytics to calculate trusted plant insights
and an LLM to automatically convert those insights into accurate, human-readable
performance reports.

## Problem statement

Industrial plants generate large volumes of operational data, but turning that data
into useful daily/weekly/monthly reports is still a slow manual process. Feeding raw
plant data straight into an LLM is unreliable: models can miscalculate KPIs or invent
measurements.

## Solution overview

Plant data → validation → deterministic analytics (KPIs, trends, anomalies) →
trusted `AnalyticsReport` → LLM (narrative only) → human-readable industrial report →
React dashboard. Our deterministic analytics engine calculates the facts, and the LLM
communicates those facts.

## Architecture

```
                    PLANT DATA (simulator / CSV)
                               |
                    +----------v----------+
                    |  Validation         |  Pydantic schemas, row-level CSV errors
                    +----------+----------+
                               |
                    +----------v----------+
                    |  Analytics Engine   |  deterministic Python (no LLM, no ML)
                    |  - KPI calculation  |
                    |  - Trend analysis   |  half-split mean comparison
                    |  - Anomaly detection|  thresholds + z-score
                    |  - Machine analysis |
                    +----------+----------+
                               |
                     AnalyticsReport (TRUSTED DATA)
                               |
                    +----------v----------+
                    |  LLM Service        |  narrative generation only
                    |  OpenAI-compatible  |
                    +----------+----------+
                               |
                     Generated Report (8-section markdown)
                               |
                    +----------v----------+
                    |  React Dashboard    |  KPIs, charts, anomalies, AI report
                    +---------------------+
```

Anti-hallucination rule: numerical KPIs/anomalies are computed by deterministic
Python; the LLM only renders narrative from validated JSON. A numeric-preservation
check records whether key figures survived verbatim (`numbers_verified`).

## Technology stack

Backend: Python, FastAPI, Pydantic, httpx.
Frontend: React, TypeScript, Vite, custom SVG charts (no chart library).
AI: configurable OpenAI-compatible LLM (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`).
Tests stub the HTTP layer, so the suite runs fully offline.
Data: CSV ingestion with row-level validation; deterministic seeded simulator;
SQLite-ready architecture (`DATABASE_URL`).
Testing: pytest (backend).

## Repository structure

```
plant-report-ai/
├── backend/
│   ├── app/
│   │   ├── api/        # FastAPI routers: data, analytics, reports
│   │   ├── core/       # env config (LLM, CORS), shared exceptions
│   │   ├── models/     # DB-model layer (re-exports schemas for now)
│   │   ├── schemas/    # Pydantic: plant, analytics, report
│   │   ├── services/   # simulator, ingestion, analytics, prompts, llm
│   │   └── main.py     # app entrypoint + router wiring
│   ├── data/           # sample_plant_data.csv
│   ├── tests/          # pytest suite
│   ├── requirements.txt
│   └── .env.example
├── frontend/           # React + Vite + TypeScript dashboard
│   ├── src/
│   │   ├── components/ # KpiCard, TrendChart, MachineTable, AnomalyPanel, AiReport
│   │   ├── pages/      # Dashboard
│   │   └── services/   # typed FastAPI client (VITE_API_BASE_URL)
│   ├── .env.example
│   └── package.json
├── docs/               # architecture.md, final-status.md
├── scripts/            # dev_backend.sh, generate_sample_data.py
├── README.md
└── .gitignore
```

## Setup requirements

- Python 3.12+ with a virtualenv (project venv: `~/.venvs/plant-report-ai`)
- Node.js 20+ and npm (note: Vite 8 officially wants Node 20.19+; 20.15 works with a warning)
- No API key needed for demo mode

## Backend setup

```bash
cd ~/code/plant-report-ai/backend
python3 -m venv ~/.venvs/plant-report-ai
~/.venvs/plant-report-ai/bin/pip install -r requirements.txt
```

Run (Terminal 1, port 8001):

```bash
cd ~/code/plant-report-ai/backend
PYTHONPATH=. ~/.venvs/plant-report-ai/bin/python -m uvicorn app.main:app --port 8001
```

(`scripts/dev_backend.sh` runs the same with `--reload`.)

## Frontend setup

```bash
cd ~/code/plant-report-ai/frontend
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8001
npm install
npm run dev            # http://localhost:5173
```

## Demo mode

Run the backend with a configured provider (see below) and open the dashboard:
every feature — KPIs, charts, anomalies, Generate Report for daily/weekly/monthly —
runs against the live pipeline. The UI badge shows the backend-reported mode
(`Live LLM` vs `LLM not configured`); provider output is never presented without
its source label.

## LLM provider configuration (live mode)

```bash
cp backend/.env.example backend/.env   # then edit: LLM_API_KEY, LLM_MODEL, LLM_BASE_URL
```

Any OpenAI-compatible provider works; only the base URL and model ID change
(client appends `/chat/completions` itself). Examples:

- OpenRouter: `LLM_BASE_URL=https://openrouter.ai/api/v1`
- Groq: `LLM_BASE_URL=https://api.groq.com/openai/v1`
- Ollama (local): `LLM_BASE_URL=http://localhost:11434/v1`

## CLI report generation (no dashboard needed)

```bash
LLM_PROVIDER=openai-compatible LLM_API_KEY=... LLM_MODEL=... LLM_BASE_URL=... \
  PYTHONPATH=backend python scripts/generate_report.py --type weekly
LLM_PROVIDER=openai-compatible LLM_API_KEY=... LLM_MODEL=... LLM_BASE_URL=... \
  PYTHONPATH=backend python scripts/generate_report.py --save  # + writes backend/data/reports/
```

The command calls the real provider and prints `numbers_verified` plus
provider/model info (never API keys).

## Environment variables

Backend (`backend/.env`):

| Variable | Purpose | Default |
|----------|---------|---------|
| `LLM_PROVIDER` | `openai-compatible` | `openai-compatible` |
| `LLM_API_KEY` | provider API key (never commit) | empty (generation then reports unconfigured) |
| `LLM_MODEL` | model name | `qwen2.5:7b-instruct-q4_K_M` |
| `LLM_BASE_URL` | OpenAI-compatible base URL | `http://localhost:11434/v1` |
| `LLM_TIMEOUT_S` | upstream timeout, seconds | `60` |
| `DATABASE_URL` | reserved for future persistence | sqlite path |
| `CORS_ORIGINS` | allowed browser origins, comma-separated | `http://localhost:5173` |

Frontend (`frontend/.env`):

| Variable | Purpose | Default |
|----------|---------|---------|
| `VITE_API_BASE_URL` | FastAPI base URL | `http://localhost:8001` |

`.env` files are gitignored. Request handling is synchronous by design (demo/small-scale
usage); upstream timeouts and HTTP failures return clean errors without secrets.

## API endpoints

| Method | Endpoint | Purpose | Key parameters |
|--------|----------|---------|----------------|
| GET | `/health` | Liveness check | — |
| GET | `/api/v1/data/sample` | Generated plant observations | `machines` (1–10), `observations` (1–200), `seed` |
| GET | `/api/v1/data/profiles` | Upload dataset profiles | — |
| POST | `/api/v1/data/upload` | Upload + map + validate + analyze a CSV (multipart `file`, `profile` query) | `profile`: generic, ai4i, iot-fault, iiot-timeseries, smart-factory, azure |
| GET | `/api/v1/analytics/sample` | Deterministic analytics report | `machines` (1–10), `observations` (4–500), `seed` |
| GET | `/api/v1/reports/sample` | Sample AI report (configured provider) | `report_type`, `machines`, `observations`, `seed` |
| GET | `/api/v1/reports/status` | Provider status (no secrets) | — |
| POST | `/api/v1/reports/generate` | AI report via configured provider | body: `report_type` (daily/weekly/monthly), `machines`, `observations`, `seed` |

## Dataset generation

```bash
PYTHONPATH=backend ~/.venvs/plant-report-ai/bin/python scripts/generate_training_dataset.py \
  --seeds 7 11 21 --machines 2 4 --types daily weekly monthly --observations 24
```

Writes validated synthetic examples to `backend/data/training/report_examples.jsonl`
(see `backend/data/training/README.md` for synthetic vs human-reviewed).

## Model adaptation / fine-tuning path

`app/services/model_adaptation.py` (`prepare_training_dataset`,
`validate_training_dataset`, `get_training_manifest`) defines the honest
interface for future domain fine-tuning with no GPU/training dependencies.
See `docs/model-adaptation.md`.

**Report generation requires a configured live provider. Tests stub the HTTP
layer, so the suite stays offline. The current prototype does not train an LLM
from scratch. A dataset-generation and model-adaptation interface is provided
for future domain fine-tuning.**

## Manual data upload (your own Kaggle CSVs)

No data is preloaded — download CSVs yourself (free Kaggle account) and upload
through the dashboard's Upload panel or directly:

```bash
curl -X POST 'http://localhost:8001/api/v1/data/upload?profile=ai4i' \
  -F 'file=@ai4i_predictive_maintenance.csv'
```

**Check which profile fits before uploading** (offline, no server needed):

```bash
~/.venvs/plant-report-ai/bin/python scripts/check_dataset.py ~/Downloads/your.csv
```

It scores all profiles, ranks them, and prints the exact `curl` to use.

Profiles: `generic` (native schema), `ai4i`, `iot-fault`, `iiot-timeseries`,
`smart-factory`, `azure` (see `GET /api/v1/data/profiles`). Columns are
alias-matched, every mapped row passes the same Pydantic validation, and any
field the source file doesn't measure is labeled DERIVED in the response —
never claimed as a measurement. Invalid rows return HTTP 422 with
row/field/reason details; files are never stored (5 MB limit).

**A wrong profile is refused, not guessed.** Each profile declares the column
groups it needs; a file that cannot feed it returns HTTP 422 naming the missing
groups and the columns actually present. This matters: without that check a
native CSV uploaded as `ai4i` maps to zeros and constants (120 units → 0,
71.4 °C → -273.15 °C) and those invented values would flow into the KPIs,
charts, anomaly detection and the LLM report as measurements.

Known limitation: the published LBNL/Azure files ship in long `telemetry` form
(`datetime, machine, component, Value`) and need pivoting to the wide form
first. The `azure` profile expects the wide form and will refuse the long one
with an explanation.

## Demo workflow (under 2 minutes)

1. Open `http://localhost:5173` — KPI cards show backend-calculated values.
2. Scroll to charts (production/efficiency/energy/downtime with backend trend labels).
3. Open Anomalies, filter by severity, click a row for the evidence detail modal.
4. In AI Reports, pick daily/weekly/monthly and click Generate (requires a configured provider key).
5. Download Report saves the displayed markdown as `plant-report-YYYY-MM-DD.md`.
6. Demo Data controls (machines 2/3/4, observations 24/48/72, seed) reload all panels.

Default demo baseline (4 machines, 48 observations, seed 7): production 16183,
efficiency 78.17%, energy 3435.55 kWh, downtime 472.67 min, 48 anomalies
(18 critical). These arise from the simulator + analytics, never hard-coded.

## Testing commands

```bash
cd ~/code/plant-report-ai/backend
PYTHONPATH=. ~/.venvs/plant-report-ai/bin/pytest -q
cd ../frontend
npm run build
npm run lint
```

## Known limitations

- Prototype data is simulated + CSV; anomaly thresholds are demonstration values
  needing per-machine calibration.
- Report endpoints serve generated sample data; no persistent database yet
  (service boundaries are persistence-ready).
- Report generation is synchronous (demo scale, not multi-user production).
- Production-quality narration needs a configured live LLM provider.

## Future scope

Real sensors/PLC → MQTT/industrial protocols → PostgreSQL → real-time monitoring →
predictive maintenance → energy optimization → conversational plant assistant →
scheduled automated reports.
