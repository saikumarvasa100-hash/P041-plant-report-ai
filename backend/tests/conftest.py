"""Shared test fixtures.

The suite must be hermetic: a developer's real ``backend/.env`` (which holds a
live API key) must never influence a test result, and no test may depend on
whether that file happens to exist on the machine running the suite.

``read_env_file`` is therefore stubbed to return an empty mapping for every test
by default. Tests that want to exercise the ``.env`` file path pass explicit
``file_values`` instead, and ``test_dotenv.py`` exercises the reader itself.
"""

from __future__ import annotations

import pytest

LLM_ENV_KEYS = (
    "LLM_PROVIDER",
    "LLM_API_KEY",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "LLM_TIMEOUT_S",
    "CORS_ORIGINS",
)


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch: pytest.MonkeyPatch):
    """Ignore any real .env file and start from a clean LLM/CORS environment."""
    for key in LLM_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("app.core.config.read_env_file", lambda *a, **k: {})
    yield
