# Plant Intelligence frontend (P041 dashboard)

React + Vite + TypeScript. Consumes the FastAPI backend — no analytics
logic lives here; Python is the source of truth.

## Run

```bash
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8001
npm install
npm run dev            # http://localhost:5173
```

Backend (separate terminal):

```bash
cd ../backend
PYTHONPATH=. ~/.venvs/plant-report-ai/bin/uvicorn app.main:app --port 8001
```

## Structure

- `src/services/api.ts` — typed API client (analytics, observations, reports)
- `src/components/` — KpiCard, TrendChart (dependency-free SVG), MachineTable,
  AnomalyPanel (severity filter), AiReport (status badge + markdown render)
- `src/pages/Dashboard.tsx` — sidebar layout, KPI cards, charts, report panel
