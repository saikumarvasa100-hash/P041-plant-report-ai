"""Environment-based configuration (no secrets in code)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.core.dotenv import read_env_file, resolve
from app.core.exceptions import LLMConfigurationError


@dataclass(frozen=True)
class LLMSettings:
    """LLM provider configuration read from environment variables."""

    provider: str = "openai-compatible"
    api_key: str = ""
    model: str = "qwen2.5:7b-instruct-q4_K_M"
    base_url: str = "http://localhost:11434/v1"
    timeout_s: float = 60.0

    @classmethod
    def from_env(cls) -> "LLMSettings":
        """Build settings from the environment; never raises (validation at use).

        Precedence is real environment variable, then ``backend/.env``, then the
        default below. ``os.environ`` is never modified, so a value in the file
        stays overridable and removable at runtime.
        """
        file_values = read_env_file()
        timeout_raw = resolve("LLM_TIMEOUT_S", "60", file_values)
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 60.0
        return cls(
            provider=resolve("LLM_PROVIDER", "openai-compatible", file_values).strip().lower(),
            api_key=resolve("LLM_API_KEY", "", file_values),
            model=resolve("LLM_MODEL", "qwen2.5:7b-instruct-q4_K_M", file_values),
            base_url=resolve("LLM_BASE_URL", "http://localhost:11434/v1", file_values).rstrip("/"),
            timeout_s=timeout,
        )

    def require_configured(self) -> None:
        """Raise if the real-provider path cannot be used."""
        if self.provider != "openai-compatible":
            raise LLMConfigurationError(
                f"Unsupported LLM_PROVIDER '{self.provider}'. "
                "Use 'openai-compatible' with a configured LLM_API_KEY."
            )
        if not self.api_key.strip() or self.api_key.strip().lower() == "changeme":
            raise LLMConfigurationError(
                "LLM_API_KEY is not configured. Copy backend/.env.example to "
                "backend/.env and set a real provider key."
            )
