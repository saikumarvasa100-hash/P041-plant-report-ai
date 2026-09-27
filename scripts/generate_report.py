#!/usr/bin/env python3
"""Generate a plant performance report from the command line.

Usage (live provider):
    LLM_PROVIDER=openai-compatible LLM_API_KEY=... LLM_MODEL=... \\
    LLM_BASE_URL=... PYTHONPATH=backend python scripts/generate_report.py
        --type weekly --save

Prints the report, grounding status, and provider/model info.
NEVER prints API keys. --save also writes
backend/data/reports/plant-report-YYYY-MM-DD.md plus a .meta.json sidecar.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import LLMSettings  # noqa: E402
from app.services.report_generator import generate_daily_report  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parents[1] / "backend" / "data" / "reports"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", default="daily", choices=["daily", "weekly", "monthly"])
    ap.add_argument("--machines", type=int, default=4)
    ap.add_argument("--observations", type=int, default=48)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    settings = LLMSettings.from_env()
    report = generate_daily_report(
        args.machines, args.observations, args.seed, args.type, settings
    )
    print(report.content)
    print(f"\nnumbers_verified={report.numbers_verified}")
    print(f"provider={report.provider} model={report.model}")

    if args.save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        md_path = REPORTS_DIR / f"plant-report-{date.today().isoformat()}.md"
        md_path.write_text(report.content, encoding="utf-8")
        meta = {
            "report_type": report.report_type.value,
            "generated_at": report.generated_at.isoformat(),
            "provider": report.provider,
            "model": report.model,
            "numbers_verified": report.numbers_verified,
            "analytics_summary": report.analytics_summary.model_dump(),
        }
        (REPORTS_DIR / f"{md_path.stem}.meta.json").write_text(
            json.dumps(meta, indent=1), encoding="utf-8"
        )
        print(f"saved -> {md_path}")


if __name__ == "__main__":
    main()
