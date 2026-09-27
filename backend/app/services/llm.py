"""LLM report service: AnalyticsReport -> human-readable markdown report.

Architecture: ``AnalyticsReport -> LLM -> Report``. The LLM never computes
plant numbers; it renders narrative from trusted JSON. A structured
numeric-grounding check records whether key figures survived verbatim.

Provider: ``openai-compatible`` — HTTP POST to ``{base_url}/chat/completions``.
There is no offline renderer: unconfigured providers fail loudly.

No API keys, auth headers, or provider bodies are ever logged.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import LLMSettings
from app.core.exceptions import LLMConfigurationError
from app.schemas.analytics import AnalyticsReport
from app.services.grounding import validate_report_numbers
from app.services.prompts import SYSTEM_PROMPT, build_user_prompt

REPORT_TYPES = ("daily", "weekly", "monthly")


class LLMError(RuntimeError):
    """Upstream LLM failure (timeout, HTTP error, bad/empty response)."""


__all__ = ["LLMConfigurationError", "LLMError"]


def _provider_error_detail(response: httpx.Response) -> str:
    """Best-effort provider error text (e.g. 'No auth credentials found').

    Providers put the actionable reason in the body: 401 for a bad key, 402 for
    no credit, 404 for a wrong model id. Falls back to a truncated raw body.
    Never includes request headers, so the key cannot leak.
    """
    try:
        data = response.json()
    except Exception:  # noqa: BLE001 - body parsing is best-effort diagnostics only
        text = getattr(response, "text", "") or ""
        return f": {text[:200]}" if text.strip() else ""
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict) and err.get("message"):
            return f": {str(err['message'])[:200]}"
        if isinstance(err, str):
            return f": {err[:200]}"
        if data.get("detail"):
            return f": {str(data['detail'])[:200]}"
    return ""


def _chat_completions(settings: LLMSettings, system: str, user: str) -> str:
    """Call an OpenAI-compatible chat API and return the assistant text."""
    url = f"{settings.base_url}/chat/completions"
    try:
        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {settings.api_key}"},
            json={
                "model": settings.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
            timeout=settings.timeout_s,
        )
        resp.raise_for_status()
    except httpx.ConnectTimeout as exc:
        raise LLMError(
            f"Connection to {settings.base_url} timed out after {settings.timeout_s}s. "
            "Check LLM_BASE_URL and that the provider is reachable."
        ) from exc
    except httpx.TimeoutException as exc:
        raise LLMError(f"LLM request timed out after {settings.timeout_s}s.") from exc
    except httpx.HTTPStatusError as exc:
        # A real HTTP status: the provider answered and rejected us. Surface the
        # provider's own message (auth/quota/model) so the cause is obvious.
        detail = _provider_error_detail(exc.response)
        raise LLMError(
            f"LLM provider returned HTTP {exc.response.status_code}{detail}."
        ) from exc
    except httpx.HTTPError as exc:
        # Transport-level failure (DNS, refused, TLS, proxy) with no HTTP
        # response at all. Naming the exception and the URL is the whole point:
        # a wrong LLM_BASE_URL is the usual cause, and "unknown status" hides it.
        raise LLMError(
            f"Could not reach the LLM provider at {settings.base_url} "
            f"({type(exc).__name__}: {exc}). Check LLM_BASE_URL and connectivity."
        ) from exc
    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMError("LLM returned a malformed response (no choices/message).") from exc
    if not content or not content.strip():
        raise LLMError("LLM returned an empty response.")
    return content


def generate_report(
    report: AnalyticsReport,
    report_type: str = "daily",
    settings: LLMSettings | None = None,
) -> tuple[str, bool, str, str]:
    """Generate markdown report content from a trusted AnalyticsReport.

    Returns:
        (content, numbers_verified, provider, model).

    Raises:
        ValueError: unknown report_type.
        LLMConfigurationError: bad provider or missing key.
        LLMError: upstream/timeout/malformed/empty failures.
    """
    if report_type not in REPORT_TYPES:
        raise ValueError(f"Unknown report_type '{report_type}'. Use: {REPORT_TYPES}.")
    settings = settings or LLMSettings.from_env()
    settings.require_configured()
    user_prompt = build_user_prompt(report, report_type)
    content = _chat_completions(settings, SYSTEM_PROMPT, user_prompt)
    verified = validate_report_numbers(report, content).numbers_verified
    return content, verified, settings.provider, settings.model


def current_utc() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc)
