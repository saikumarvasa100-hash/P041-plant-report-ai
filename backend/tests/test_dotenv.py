"""Tests for the stdlib backend/.env loader and its precedence rules."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.core.config import LLMSettings
from app.core.dotenv import parse_dotenv, read_env_file, resolve
from app.core.exceptions import LLMConfigurationError


def write_env(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return path


# ---------- parse_dotenv ----------


def test_parses_plain_assignments():
    assert parse_dotenv("A=1\nB=two\n") == {"A": "1", "B": "two"}


def test_skips_comments_blank_lines_and_junk():
    parsed = parse_dotenv("# comment\n\n   \nA=1\nnot-an-assignment\n=novalue\nB=2\n")
    assert parsed == {"A": "1", "B": "2"}


def test_strips_export_prefix_and_surrounding_quotes():
    parsed = parse_dotenv('export A="one two"\nB=\'three\'\nC=bare\n')
    assert parsed == {"A": "one two", "B": "three", "C": "bare"}


def test_keeps_equals_signs_inside_value():
    assert parse_dotenv("A=x=y=z\n") == {"A": "x=y=z"}


def test_preserves_hash_inside_value():
    # Only whole-line comments are stripped; a '#' in a value must survive.
    assert parse_dotenv("A=abc#123\n") == {"A": "abc#123"}


# ---------- read_env_file ----------


def test_missing_file_is_not_an_error(tmp_path: Path):
    assert read_env_file(tmp_path / "nope.env") == {}


def test_reads_file_without_mutating_environ(tmp_path: Path):
    # The key property: reading a .env must never leak into os.environ, or the
    # value becomes indistinguishable from (and impossible to remove as) a real
    # exported variable.
    before = dict(os.environ)
    values = read_env_file(write_env(tmp_path, "LLM_MODEL=from-file\n"))
    assert values == {"LLM_MODEL": "from-file"}
    assert dict(os.environ) == before
    assert "LLM_MODEL" not in os.environ


def test_directory_path_is_ignored(tmp_path: Path):
    assert read_env_file(tmp_path) == {}


def test_undecodable_file_is_ignored(tmp_path: Path):
    path = tmp_path / ".env"
    path.write_bytes(b"LLM_MODEL=\xff\xfe\x00bad\n")
    assert read_env_file(path) == {}


# ---------- resolve ----------


def test_resolve_prefers_file_when_env_absent(tmp_path: Path):
    values = read_env_file(write_env(tmp_path, "LLM_MODEL=from-file\n"))
    assert resolve("LLM_MODEL", "fallback", values) == "from-file"


def test_resolve_prefers_env_over_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_MODEL", "from-shell")
    values = read_env_file(write_env(tmp_path, "LLM_MODEL=from-file\n"))
    assert resolve("LLM_MODEL", "fallback", values) == "from-shell"


def test_resolve_treats_explicitly_empty_env_as_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LLM_MODEL", "")
    values = read_env_file(write_env(tmp_path, "LLM_MODEL=from-file\n"))
    assert resolve("LLM_MODEL", "fallback", values) == ""


def test_resolve_falls_back_to_default():
    assert resolve("LLM_NOT_SET_ANYWHERE", "fallback", {}) == "fallback"


def test_resolve_reads_file_itself_when_values_not_supplied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("app.core.dotenv.ENV_FILE", write_env(tmp_path, "LLM_MODEL=from-file\n"))
    assert resolve("LLM_MODEL", "fallback") == "from-file"


# ---------- LLMSettings integration ----------


def test_from_env_defaults_without_file():
    settings = LLMSettings.from_env()
    assert settings.provider == "openai-compatible"
    assert settings.model == "qwen2.5:7b-instruct-q4_K_M"
    assert settings.timeout_s == 60.0


def test_from_env_reads_file_values(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.core.config.read_env_file",
        lambda *a, **k: {
            "LLM_PROVIDER": "openai-compatible",
            "LLM_API_KEY": "file-key",
            "LLM_MODEL": "liquid/lfm-2.5-2.6b:free",
            "LLM_BASE_URL": "https://openrouter.ai/api/v1/",
        },
    )
    settings = LLMSettings.from_env()
    assert settings.api_key == "file-key"
    assert settings.model == "liquid/lfm-2.5-2.6b:free"
    # Trailing slash is normalised so the client can append /chat/completions.
    assert settings.base_url == "https://openrouter.ai/api/v1"
    settings.require_configured()  # must not raise


def test_from_env_lets_shell_override_file(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.core.config.read_env_file",
        lambda *a, **k: {"LLM_BASE_URL": "http://localhost:11434/v1"},
    )
    monkeypatch.setenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    assert LLMSettings.from_env().base_url == "https://openrouter.ai/api/v1"


def test_from_env_does_not_leak_file_key_into_environ(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.core.config.read_env_file", lambda *a, **k: {"LLM_API_KEY": "file-key"})
    LLMSettings.from_env()
    assert "LLM_API_KEY" not in os.environ


def test_invalid_timeout_falls_back_to_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_TIMEOUT_S", "not-a-number")
    assert LLMSettings.from_env().timeout_s == 60.0


def test_placeholder_key_still_rejected(monkeypatch: pytest.MonkeyPatch):
    # The .env.example placeholder must not read as a configured provider.
    monkeypatch.setenv("LLM_API_KEY", "changeme")
    with pytest.raises(LLMConfigurationError):
        LLMSettings.from_env().require_configured()


def test_blank_key_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_API_KEY", "   ")
    with pytest.raises(LLMConfigurationError):
        LLMSettings.from_env().require_configured()


def test_error_message_points_at_backend_env():
    # The error text is the only guidance a user gets; it must name the real file.
    with pytest.raises(LLMConfigurationError) as exc:
        LLMSettings(api_key="").require_configured()
    assert "backend/.env" in str(exc.value)
