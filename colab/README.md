# Driving the P041 pipeline from opencode through Colab (colab-mcp)

Bridges your local opencode agent to a Google Colab runtime so the
plant-report-ai pipeline runs in the browser session and the agent can feed it
local files, run it, and bring the report back.

```
opencode (local)  --MCP-->  colab-mcp (local proxy, uvx)  --websocket-->
Colab notebook runtime (this folder's .ipynb)  --exposes-->  pipeline cells
```

## 1. Config (already done)

`~/.config/opencode/opencode.jsonc` now includes:

```jsonc
"colab-mcp": {
  "type": "local",
  "command": ["uvx", "git+https://github.com/googlecolab/colab-mcp"],
  "enabled": true
}
```

Prerequisites on this machine (done):
- `uv` installed at `~/.local/bin/uv` (official installer; colab-mcp launches via `uvx`).

After any config change, restart the opencode session so the server starts.

## 2. Connect flow (one time per session)

1. Start opencode and open the `colab-mcp` server tool list
   (`tools/list` -> `colab-mcp.open_colab_browser_connection`).
2. Call `open_colab_browser_connection` — a browser tab opens for Google
   sign-in; pick the notebook runtime for `p041_colab_pipeline.ipynb`
   (open the notebook in Colab first, Runtime > Run all for cells 1–6).
3. Once connected, the bridge proxies the runtime; the agent can execute
   pipeline code against the live kernel.

> The notebook uses cells 1–6 as plain callable functions, so this works with
> whatever execution-style tool the bridge exposes. Cell 8 additionally
> registers named tools (`p041_run_pipeline`, `p041_ingest`) where the runtime
> supports registered tools.

## 3. Ingestion (local files -> runtime)

| Source | How | Notebook entry |
|---|---|---|
| Local CSV (MCP) | Agent reads the file, base64-encodes it, calls `ingest_base64_csv(b64, "ai4i.csv")` | `ingest_base64_csv` |
| Google Drive | Mount Drive, drop CSVs in MyDrive | `ingest_drive("plant_data.csv")` |
| Simulator | Deterministic demo data (no upload) | `simulate(4, 48, 7)` |

Kaggle CSVs: pass the dataset profile so columns map onto the native schema,
e.g. `run_pipeline(csv_path=..., profile="ai4i")` (profiles: `generic`,
`ai4i`, `iot-fault`, `iiot-timeseries`, `smart-factory`, `azure`).

## 4. Pipeline representation in the notebook

| Stage | Notebook cell / function | Notes |
|---|---|---|
| Setup | cell 1 | `pip install` fastapi, uvicorn, httpx, python-multipart, pydantic, fastmcp |
| Backend | cell 2 | `backend/app` expected at `/content/p041/backend/app` (agent pushes it via the bridge, or copy through Drive) |
| Ingest | cell 3 | base64 / Drive / simulator |
| LLM config | cell 4 | Colab secrets (`LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`) or env; `demo-stub` fallback |
| Validate + Analytics + LLM + Report | cells 5–6 | `run_pipeline(...)` -> `save_report(...)` |

`run_pipeline(use_stub=True)` is a keyless demo path (clearly labeled
`demo-stub`, no network). Live mode uses the real OpenAI-compatible provider.

## 5. LLM provider inside Colab

Set Colab secrets (key icon in the left panel) so keys never appear in the
notebook:

- OpenRouter: `LLM_BASE_URL=https://openrouter.ai/api/v1`
- Groq: `LLM_BASE_URL=https://api.groq.com/openai/v1`
- Ollama on your laptop: not reachable from the Colab VM — tunnel it
  (e.g. Cloudflare quick tunnel) and use that URL.

## 6. Getting the report back

`save_report(...)` returns `{content, path, content_b64, provider, model,
numbers_verified, ...}`. The agent decodes `content_b64` and writes the
markdown to the local repo, e.g.
`/home/vasa/code/plant-report-ai/backend/data/reports/plant-report-<date>.md`
(mirroring `scripts/generate_report.py --save`).

## 7. Files

- `p041_colab_pipeline.ipynb` — the runtime notebook (9 cells, this README's contract).
- The pipeline source stays in `backend/app/` (single source of truth; the
  notebook imports it rather than duplicating logic).
