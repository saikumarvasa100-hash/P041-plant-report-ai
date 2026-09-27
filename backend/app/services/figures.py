"""The canonical list of figures a generated report must reproduce verbatim.

Lives in its own module because two consumers need it and they must not depend
on each other:

* ``app.services.prompts`` puts the list in the prompt, so a small model knows
  exactly which values to quote.
* ``app.services.grounding`` checks the generated text against it.

Both therefore read the same source, so the instruction and the check cannot
drift apart. The list is derived from the Stage 3 ``AnalyticsReport`` only — it
never calls the LLM and never recomputes plant values.
"""

from __future__ import annotations

from collections import Counter

from app.schemas.analytics import AnalyticsReport

#: Plant-level figures, in report order, with their grounding labels.
PLANT_FIGURES = (
    ("plant.total_production", "total_production"),
    ("plant.average_efficiency", "average_efficiency"),
    ("plant.total_energy_kwh", "total_energy_kwh"),
    ("plant.total_downtime_minutes", "total_downtime_minutes"),
)


def key_numbers(report: AnalyticsReport) -> list[str]:
    """Top-level plant figures that must appear verbatim, as strings."""
    p = report.plant
    return [
        str(p.total_production),
        str(p.average_efficiency),
        str(p.total_energy_kwh),
        str(p.total_downtime_minutes),
        str(len(report.anomalies)),
    ]


def required_numbers(report: AnalyticsReport) -> list[tuple[str, object]]:
    """Every (label, value) pair a report must reproduce verbatim."""
    p = report.plant
    checks: list[tuple[str, object]] = [
        (label, getattr(p, field)) for label, field in PLANT_FIGURES
    ]
    checks.append(("plant.anomaly_count", len(report.anomalies)))

    sev_counts = Counter(a.severity.value for a in report.anomalies)
    for sev in ("critical", "high", "medium", "low"):
        if sev_counts.get(sev, 0) > 0:
            checks.append((f"severity.{sev}_count", sev_counts[sev]))

    for m in report.machines:
        checks += [
            (f"{m.machine_id}.production", m.production),
            (f"{m.machine_id}.avg_efficiency", m.average_efficiency),
            (f"{m.machine_id}.energy_kwh", m.energy_kwh),
            (f"{m.machine_id}.downtime", m.downtime_minutes),
        ]

    # Check the first anomalies quoted in the report text.
    for i, a in enumerate(report.anomalies[:10]):
        checks.append((f"anomaly[{i}].{a.metric}", a.value))
    return checks
