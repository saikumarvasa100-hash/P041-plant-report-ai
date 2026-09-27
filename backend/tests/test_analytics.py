"""Stage 3 tests: deterministic analytics engine. Hand-made datasets, no network."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.analytics import AnalyticsThresholds
from app.schemas.plant import PlantObservation
from app.services.analytics import (
    analyze_plant,
    analyze_trends,
    calculate_machine_kpis,
    calculate_plant_kpis,
    detect_anomalies,
)
from app.services.simulator import generate_plant_data

BASE = datetime(2026, 9, 1, 6, 0, 0)
client = TestClient(app)


def _obs(i=0, machine="MACHINE-001", prod=100, energy=20.0, eff=85.0,
         temp=65.0, vib=2.0, dt=0.0, status="running"):
    return PlantObservation(
        timestamp=BASE + timedelta(minutes=15 * i),
        machine_id=machine,
        production_count=prod,
        energy_consumption_kwh=energy,
        efficiency_percent=eff,
        temperature_c=temp,
        vibration_mm_s=vib,
        downtime_minutes=dt,
        status=status,
    )


def _kpi_dataset():
    return [
        _obs(0, "MACHINE-001", prod=100, energy=20.0, eff=80.0, temp=60.0, vib=2.0, dt=0.0, status="running"),
        _obs(1, "MACHINE-001", prod=200, energy=30.0, eff=90.0, temp=70.0, vib=4.0, dt=5.0, status="running"),
        _obs(2, "MACHINE-002", prod=50, energy=10.0, eff=50.0, temp=90.0, vib=8.0, dt=20.0, status="fault"),
        _obs(3, "MACHINE-002", prod=0, energy=5.0, eff=0.0, temp=55.0, vib=1.0, dt=10.0, status="idle"),
    ]


def test_kpi_total_production():
    assert calculate_plant_kpis(_kpi_dataset()).total_production == 350


def test_kpi_average_efficiency():
    assert calculate_plant_kpis(_kpi_dataset()).average_efficiency == 55.0


def test_kpi_total_energy():
    assert calculate_plant_kpis(_kpi_dataset()).total_energy_kwh == 65.0


def test_kpi_total_downtime():
    assert calculate_plant_kpis(_kpi_dataset()).total_downtime_minutes == 35.0


def test_kpi_plant_averages_and_counts():
    k = calculate_plant_kpis(_kpi_dataset())
    assert k.average_temperature_c == 68.75
    assert k.average_vibration_mm_s == 3.75
    assert k.machine_count == 2
    assert k.observation_count == 4
    assert (k.running_count, k.fault_count, k.idle_count, k.maintenance_count) == (2, 1, 1, 0)


def test_machine_kpis():
    mk = {m.machine_id: m for m in calculate_machine_kpis(_kpi_dataset())}
    assert mk["MACHINE-001"].production == 300
    assert mk["MACHINE-001"].average_efficiency == 85.0
    assert mk["MACHINE-001"].downtime_minutes == 5.0
    assert mk["MACHINE-002"].production == 50
    assert mk["MACHINE-002"].fault_count == 1
    assert mk["MACHINE-002"].average_temperature_c == 72.5


def test_trend_increasing():
    obs = [_obs(i, prod=10 * (i + 1), eff=80.0, energy=10.0, temp=65.0, vib=2.0, dt=0.0) for i in range(8)]
    trends = {t.metric: t for t in analyze_trends(obs)}
    assert trends["production_count"].direction == "increasing"
    assert trends["production_count"].change_percent > 5
    assert trends["efficiency_percent"].direction == "stable"


def test_trend_decreasing():
    obs = [_obs(i, prod=80 - 10 * i, eff=80.0, energy=10.0, temp=65.0, vib=2.0, dt=0.0) for i in range(8)]
    trends = {t.metric: t for t in analyze_trends(obs)}
    assert trends["production_count"].direction == "decreasing"
    assert trends["production_count"].change_percent < -5


def test_trend_stable():
    obs = [_obs(i) for i in range(8)]
    trends = analyze_trends(obs)
    assert trends, "expected one trend per metric"
    assert all(t.direction == "stable" for t in trends)
    assert all(t.change_percent == 0.0 for t in trends)


def test_high_temperature_anomaly():
    anomalies = detect_anomalies([_obs(temp=98.4, vib=2.0)])
    temp_flags = [a for a in anomalies if a.metric == "temperature_c"]
    assert len(temp_flags) == 1
    assert temp_flags[0].value == 98.4
    assert temp_flags[0].expected == 85.0
    assert temp_flags[0].detector == "threshold"
    assert "threshold" in temp_flags[0].reason.lower()


def test_high_vibration_anomaly():
    anomalies = detect_anomalies([_obs(temp=65.0, vib=8.0)])
    vib_flags = [a for a in anomalies if a.metric == "vibration_mm_s"]
    assert len(vib_flags) == 1
    assert vib_flags[0].severity in ("medium", "high", "critical")


def test_low_efficiency_anomaly():
    anomalies = detect_anomalies([_obs(eff=45.0, status="running")])
    eff_flags = [a for a in anomalies if a.metric == "efficiency_percent"]
    assert len(eff_flags) == 1


def test_idle_zero_efficiency_not_flagged():
    # Idle/maintenance legitimately sit at 0% — must not flood anomalies.
    anomalies = detect_anomalies([_obs(eff=0.0, status="idle", prod=0)])
    assert not [a for a in anomalies if a.metric == "efficiency_percent"]


def test_high_downtime_anomaly():
    anomalies = detect_anomalies([_obs(dt=35.0)])
    dt_flags = [a for a in anomalies if a.metric == "downtime_minutes"]
    assert len(dt_flags) == 1
    assert dt_flags[0].severity == "critical"


def test_severity_assignment():
    assert detect_anomalies([_obs(temp=98.0)])[0].severity == "critical"
    med = [a for a in detect_anomalies([_obs(temp=86.0)]) if a.metric == "temperature_c"]
    assert med and med[0].severity == "medium"
    assert detect_anomalies([_obs(dt=35.0)])[0].severity == "critical"


def test_zscore_detection():
    # Tight cluster at 65C + one 80C outlier (below the 85C threshold).
    obs = [_obs(i, temp=65.0) for i in range(11)] + [_obs(11, temp=80.0)]
    anomalies = detect_anomalies(obs)
    z_flags = [a for a in anomalies if a.detector == "zscore"]
    assert len(z_flags) == 1
    assert z_flags[0].metric == "temperature_c"
    assert z_flags[0].expected is not None
    assert "z-score" in z_flags[0].reason


def test_empty_dataset_handling():
    report = analyze_plant([])
    assert report.period is None
    assert report.plant.observation_count == 0
    assert report.machines == [] and report.trends == []
    assert report.anomalies == [] and report.summaries == []
    assert detect_anomalies([]) == []
    assert analyze_trends([]) == []
    with pytest.raises(ValueError):
        calculate_plant_kpis([])
    with pytest.raises(ValueError):
        calculate_machine_kpis([])


def test_analyze_plant_complete_output():
    obs = generate_plant_data(num_machines=4, observations_per_machine=48, seed=7)
    report = analyze_plant(obs)
    assert report.period is not None
    assert report.period.observation_count == 192
    assert report.period.start_timestamp < report.period.end_timestamp
    assert report.plant.total_production > 0
    assert report.plant.machine_count == 4
    assert len(report.machines) == 4
    assert len(report.trends) == 6  # one per metric
    assert len(report.anomalies) > 0, "sample data must contain anomalies"
    assert any(a.severity == "critical" or a.severity == "high" for a in report.anomalies)
    assert len(report.summaries) >= 4
    # Report carries only derived data: every anomaly references a real observation.
    seen = {(o.machine_id, o.timestamp) for o in obs}
    assert all((a.machine_id, a.timestamp) in seen for a in report.anomalies)


def test_machine_comparison_factual():
    obs = generate_plant_data(num_machines=2, observations_per_machine=12, seed=1)
    report = analyze_plant(obs)
    assert any("highest downtime" in s for s in report.summaries)
    assert all("best" not in s and "worst" not in s for s in report.summaries)


def test_sample_analytics_api_endpoint():
    resp = client.get("/api/v1/analytics/sample?machines=2&observations=8&seed=1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["plant"]["machine_count"] == 2
    assert body["period"]["observation_count"] == 16
    assert len(body["machines"]) == 2
    assert len(body["trends"]) == 6
    assert isinstance(body["anomalies"], list)


def test_threshold_defaults_valid():
    th = AnalyticsThresholds()
    assert th.temperature_high < th.temperature_critical
    assert th.vibration_high < th.vibration_critical
    assert th.efficiency_critical < th.efficiency_low
    assert th.downtime_high < th.downtime_critical


def test_threshold_inverted_rejected():
    with pytest.raises(ValidationError):
        AnalyticsThresholds(temperature_high=95.0, temperature_critical=85.0)
    with pytest.raises(ValidationError):
        AnalyticsThresholds(vibration_high=10.0, vibration_critical=7.0)
    with pytest.raises(ValidationError):
        AnalyticsThresholds(efficiency_low=40.0, efficiency_critical=60.0)
    with pytest.raises(ValidationError):
        AnalyticsThresholds(downtime_high=30.0, downtime_critical=10.0)
