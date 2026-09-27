"""Shared exception types (import-cycle-free zone).

`app.core.config` and `app.services.llm` both need the configuration
error; defining it here keeps the import graph acyclic without
deferred imports. This module must not import from either consumer.
"""


class LLMConfigurationError(RuntimeError):
    """Missing or invalid LLM configuration (no key, bad provider)."""
