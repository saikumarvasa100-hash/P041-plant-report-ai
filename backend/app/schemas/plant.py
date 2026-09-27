"""Canonical plant observation schema with validation.

Validation lives here (not in APIrouters) so services, CSV ingestion,
and future DB layers share one source of truth.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlantStatus(str, Enum):
    """Allowed machine states."""

    RUNNING = "running"
    IDLE = "idle"
    MAINTENANCE = "maintenance"
    FAULT = "fault"


class PlantObservation(BaseModel):
    """One plant observation (one machine, one timestamp)."""

    model_config = ConfigDict(extra="ignore")

    timestamp: datetime
    machine_id: str = Field(min_length=1)
    production_count: int = Field(ge=0)
    energy_consumption_kwh: float = Field(ge=0)
    efficiency_percent: float = Field(ge=0, le=100)
    temperature_c: float = Field(ge=-20, le=150)
    vibration_mm_s: float = Field(ge=0, le=50)
    downtime_minutes: float = Field(ge=0)
    status: PlantStatus

    @field_validator("machine_id")
    @classmethod
    def machine_id_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("machine_id cannot be empty")
        return v
