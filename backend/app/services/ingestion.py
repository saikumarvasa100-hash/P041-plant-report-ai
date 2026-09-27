"""CSV ingestion + validation for plant observations.

Uses only the standard-library ``csv`` module. Never silently drops bad
rows: every problem is collected into ``PlantDataValidationError`` with
row number, field, and reason.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from pydantic import ValidationError

from app.schemas.plant import PlantObservation

REQUIRED_COLUMNS = (
    "timestamp",
    "machine_id",
    "production_count",
    "energy_consumption_kwh",
    "efficiency_percent",
    "temperature_c",
    "vibration_mm_s",
    "downtime_minutes",
    "status",
)


class PlantDataValidationError(ValueError):
    """Raised when CSV rows fail validation.

    Attributes:
        errors: list of ``{"row": int, "field": str, "reason": str}``.
            For file loads, ``row`` is the CSV line number (header = 1).
    """

    def __init__(self, errors: list[dict]) -> None:
        self.errors = errors
        super().__init__(f"{len(errors)} invalid plant record(s): {errors[:3]}")


def validate_plant_data(rows: Iterable[dict]) -> list[PlantObservation]:
    """Validate raw dict rows into ``PlantObservation`` records.

    Row numbers are 1-indexed over the input iterable.

    Raises:
        PlantDataValidationError: with per-row/field/reason details.
    """
    records: list[PlantObservation] = []
    errors: list[dict] = []
    for idx, raw in enumerate(rows, start=1):
        try:
            records.append(PlantObservation(**raw))
        except ValidationError as exc:
            for err in exc.errors():
                loc = err.get("loc", ())
                field = str(loc[0]) if loc else "unknown"
                errors.append({"row": idx, "field": field, "reason": err.get("msg", "invalid")})
    if errors:
        raise PlantDataValidationError(errors)
    return records


def load_plant_csv(path: str | Path) -> list[PlantObservation]:
    """Load and validate plant observations from a CSV file.

    Returns:
        List of validated ``PlantObservation``.

    Raises:
        FileNotFoundError: if path does not exist.
        PlantDataValidationError: missing columns, empty file, or bad rows
            (row numbers are CSV line numbers, header = line 1).
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise PlantDataValidationError(
                [{"row": 1, "field": "header", "reason": "empty file, no header row"}]
            )
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise PlantDataValidationError(
                [{"row": 1, "field": c, "reason": "missing required column"} for c in missing]
            )
        rows = list(reader)
        if not rows:
            raise PlantDataValidationError(
                [{"row": 1, "field": "body", "reason": "no data rows"}]
            )
        try:
            return validate_plant_data(rows)
        except PlantDataValidationError as exc:
            # Offset: data row 1 == CSV line 2.
            for e in exc.errors:
                e["row"] += 1
            raise
