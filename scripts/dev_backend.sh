#!/usr/bin/env bash
# Dev helper: run backend with reload.
# Usage: ./scripts/dev_backend.sh
set -euo pipefail
cd "$(dirname "$0")/../backend"
PYTHONPATH=. exec uvicorn app.main:app --reload --port 8001
