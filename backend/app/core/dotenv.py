"""Minimal ``backend/.env`` reader (stdlib only, no python-dotenv dependency).

Rules, chosen to match the intuition developers already have from other tools:

* Missing file is not an error — the app runs fine on environment variables alone.
* Real environment variables always win. A value exported in the shell, or
  prefixed inline (``LLM_MODEL=x uvicorn ...``), overrides the file. That keeps
  one-off overrides working without editing the file.
* Unknown syntax is ignored rather than fatal: blank lines, ``#`` comments,
  ``export KEY=value`` prefixes, and surrounding quotes are handled; anything
  else is skipped.
* ``os.environ`` is never mutated. Values are resolved on read, so a key in the
  file stays distinguishable from an exported one and the process environment
  is left exactly as the shell set it up.
* Values are never logged, so a key in the file cannot leak into logs.
"""

from __future__ import annotations

import os
from pathlib import Path

# app/core/dotenv.py -> app/core -> app -> backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


def parse_dotenv(text: str) -> dict[str, str]:
    """Parse ``KEY=value`` lines into a mapping. Malformed lines are skipped."""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        # Strip one matched pair of surrounding quotes; inner text is kept as-is.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def read_env_file(path: Path | None = None) -> dict[str, str]:
    """Parse the ``.env`` file without touching ``os.environ``.

    Returns ``{}`` when the file is absent or unreadable — running without a
    ``.env`` file is the normal case, not a failure.
    """
    target = path or ENV_FILE
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    return parse_dotenv(text)


def resolve(
    key: str,
    default: str = "",
    file_values: dict[str, str] | None = None,
) -> str:
    """Return the effective value for ``key``: real env var, else ``.env``, else default.

    An exported variable always wins, including when it is set to an empty
    string (an explicit "unset this" beats the file).
    """
    if key in os.environ:
        return os.environ[key]
    if file_values is None:
        file_values = read_env_file()
    return file_values.get(key, default)
