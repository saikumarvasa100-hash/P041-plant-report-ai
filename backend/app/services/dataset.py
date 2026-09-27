"""Training/fine-tuning example pipeline (provider-rendered, deterministic inputs).

Transforms a trusted ``AnalyticsReport`` plus a reference report text into a
JSONL-ready example of ``{"report_type", "analytics", "target_report",
"source", "seed"}``. The ``synthetic`` source means machine-rendered through
the configured provider — never human ground truth
(see ``backend/data/training/README.md``).
"""

from __future__ import annotations

from typing import Any

from app.core.config import LLMSettings
from app.schemas.analytics import AnalyticsReport
from app.schemas.report import ReportType
from app.services.analytics import analyze_plant
from app.services.grounding import validate_report_numbers
from app.services.llm import generate_report
from app.services.simulator import generate_plant_data

SYNTHETIC_SOURCE = "synthetic"
HUMAN_REVIEWED_SOURCE = "human-reviewed"

_SECRET_MARKERS = ("api_key", "apikey", "bearer ", "sk-", "passwd", "token=")


def make_training_example(
    analytics: AnalyticsReport,
    report_type: str,
    target_report: str,
    source: str = SYNTHETIC_SOURCE,
    seed: int | None = None,
) -> dict[str, Any]:
    """Build one complete training example record."""
    return {
        "report_type": report_type,
        "analytics": analytics.model_dump(mode="json"),
        "target_report": target_report,
        "source": source,
        "seed": seed,
    }


def validate_training_example(example: dict[str, Any]) -> list[str]:
    """Return a list of problems; empty means valid."""
    problems: list[str] = []
    if example.get("report_type") not in ("daily", "weekly", "monthly"):
        problems.append(f"bad report_type: {example.get('report_type')!r}")
    if example.get("source") not in (SYNTHETIC_SOURCE, HUMAN_REVIEWED_SOURCE):
        problems.append(f"bad source: {example.get('source')!r}")
    target = example.get("target_report", "")
    if not isinstance(target, str) or not target.strip():
        problems.append("empty target_report")
    try:
        analytics = AnalyticsReport(**example.get("analytics", {}))
    except Exception as exc:  # noqa: BLE001 - report the validation failure
        problems.append(f"invalid analytics: {exc}")
        return problems
    if isinstance(target, str) and target.strip():
        result = validate_report_numbers(analytics, target)
        if not result.numbers_verified:
            problems.append(f"untraceable numbers: {result.mismatches[:5]}")
    blob = (str(example.get("target_report", "")) + str(example.get("analytics", ""))).lower()
    if any(marker in blob for marker in _SECRET_MARKERS):
        problems.append("possible secret material in example")
    return problems


def generate_dataset(
    seeds: list[int],
    machines_list: list[int],
    report_types: list[str],
    observations_per_machine: int = 48,
    settings: LLMSettings | None = None,
) -> list[dict[str, Any]]:
    """Generate examples across seeds/configs via the configured provider."""
    examples: list[dict[str, Any]] = []
    for seed in seeds:
        for machines in machines_list:
            obs = generate_plant_data(
                num_machines=machines,
                observations_per_machine=observations_per_machine,
                seed=seed,
            )
            analytics = analyze_plant(obs)
            for report_type in report_types:
                rt = ReportType(report_type)
                target, _, _, _ = generate_report(analytics, rt.value, settings)
                examples.append(
                    make_training_example(analytics, rt.value, target, seed=seed)
                )
    return examples
