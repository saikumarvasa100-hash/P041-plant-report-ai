# Frontend Handoff Brief (paste to ChatGPT)

## What this is

P041 — Automated Report Generation from Plant Data with LLMs. A hackathon MVP:
FastAPI backend does deterministic plant analytics; an LLM narrates verified
results; this React dashboard presents everything. Working code, verified in a
real browser — improve it, don't rebuild it.

## Stack & commands

React 19 + TypeScript + Vite 8 + custom CSS (`src/index.css`, no UI framework,
no chart library). Node 20+.

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
npm run build   # must pass (tsc + vite)
npm run lint    # oxlint, must stay 0 errors
```

Backend it talks to (already running for you at `VITE_API_BASE_URL`):

- `GET /api/v1/analytics/sample?machines=4&observations=48&seed=7` → KPIs, trends, machines, anomalies
- `GET /api/v1/data/sample?...` → raw observations (chart series only)
- `GET /api/v1/data/profiles` → upload dataset profiles
- `POST /api/v1/data/upload?profile=<id>` (multipart `file`) → mapped + validated observations + analytics
- `GET /api/v1/reports/sample?...&report_type=daily` → AI report (needs provider key server-side)
- `POST /api/v1/reports/generate` / `POST /api/v1/reports/from-analytics` → AI report
- `GET /api/v1/reports/status` → `{provider, mode, model}` for the badge; never any keys

## File map

- `src/services/api.ts` — typed client + `DemoParams`; base URL ONLY from `VITE_API_BASE_URL`
- `src/pages/Dashboard.tsx` — layout, data loading (AbortController-guarded), demo controls
- `src/components/` — `KpiCard`, `TrendChart` (dependency-free SVG), `MachineTable`,
  `AnomalyPanel` (severity filter + detail modal), `AiReport` (report + history + download),
  `UploadPanel` (manual Kaggle CSV upload)
- `src/index.css` — entire visual system (see `DESIGN.md` for art direction + tokens)
- `index.html` — fonts (Barlow Condensed / Barlow / JetBrains Mono, display=swap)

## Hard rules (from the project owner)

1. Python backend is the source of truth — NO analytics math in JS (mean-per-timestamp
   display aggregation in charts is the only exception).
2. Keep the CSS class API stable unless you update every consumer.
3. No new runtime dependencies without a stated reason.
4. Every number shown must come from an API response; never invent metrics.
5. Keep: keyboard support (Enter/Space open, Escape closes modal, visible focus),
   responsive down to 390px with zero horizontal overflow, loading/error/empty states.
6. No color-emoji glyphs (target machines lack emoji fonts); no secret handling —
   the frontend never sees API keys.

## Current design (see DESIGN.md)

Control-room console: deep slate-teal, mono readouts, condensed KPI numerals,
numbered panel sections, lamp-dot brand. Verified via headless-Chromium
screenshots (desktop 1400px, mobile 390px, modal).

## Ask it for

Pick ONE per round: (a) visual polish within DESIGN.md tokens, (b) a named new
panel with exact data source, or (c) an accessibility pass. Ask for: file-by-file
diffs, build+lint output, and what it checked in a browser (or what it couldn't).
