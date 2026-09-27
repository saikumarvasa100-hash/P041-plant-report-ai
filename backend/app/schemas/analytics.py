"""Analytics result models (deterministic output, future LLM input).

These models contain ONLY values derived from input observations via
deterministic Python. The LLM in Stage 4+ receives an ``AnalyticsReport``
and renders narrative — it never computes these numbers.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Severity(str, Enum):
    """Anomaly severity tiers."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrendDirection(str, Enum):
    """Trend direction for a metric's recent vs earlier window."""

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"


class PlantKPIs(BaseModel):
    """Plant-wide aggregate KPIs."""

    observation_count: int = 0
    machine_count: int = 0
    total_production: int = 0
    average_efficiency: float = 0.0
    total_energy_kwh: float = 0.0
    total_downtime_minutes: float = 0.0
    average_temperature_c: float = 0.0
    average_vibration_mm_s: float = 0.0
    running_count: int = 0
    idle_count: int = 0
    maintenance_count: int = 0
    fault_count: int = 0
    oee_percent: float = 0.0
    availability_percent: float = 0.0
    performance_percent: float = 0.0
    quality_percent: float = 0.0
    energy_intensity: float = 0.0
    mtbf_hours: float = 0.0
    mttr_minutes: float = 0.0


class MachineKPIs(BaseModel):
    """Per-machine aggregate KPIs."""

    machine_id: str
    observation_count: int = 0
    production: int = 0
    average_efficiency: float = 0.0
    energy_kwh: float = 0.0
    downtime_minutes: float = 0.0
    average_temperature_c: float = 0.0
    average_vibration_mm_s: float = 0.0
    running_count: int = 0
    idle_count: int = 0
    maintenance_count: int = 0
    fault_count: int = 0
    oee_percent: float = 0.0
    availability_percent: float = 0.0
    performance_percent: float = 0.0
    quality_percent: float = 0.0
    energy_intensity: float = 0.0
    mtbf_hours: float = 0.0
    mttr_minutes: float = 0.0


class TrendResult(BaseModel):
    """Half-split mean-comparison trend for one metric."""

    metric: str
    direction: TrendDirection
    change_percent: float
    strength: float = Field(ge=0, le=1)
    earlier_mean: float
    later_mean: float
    start_timestamp: datetime
    end_timestamp: datetime
    observation_count: int
    method: str = "half-split mean comparison"


class Anomaly(BaseModel):
    """One explainable anomaly flag."""

    machine_id: str
    timestamp: datetime
    metric: str
    value: float
    expected: float | None = None
    severity: Severity
    reason: str
    detector: str = "threshold"


class ReportingPeriod(BaseModel):
    """Time range covered by the analyzed observations."""

    start_timestamp: datetime
    end_timestamp: datetime
    duration_minutes: float
    observation_count: int


class AnalyticsThresholds(BaseModel):
    """Tunable detection thresholds (demonstration values).

    Calibrated against the Stage 2 simulator's normal/abnormal ranges:
    normal temp ~55-80C vs fault 85-105C; normal vibration <4.5 vs fault
    7.5-12 mm/s; running efficiency 70-99.5 vs fault 35-60; normal
    downtime 0-2 min vs fault 10-45 min per interval.

    THESE ARE DEMONSTRATION THRESHOLDS. Real equipment needs calibration
    against manufacturer specs and historical baselines.
    """

    temperature_high: float = 85.0
    temperature_critical: float = 95.0
    vibration_high: float = 7.0
    vibration_critical: float = 10.0
    efficiency_low: float = 60.0
    efficiency_critical: float = 40.0
    downtime_high: float = 10.0
    downtime_critical: float = 30.0
    zscore_threshold: float = 3.0
    trend_stable_band_percent: float = 5.0

    @model_validator(mode="after")
    def check_threshold_ordering(self) -> "AnalyticsThresholds":
        """Fail fast on inverted tiers instead of silently mis-severing."""
        pairs = [
            ("temperature_high", self.temperature_high, "temperature_critical", self.temperature_critical),
            ("vibration_high", self.vibration_high, "vibration_critical", self.vibration_critical),
            ("downtime_high", self.downtime_high, "downtime_critical", self.downtime_critical),
        ]
        for low_name, low_val, high_name, high_val in pairs:
            if not low_val < high_val:
                raise ValueError(f"{low_name} ({low_val}) must be below {high_name} ({high_val})")
        # Efficiency is lower-worse: critical (40) must sit below low (60).
        if not self.efficiency_critical < self.efficiency_low:
            raise ValueError(
                f"efficiency_critical ({self.efficiency_critical}) must be below "
                f"efficiency_low ({self.efficiency_low})"
            )
        return self


class AnalyticsReport(BaseModel):
    """Complete deterministic analytics output for one dataset."""

    period: ReportingPeriod | None = None
    plant: PlantKPIs = PlantKPIs()
    machines: list[MachineKPIs] = []
    trends: list[TrendResult] = []
    anomalies: list[Anomaly] = []
    summaries: list[str] = []
