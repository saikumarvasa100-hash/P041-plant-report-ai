# P041 — Final Project Status (release freeze)

## Project goal

Automated report generation from plant data with LLMs: deterministic Python
analytics produce trusted facts; an LLM renders them as human-readable reports;
a React dashboard presents everything. Completed and frozen after full verification.

## Completed features

- Plant-data simulator (seeded, fault injection) + CSV ingestion with row-level errors
- Deterministic analytics: KPIs, half-split trends, threshold + z-score anomalies,
  machine comparison, self-validating thresholds
- LLM layer: OpenAI-compatible provider only, anti-hallucination prompt,
  structured numeric grounding (`numbers_verified`/`checked_count`/`mismatches`),
  central `report_generator` orchestration + CLI (`scripts/generate_report.py`,
  `--save` to `backend/data/reports/`), clean timeout/HTTP/malformed handling,
  no secret logging
- Dataset pipeline: synthetic JSONL generation + validation + adaptation manifest
- React dashboard: KPI cards, SVG trend charts with time axis, machine table,
  severity-filterable anomalies with keyboard-accessible drill-down modal,
  AI report panel (daily/weekly/monthly, type always matches content),
  Blob report download, session report history, demo-data controls with
  stale-request cancellation, backend-driven Demo/Live status badge

## Architecture

Plant Data → Validation → Analytics Engine → AnalyticsReport (trusted) →
LLM (narrative only) → Generated Report → React Dashboard.
See README for the full diagram. Details: `architecture.md`, `llm-integration.md`,
`model-adaptation.md`.

## Test status (actually executed, final pass)

- Backend: **78 passed, 0 failed** (`pytest -q`; includes orchestration, CLI stub-server, grounding, dataset, status, upload, from-analytics tests)
- Frontend: `npm run build` PASS (also from clean `node_modules` reinstall);
  `oxlint` 0 errors, 1 benign pre-existing warning (mount-time fetch effect)

## Frontend verification (headless Chromium, live servers — 20 checks, 20 pass)

Dashboard loads; KPIs match backend exactly; 4 charts with time ticks; machine
table; severity filter yields 18 critical; drill-down opens with full evidence and
Escape closes with focus restore; selector switch reloads matching report type;
Generate works against the configured provider with session history (select previous works);
status badge reads Live/unconfigured from backend; download yields dated markdown;
rapid demo-control changes settle on newest selection; zero overflow at 1400px
and 390px; zero page/console errors.

## Demo baseline (default 4/48/seed 7, from simulator + analytics, never hard-coded)

Production 16183 · Efficiency 78.17% · Energy 3435.55 kWh · Downtime 472.67 min ·
Anomalies 48 (18 critical, 9 high, 21 medium).

## Security status

No secrets in repo; no `.env` files; `.env` gitignored; errors expose status codes
only; CORS restricted to configured origins without credentials; dataset
validator rejects secret-like material.

## Demo instructions

```bash
cd ~/code/plant-report-ai/backend
PYTHONPATH=. ~/.venvs/plant-report-ai/bin/python -m uvicorn app.main:app --port 8001
cd ~/code/plant-report-ai/frontend
npm run dev   # http://localhost:5173
```

## Known limitations

Simulated/CSV data; demo thresholds need per-machine calibration; no persistent
database; synchronous report generation (demo scale); production narration needs
a live provider key (live HTTP tested with stubbed responses + one real 403 surfaced
cleanly, confirming error handling against the real Zen endpoint).

## Future scope

Sensors/PLC → MQTT → PostgreSQL → real-time → predictive maintenance →
energy optimization → plant assistant → scheduled reports. Fine-tuning path:
collect human-reviewed examples → manifest → external runner (not in repo).
