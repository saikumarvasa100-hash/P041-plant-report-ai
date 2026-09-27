"""Stage 2 tests: schema validation, simulator, CSV ingestion. No network."""

import csv
from datetime import datetime

import pytest

from app.schemas.plant import PlantObservation
from app.services.ingestion import (
    PlantDataValidationError,
    load_plant_csv,
    validate_plant_data,
)
from app.services.simulator import generate_plant_data


def _valid_row(**overrides):
    row = {
        "timestamp": datetime(2026, 9, 1, 6, 0, 0),
        "machine_id": "MACHINE-001",
        "production_count": 100,
        "energy_consumption_kwh": 20.5,
        "efficiency_percent": 88.5,
        "temperature_c": 68.0,
        "vibration_mm_s": 2.5,
        "downtime_minutes": 0.0,
        "status": "running",
    }
    row.update(overrides)
    return row


def test_valid_observation_passes():
    obs = PlantObservation(**_valid_row())
    assert obs.machine_id == "MACHINE-001"
    assert obs.status == "running"


def test_negative_production_fails():
    with pytest.raises(Exception):
        PlantObservation(**_valid_row(production_count=-1))


def test_efficiency_out_of_range_fails():
    with pytest.raises(Exception):
        PlantObservation(**_valid_row(efficiency_percent=101))
    with pytest.raises(Exception):
        PlantObservation(**_valid_row(efficiency_percent=-0.1))


def test_empty_machine_id_fails():
    with pytest.raises(Exception):
        PlantObservation(**_valid_row(machine_id=""))
    with pytest.raises(Exception):
        PlantObservation(**_valid_row(machine_id="   "))


def test_invalid_status_fails():
    with pytest.raises(Exception):
        PlantObservation(**_valid_row(status="exploding"))


def test_simulator_record_count():
    recs = generate_plant_data(
        num_machines=2, observations_per_machine=10, seed=1
    )
    assert len(recs) == 20


def test_simulator_multiple_machines():
    recs = generate_plant_data(
        num_machines=3, observations_per_machine=5, seed=1
    )
    assert sorted({r.machine_id for r in recs}) == [
        "MACHINE-001",
        "MACHINE-002",
        "MACHINE-003",
    ]


def test_csv_ingestion(tmp_path):
    recs = generate_plant_data(
        num_machines=2, observations_per_machine=4, seed=3
    )
    p = tmp_path / "plant.csv"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(_valid_row().keys()))
        w.writeheader()
        for r in recs:
            w.writerow(r.model_dump())
    loaded = load_plant_csv(p)
    assert len(loaded) == 8
    assert loaded[0].machine_id == "MACHINE-001"


def test_invalid_csv_errors(tmp_path):
    p = tmp_path / "bad.csv"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(_valid_row().keys()))
        w.writeheader()
        bad = _valid_row(production_count=-5, efficiency_percent=999)
        w.writerow(bad)
    with pytest.raises(PlantDataValidationError) as exc_info:
        load_plant_csv(p)
    errors = exc_info.value.errors
    assert len(errors) >= 2
    # Useful details: row number, field, reason.
    assert all({"row", "field", "reason"} <= set(e) for e in errors)
    assert errors[0]["row"] == 2  # CSV line number (header = 1)
    fields = {e["field"] for e in errors}
    assert "production_count" in fields
    assert "efficiency_percent" in fields


def test_simulator_produces_abnormal_conditions():
    recs = generate_plant_data(
        num_machines=4, observations_per_machine=48, seed=7, fault_rate=0.06
    )
    abnormal = [
        r
        for r in recs
        if r.status == "fault"
        or r.temperature_c > 85
        or r.vibration_mm_s > 7
        or (r.status == "running" and r.efficiency_percent < 65)
    ]
    assert len(abnormal) > 0, "simulator must produce abnormal rows for Stage 3"


def test_validate_service_function():
    recs = validate_plant_data([_valid_row(), _valid_row(machine_id="MACHINE-002")])
    assert len(recs) == 2
