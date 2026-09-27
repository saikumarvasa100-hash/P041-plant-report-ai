"""Central orchestration + CLI tests. Provider HTTP is stubbed locally."""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from app.core.config import LLMSettings
from app.services import llm as llm_mod
from app.services.analytics import analyze_plant
from app.services.report_generator import generate_daily_report, generate_plant_report
from app.services.simulator import generate_plant_data

ROOT = Path(__file__).resolve().parents[2]
# The CLI lives outside backend/ at repo level. It is absent when only the
# backend package is distributed, so these two tests declare that dependency
# rather than failing on a missing sibling file.
CLI = ROOT / "scripts" / "generate_report.py"
requires_cli = pytest.mark.skipif(
    not CLI.is_file(), reason="scripts/generate_report.py not present in this distribution"
)
CANNED = "# Stubbed Report\n\nStubbed provider body."

SETTINGS = LLMSettings(provider="openai-compatible", api_key="k")


def _analytics():
    return analyze_plant(
        generate_plant_data(num_machines=2, observations_per_machine=8, seed=1)
    )


@pytest.fixture()
def stub_transport(monkeypatch):
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": CANNED}}]}

    monkeypatch.setattr(llm_mod.httpx, "post", lambda *a, **k: _Resp())


@pytest.mark.parametrize("report_type", ["daily", "weekly", "monthly"])
def test_generate_plant_report_types(stub_transport, report_type):
    rep = generate_plant_report(_analytics(), report_type, SETTINGS)
    assert rep.report_type.value == report_type
    assert rep.content == CANNED
    assert rep.provider == "openai-compatible"
    assert rep.analytics_summary.machine_count == 2


def test_generate_daily_report_defaults(stub_transport):
    rep = generate_daily_report(settings=SETTINGS)
    assert rep.analytics_summary.machine_count == 4
    assert rep.analytics_summary.total_production == 16183


def test_generate_plant_report_bad_type(stub_transport):
    with pytest.raises(ValueError):
        generate_plant_report(_analytics(), "hourly", SETTINGS)


class _StubHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        body = json.dumps({"choices": [{"message": {"content": CANNED}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def stub_server():
    server = HTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _cli_env(stub_server):
    return dict(
        os.environ,
        LLM_PROVIDER="openai-compatible",
        LLM_API_KEY="test-key",
        LLM_MODEL="stub-model",
        LLM_BASE_URL=stub_server,
        PYTHONPATH=str(ROOT / "backend"),
    )


@requires_cli
def test_cli_live_stub_report(stub_server):
    proc = subprocess.run(
        [sys.executable, str(CLI),
         "--machines", "2", "--observations", "8", "--seed", "1"],
        capture_output=True, text=True, env=_cli_env(stub_server), timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "# Stubbed Report" in proc.stdout
    assert "provider=openai-compatible model=stub-model" in proc.stdout
    assert "sk-" not in proc.stdout and "test-key" not in proc.stdout


@requires_cli
def test_cli_save_report_file(stub_server):
    proc = subprocess.run(
        [sys.executable, str(CLI),
         "--machines", "2", "--observations", "8", "--seed", "1", "--save"],
        capture_output=True, text=True, env=_cli_env(stub_server), timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    reports = sorted((ROOT / "backend" / "data" / "reports").glob("plant-report-*.md"))
    assert reports, "expected a saved markdown report"
    assert reports[-1].read_text().startswith("# Stubbed Report")
    meta = json.loads((reports[-1].parent / (reports[-1].stem + ".meta.json")).read_text())
    assert meta["provider"] == "openai-compatible"
    assert "api_key" not in json.dumps(meta).lower()
    for p in reports[-1].parent.glob("plant-report-*.m*"):
        p.unlink()
