"""Report request/response models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """Supported report cadences (shared pipeline for now)."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReportRequest(BaseModel):
    """Parameters for generating a report from simulated plant data."""

    report_type: ReportType = ReportType.DAILY
    machines: int = Field(4, ge=1, le=10)
    observations: int = Field(48, ge=4, le=500)
    seed: int = 7


class AnalyticsSummary(BaseModel):
    """Key deterministic figures backing the narrative report."""

    total_production: int = 0
    average_efficiency: float = 0.0
    total_energy_kwh: float = 0.0
    total_downtime_minutes: float = 0.0
    anomaly_count: int = 0
    machine_count: int = 0


class GeneratedReport(BaseModel):
    """LLM-generated narrative report plus deterministic metadata."""

    report_type: ReportType
    generated_at: datetime
    reporting_period: str = "unavailable"
    content: str
    analytics_summary: AnalyticsSummary = AnalyticsSummary()
    numbers_verified: bool = False
    provider: str = "openai-compatible"
    model: str = ""
