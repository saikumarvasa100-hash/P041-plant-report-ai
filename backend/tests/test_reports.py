"""LLM report layer tests. No real network calls (httpx is stubbed)."""

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import LLMSettings
from app.main import app
from app.schemas.report import GeneratedReport, ReportRequest
from app.services import llm as llm_mod
from app.services.analytics import analyze_plant
from app.services.grounding import required_numbers, validate_report_numbers
from app.services.llm import (
    LLMConfigurationError,
    LLMError,
    generate_report,
)
from app.services.prompts import SYSTEM_PROMPT, build_user_prompt, key_numbers
from app.services.simulator import generate_plant_data

client = TestClient(app)

CANNED = "Canned provider report text."


def _stub_post(monkeypatch, text=CANNED):
    """Replace httpx.post with a canned chat-completions response."""

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": text}}]}

    monkeypatch.setattr(llm_mod.httpx, "post", lambda *a, **k: _Resp())


def _live_settings(**over):
    args = {"provider": "openai-compatible", "api_key": "test-key"}
    args.update(over)
    return LLMSettings(**args)


def _report():
    return analyze_plant(generate_plant_data(num_machines=2, observations_per_machine=8, seed=1))


def _clear_env(monkeypatch):
    for var in ("LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL"):
        monkeypatch.delenv(var, raising=False)


def test_prompt_generation():
    rep = _report()
    user = build_user_prompt(rep, "daily")
    assert "daily" in user
    assert str(rep.plant.total_production) in user  # analytics JSON embedded
    assert "Never invent measurements" in SYSTEM_PROMPT
    assert "exactly as given" in SYSTEM_PROMPT
    assert key_numbers(rep) == [
        str(rep.plant.total_production),
        str(rep.plant.average_efficiency),
        str(rep.plant.total_energy_kwh),
        str(rep.plant.total_downtime_minutes),
        str(len(rep.anomalies)),
    ]


def test_configured_provider_used(monkeypatch):
    rep = _report()
    _stub_post(monkeypatch)
    content, verified, provider, _ = generate_report(rep, "daily", _live_settings())
    assert content == CANNED
    assert provider == "openai-compatible"
    assert verified is False  # canned text omits figures; grounding is honest


def test_report_type_validation():
    with pytest.raises(ValueError):
        generate_report(_report(), "hourly", _live_settings())
    with pytest.raises(ValidationError):
        ReportRequest(report_type="hourly")  # type: ignore[arg-type]


@pytest.mark.parametrize("key", ["", "changeme", "  "])
def test_missing_api_key(key):
    with pytest.raises(LLMConfigurationError):
        LLMSettings(provider="openai-compatible", api_key=key).require_configured()


def test_analytics_report_passed_to_llm(monkeypatch):
    rep = _report()
    captured = {}

    def _fake(settings, system, user):
        captured["system"] = system
        captured["user"] = user
        return f"Report covering {rep.plant.total_production} units."

    monkeypatch.setattr(llm_mod, "_chat_completions", _fake)
    settings = LLMSettings(provider="openai-compatible", api_key="test-key")
    content, _, provider, _ = generate_report(rep, "daily", settings)
    assert provider == "openai-compatible"
    assert str(rep.plant.total_production) in captured["user"]
    assert "industrial plant reporting assistant" in captured["system"].lower()
    assert str(rep.plant.total_production) in content


def test_generated_report_schema():
    gen = GeneratedReport(
        report_type="monthly",
        generated_at="2026-09-26T00:00:00",
        reporting_period="x to y",
        content=CANNED,
        provider="openai-compatible",
        model="test-model",
    )
    assert gen.numbers_verified is False  # default
    assert gen.analytics_summary.total_production == 0  # default until API fills it


def test_sample_endpoint_needs_key(monkeypatch):
    _clear_env(monkeypatch)
    resp = client.get("/api/v1/reports/sample")
    assert resp.status_code == 500
    assert "LLM_API_KEY" in resp.json()["detail"]


def test_sample_endpoint_report_type_carried(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_API_KEY", "k")
    _stub_post(monkeypatch)
    for report_type in ("daily", "weekly", "monthly"):
        resp = client.get(f"/api/v1/reports/sample?report_type={report_type}&machines=2&observations=8&seed=1")
        assert resp.status_code == 200
        assert resp.json()["report_type"] == report_type


def test_status_endpoint_modes(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_API_KEY", "live-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    body = client.get("/api/v1/reports/status").json()
    assert body["mode"] == "live"
    assert body["model"] == "test-model"
    assert "key" not in str(body).lower()

    monkeypatch.delenv("LLM_API_KEY")
    assert client.get("/api/v1/reports/status").json()["mode"] == "unconfigured"


def test_real_request_construction(monkeypatch):
    rep = _report()
    captured = {}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "REPORT TEXT"}}]}

    def _fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return _Resp()

    monkeypatch.setattr(llm_mod.httpx, "post", _fake_post)
    settings = LLMSettings(
        provider="openai-compatible", api_key="k",
        model="test-model", base_url="https://example.com/v1",
    )
    content, verified, provider, model = generate_report(rep, "weekly", settings)
    assert content == "REPORT TEXT"
    assert captured["url"] == "https://example.com/v1/chat/completions"
    assert captured["headers"] == {"Authorization": "Bearer k"}
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["temperature"] == 0.2
    roles = [m["role"] for m in captured["json"]["messages"]]
    assert roles == ["system", "user"]
    system, user = (m["content"] for m in captured["json"]["messages"])
    assert "industrial plant reporting assistant" in system.lower()
    assert "never invent measurements" in system.lower()
    assert str(rep.plant.total_production) in user
    assert "weekly" in user


def test_grounding_verified_text():
    rep = _report()
    text = " ".join(str(v) for _, v in required_numbers(rep))
    result = validate_report_numbers(rep, text)
    assert result.numbers_verified is True
    assert result.mismatches == []
    assert result.checked_count > 5  # core KPIs + machines + anomalies


def test_grounding_catches_tampered_text():
    rep = _report()
    result = validate_report_numbers(rep, "unrelated text with no figures")
    assert result.numbers_verified is False
    assert len(result.mismatches) == result.checked_count
    assert any("plant.total_production" in m for m in result.mismatches)


def test_upstream_timeout(monkeypatch):
    def _timeout(*a, **k):
        raise httpx.TimeoutException("too slow")

    monkeypatch.setattr(llm_mod.httpx, "post", _timeout)
    settings = LLMSettings(provider="openai-compatible", api_key="k", timeout_s=1)
    with pytest.raises(LLMError, match="timed out"):
        generate_report(_report(), "daily", settings)


def test_connect_timeout_names_base_url(monkeypatch):
    def _timeout(*a, **k):
        raise httpx.ConnectTimeout("no route")

    monkeypatch.setattr(llm_mod.httpx, "post", _timeout)
    settings = LLMSettings(
        provider="openai-compatible", api_key="k", timeout_s=1, base_url="http://localhost:11434/v1"
    )
    with pytest.raises(LLMError) as exc:
        generate_report(_report(), "daily", settings)
    assert "http://localhost:11434/v1" in str(exc.value)
    assert "LLM_BASE_URL" in str(exc.value)


def test_transport_error_names_base_url_and_exception(monkeypatch):
    """A refused/DNS/TLS failure has no HTTP status; the old code said 'unknown'."""

    def _refused(*a, **k):
        raise httpx.ConnectError("[Errno 111] Connection refused")

    monkeypatch.setattr(llm_mod.httpx, "post", _refused)
    settings = LLMSettings(
        provider="openai-compatible", api_key="k", base_url="http://localhost:11434/v1"
    )
    with pytest.raises(LLMError) as exc:
        generate_report(_report(), "daily", settings)
    message = str(exc.value)
    assert "http://localhost:11434/v1" in message
    assert "ConnectError" in message
    assert "Connection refused" in message
    # The whole point: no more misleading "HTTP status: unknown".
    assert "unknown" not in message


def test_transport_error_never_leaks_api_key(monkeypatch):
    def _refused(*a, **k):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(llm_mod.httpx, "post", _refused)
    settings = LLMSettings(provider="openai-compatible", api_key="super-secret-key")
    with pytest.raises(LLMError) as exc:
        generate_report(_report(), "daily", settings)
    assert "super-secret-key" not in str(exc.value)


class _FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def raise_for_status(self):
        raise httpx.HTTPStatusError("err", request=None, response=self)

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


@pytest.mark.parametrize(
    "status,payload,expected",
    [
        (401, {"error": {"message": "No auth credentials found"}}, "No auth credentials found"),
        (402, {"error": {"message": "Insufficient credits"}}, "Insufficient credits"),
        (404, {"error": {"message": "No such model"}}, "No such model"),
        (429, {"error": "Rate limit exceeded"}, "Rate limit exceeded"),
        (500, None, "HTTP 500"),
    ],
)
def test_http_status_error_surfaces_provider_reason(monkeypatch, status, payload, expected):
    monkeypatch.setattr(
        llm_mod.httpx, "post", lambda *a, **k: _FakeResponse(status, payload, text="boom")
    )
    settings = LLMSettings(provider="openai-compatible", api_key="k")
    with pytest.raises(LLMError) as exc:
        generate_report(_report(), "daily", settings)
    message = str(exc.value)
    assert f"HTTP {status}" in message
    assert expected in message


def test_upstream_http_and_malformed(monkeypatch):
    class _BadStatus:
        status_code = 500

    class _HTTPResp:
        response = _BadStatus()

        def raise_for_status(self):
            raise httpx.HTTPStatusError("err", request=None, response=self.response)

    monkeypatch.setattr(llm_mod.httpx, "post", lambda *a, **k: _HTTPResp())
    settings = LLMSettings(provider="openai-compatible", api_key="k")
    with pytest.raises(LLMError, match="HTTP 500"):
        generate_report(_report(), "daily", settings)

    class _Malformed:
        def raise_for_status(self):
            return None

        def json(self):
            return {"no": "choices"}

    monkeypatch.setattr(llm_mod.httpx, "post", lambda *a, **k: _Malformed())
    with pytest.raises(LLMError, match="malformed"):
        generate_report(_report(), "daily", settings)

    class _Empty:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "   "}}]}

    monkeypatch.setattr(llm_mod.httpx, "post", lambda *a, **k: _Empty())
    with pytest.raises(LLMError, match="empty"):
        generate_report(_report(), "daily", settings)


def test_invalid_provider():
    settings = LLMSettings(provider="telepathy", api_key="k")
    with pytest.raises(LLMConfigurationError, match="Unsupported"):
        generate_report(_report(), "daily", settings)


def test_generate_endpoint_live_stubbed(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_API_KEY", "k")
    _stub_post(monkeypatch)
    resp = client.post(
        "/api/v1/reports/generate",
        json={"report_type": "daily", "machines": 2, "observations": 8, "seed": 1},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_type"] == "daily"
    assert body["content"] == CANNED
    assert body["analytics_summary"]["machine_count"] == 2
    assert body["provider"] == "openai-compatible"


def test_from_analytics_endpoint(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_API_KEY", "k")
    _stub_post(monkeypatch)
    analytics = analyze_plant(
        generate_plant_data(num_machines=2, observations_per_machine=8, seed=1)
    )
    resp = client.post(
        "/api/v1/reports/from-analytics",
        json={"analytics": analytics.model_dump(mode="json"), "report_type": "weekly"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["report_type"] == "weekly"
    assert body["content"] == CANNED
    assert body["analytics_summary"]["total_production"] == analytics.plant.total_production


def test_from_analytics_rejects_bad_body(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_API_KEY", "k")
    _stub_post(monkeypatch)
    resp = client.post(
        "/api/v1/reports/from-analytics",
        json={"analytics": {"plant": {"total_production": "lots"}}, "report_type": "daily"},
    )
    assert resp.status_code == 422


def test_generate_endpoint_bad_provider(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "telepathy")
    resp = client.post(
        "/api/v1/reports/generate",
        json={"report_type": "daily", "machines": 2, "observations": 8, "seed": 1},
    )
    assert resp.status_code == 500
    assert "Unsupported" in resp.json()["detail"]
