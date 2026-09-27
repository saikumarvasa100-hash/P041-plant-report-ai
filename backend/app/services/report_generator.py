"""Central reporting orchestration (usable without the dashboard).

Owns the full pipeline: AnalyticsReport -> LLM narrative -> GeneratedReport,
plus the schedule-ready ``generate_daily_report`` boundary (no cron here —
a future scheduler calls that function).
"""

from __future__ import annotations

from app.core.config import LLMSettings
from app.schemas.analytics import AnalyticsReport
from app.schemas.report import (
    AnalyticsSummary,
    GeneratedReport,
    ReportType,
)
from app.services.analytics import analyze_plant
from app.services.llm import current_utc, generate_report
from app.services.simulator import generate_plant_data


def generate_plant_report(
    analytics: AnalyticsReport,
    report_type: str = "daily",
    settings: LLMSettings | None = None,
) -> GeneratedReport:
    """Render a GeneratedReport from a trusted AnalyticsReport.

    Raises whatever ``generate_report`` raises (ValueError, LLMError,
    LLMConfigurationError) — callers map to transport errors.
    """
    rt = ReportType(report_type)
    content, verified, provider, model = generate_report(
        analytics, rt.value, settings
    )
    period = "unavailable"
    if analytics.period is not None:
        period = (
            f"{analytics.period.start_timestamp.isoformat()} to "
            f"{analytics.period.end_timestamp.isoformat()}"
        )
    p = analytics.plant
    return GeneratedReport(
        report_type=rt,
        generated_at=current_utc(),
        reporting_period=period,
        content=content,
        analytics_summary=AnalyticsSummary(
            total_production=p.total_production,
            average_efficiency=p.average_efficiency,
            total_energy_kwh=p.total_energy_kwh,
            total_downtime_minutes=p.total_downtime_minutes,
            anomaly_count=len(analytics.anomalies),
            machine_count=p.machine_count,
        ),
        numbers_verified=verified,
        provider=provider,
        model=model,
    )


def generate_daily_report(
    machines: int = 4,
    observations: int = 48,
    seed: int = 7,
    report_type: str = "daily",
    settings: LLMSettings | None = None,
) -> GeneratedReport:
    """Schedule-ready boundary: demo data -> analytics -> narrative report."""
    obs = generate_plant_data(
        num_machines=machines,
        observations_per_machine=observations,
        seed=seed,
    )
    return generate_plant_report(analyze_plant(obs), report_type, settings)
