"""Deterministic industrial analytics engine (no LLM, no ML black boxes).

Python = truth: every number here is computed from the input observations.
Stage 4+ will hand the resulting ``AnalyticsReport`` to the LLM for
narrative rendering only.

Methods (all explainable):
- KPIs: plain sums / arithmetic means.
- Trends: chronological half-split mean comparison per metric.
  Sort observations by timestamp, split into earlier/later halves,
  compare means. |change| below the stable band -> "stable".
- Anomalies: (a) threshold checks per observation, (b) per-machine
  z-score (|z| >= threshold, needs >= 10 obs for that machine) for
  temperature and vibration. Threshold hits suppress the z-score flag
  for the same observation+metric to avoid duplicates.
"""

from __future__ import annotations

import statistics
from datetime import datetime

from app.schemas.analytics import (
    AnalyticsReport,
    AnalyticsThresholds,
    Anomaly,
    MachineKPIs,
    PlantKPIs,
    ReportingPeriod,
    Severity,
    TrendDirection,
    TrendResult,
)
from app.schemas.plant import PlantObservation, PlantStatus

DEFAULT_THRESHOLDS = AnalyticsThresholds()

TREND_METRICS: tuple[tuple[str, str], ...] = (
    ("production_count", "production_count"),
    ("efficiency_percent", "efficiency_percent"),
    ("energy_consumption_kwh", "energy_consumption_kwh"),
    ("temperature_c", "temperature_c"),
    ("vibration_mm_s", "vibration_mm_s"),
    ("downtime_minutes", "downtime_minutes"),
)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _tiered_severity(value: float, high: float, critical: float, *, upper: bool) -> Severity | None:
    """Map a value onto medium/high/critical tiers, or None if normal.

    upper=True: higher values are worse (temp/vibration/downtime).
    upper=False: lower values are worse (efficiency).
    """
    mid = (high + critical) / 2.0
    if upper:
        if value >= critical:
            return Severity.CRITICAL
        if value >= mid:
            return Severity.HIGH
        if value >= high:
            return Severity.MEDIUM
        return None
    if value <= critical:
        return Severity.CRITICAL
    if value <= mid:
        return Severity.HIGH
    if value <= high:
        return Severity.MEDIUM
    return None


def _compute_oee_metrics(
    obs_count: int,
    prod: int,
    avg_eff: float,
    energy_kwh: float,
    downtime_min: float,
    fault_count: int,
) -> dict[str, float]:
    """Helper to compute deterministic OEE, MTBF, MTTR, and Energy Intensity metrics."""
    scheduled_min = max(30.0, obs_count * 30.0)
    operating_min = max(0.0, scheduled_min - downtime_min)
    availability = min(100.0, max(0.0, (operating_min / scheduled_min) * 100.0))
    performance = min(100.0, max(0.0, avg_eff))
    quality = min(100.0, max(0.0, 100.0 - (fault_count / max(1, obs_count)) * 25.0))
    oee = (availability * performance * quality) / 10000.0
    intensity = (energy_kwh / prod * 1000.0) if prod > 0 else 0.0
    mtbf = (operating_min / 60.0) / max(1, fault_count)
    mttr = downtime_min / max(1, fault_count)
    return {
        "oee_percent": round(oee, 2),
        "availability_percent": round(availability, 2),
        "performance_percent": round(performance, 2),
        "quality_percent": round(quality, 2),
        "energy_intensity": round(intensity, 2),
        "mtbf_hours": round(mtbf, 2),
        "mttr_minutes": round(mttr, 2),
    }


def calculate_plant_kpis(observations: list[PlantObservation]) -> PlantKPIs:
    """Aggregate plant-wide KPIs (sums, arithmetic means, and OEE metrics).

    Raises:
        ValueError: on empty input.
    """
    if not observations:
        raise ValueError("no observations to analyze")
    n = len(observations)
    statuses = [o.status for o in observations]
    prod = sum(o.production_count for o in observations)
    eff = round(_mean([o.efficiency_percent for o in observations]), 2)
    energy = round(sum(o.energy_consumption_kwh for o in observations), 2)
    down = round(sum(o.downtime_minutes for o in observations), 2)
    faults = statuses.count(PlantStatus.FAULT)

    oee = _compute_oee_metrics(n, prod, eff, energy, down, faults)

    return PlantKPIs(
        observation_count=n,
        machine_count=len({o.machine_id for o in observations}),
        total_production=prod,
        average_efficiency=eff,
        total_energy_kwh=energy,
        total_downtime_minutes=down,
        average_temperature_c=round(_mean([o.temperature_c for o in observations]), 2),
        average_vibration_mm_s=round(_mean([o.vibration_mm_s for o in observations]), 2),
        running_count=statuses.count(PlantStatus.RUNNING),
        idle_count=statuses.count(PlantStatus.IDLE),
        maintenance_count=statuses.count(PlantStatus.MAINTENANCE),
        fault_count=faults,
        oee_percent=oee["oee_percent"],
        availability_percent=oee["availability_percent"],
        performance_percent=oee["performance_percent"],
        quality_percent=oee["quality_percent"],
        energy_intensity=oee["energy_intensity"],
        mtbf_hours=oee["mtbf_hours"],
        mttr_minutes=oee["mttr_minutes"],
    )


def calculate_machine_kpis(observations: list[PlantObservation]) -> list[MachineKPIs]:
    """Aggregate per-machine KPIs, sorted by machine_id.

    Raises:
        ValueError: on empty input.
    """
    if not observations:
        raise ValueError("no observations to analyze")
    by_machine: dict[str, list[PlantObservation]] = {}
    for o in observations:
        by_machine.setdefault(o.machine_id, []).append(o)
    result = []
    for mid in sorted(by_machine):
        obs = by_machine[mid]
        statuses = [o.status for o in obs]
        n = len(obs)
        prod = sum(o.production_count for o in obs)
        eff = round(_mean([o.efficiency_percent for o in obs]), 2)
        energy = round(sum(o.energy_consumption_kwh for o in obs), 2)
        down = round(sum(o.downtime_minutes for o in obs), 2)
        faults = statuses.count(PlantStatus.FAULT)

        oee = _compute_oee_metrics(n, prod, eff, energy, down, faults)

        result.append(
            MachineKPIs(
                machine_id=mid,
                observation_count=n,
                production=prod,
                average_efficiency=eff,
                energy_kwh=energy,
                downtime_minutes=down,
                average_temperature_c=round(_mean([o.temperature_c for o in obs]), 2),
                average_vibration_mm_s=round(_mean([o.vibration_mm_s for o in obs]), 2),
                running_count=statuses.count(PlantStatus.RUNNING),
                idle_count=statuses.count(PlantStatus.IDLE),
                maintenance_count=statuses.count(PlantStatus.MAINTENANCE),
                fault_count=faults,
                oee_percent=oee["oee_percent"],
                availability_percent=oee["availability_percent"],
                performance_percent=oee["performance_percent"],
                quality_percent=oee["quality_percent"],
                energy_intensity=oee["energy_intensity"],
                mtbf_hours=oee["mtbf_hours"],
                mttr_minutes=oee["mttr_minutes"],
            )
        )
    return result


def analyze_trends(
    observations: list[PlantObservation],
    stable_band_percent: float = DEFAULT_THRESHOLDS.trend_stable_band_percent,
) -> list[TrendResult]:
    """Half-split trend per metric over the global timestamp order.

    Needs >= 4 observations; fewer returns []. Zero earlier-mean is
    handled by convention (0->0 = 0% stable; 0->x = +/-100%).
    Strength = min(1, |change|/50), a normalized magnitude indicator.
    """
    if len(observations) < 4:
        return []
    ordered = sorted(observations, key=lambda o: o.timestamp)
    half = len(ordered) // 2
    earlier, later = ordered[:half], ordered[half:]
    start, end = ordered[0].timestamp, ordered[-1].timestamp
    results: list[TrendResult] = []
    for attr, metric in TREND_METRICS:
        e_vals = [float(getattr(o, attr)) for o in earlier]
        l_vals = [float(getattr(o, attr)) for o in later]
        e_mean, l_mean = _mean(e_vals), _mean(l_vals)
        if e_mean == 0:
            if l_mean == 0:
                change, direction = 0.0, TrendDirection.STABLE
            else:
                change = 100.0 if l_mean > 0 else -100.0
                direction = (
                    TrendDirection.INCREASING if l_mean > 0 else TrendDirection.DECREASING
                )
        else:
            change = (l_mean - e_mean) / abs(e_mean) * 100.0
            if abs(change) < stable_band_percent:
                direction = TrendDirection.STABLE
            else:
                direction = (
                    TrendDirection.INCREASING if change > 0 else TrendDirection.DECREASING
                )
        results.append(
            TrendResult(
                metric=metric,
                direction=direction,
                change_percent=round(change, 2),
                strength=round(min(1.0, abs(change) / 50.0), 3),
                earlier_mean=round(e_mean, 3),
                later_mean=round(l_mean, 3),
                start_timestamp=start,
                end_timestamp=end,
                observation_count=len(ordered),
                method="half-split mean comparison",
            )
        )
    return results


def detect_anomalies(
    observations: list[PlantObservation],
    thresholds: AnalyticsThresholds | None = None,
) -> list[Anomaly]:
    """Threshold + per-machine z-score anomaly detection.

    Efficiency is only evaluated when the machine is expected to produce
    (running/fault); idle/maintenance legitimately sit at 0%.
    """
    if not observations:
        return []
    th = thresholds or DEFAULT_THRESHOLDS
    anomalies: list[Anomaly] = []
    flagged: set[tuple[str, str, datetime]] = set()  # (machine, metric, ts)

    for o in observations:
        sev = _tiered_severity(o.temperature_c, th.temperature_high, th.temperature_critical, upper=True)
        if sev is not None:
            anomalies.append(
                Anomaly(
                    machine_id=o.machine_id,
                    timestamp=o.timestamp,
                    metric="temperature_c",
                    value=o.temperature_c,
                    expected=th.temperature_high,
                    severity=sev,
                    reason=(
                        f"Temperature {o.temperature_c}C exceeded "
                        f"{'critical' if sev == Severity.CRITICAL else 'high'} "
                        f"threshold {th.temperature_critical if sev == Severity.CRITICAL else th.temperature_high}C"
                    ),
                    detector="threshold",
                )
            )
            flagged.add((o.machine_id, "temperature_c", o.timestamp))

        sev = _tiered_severity(o.vibration_mm_s, th.vibration_high, th.vibration_critical, upper=True)
        if sev is not None:
            anomalies.append(
                Anomaly(
                    machine_id=o.machine_id,
                    timestamp=o.timestamp,
                    metric="vibration_mm_s",
                    value=o.vibration_mm_s,
                    expected=th.vibration_high,
                    severity=sev,
                    reason=(
                        f"Vibration {o.vibration_mm_s} mm/s exceeded "
                        f"{'critical' if sev == Severity.CRITICAL else 'high'} "
                        f"threshold {th.vibration_critical if sev == Severity.CRITICAL else th.vibration_high} mm/s"
                    ),
                    detector="threshold",
                )
            )
            flagged.add((o.machine_id, "vibration_mm_s", o.timestamp))

        if o.status in (PlantStatus.RUNNING, PlantStatus.FAULT):
            sev = _tiered_severity(
                o.efficiency_percent, th.efficiency_low, th.efficiency_critical, upper=False
            )
            if sev is not None:
                anomalies.append(
                    Anomaly(
                        machine_id=o.machine_id,
                        timestamp=o.timestamp,
                        metric="efficiency_percent",
                        value=o.efficiency_percent,
                        expected=th.efficiency_low,
                        severity=sev,
                        reason=(
                            f"Efficiency {o.efficiency_percent}% below "
                            f"{'critical' if sev == Severity.CRITICAL else 'low'} "
                            f"threshold {th.efficiency_critical if sev == Severity.CRITICAL else th.efficiency_low}%"
                        ),
                        detector="threshold",
                    )
                )
                flagged.add((o.machine_id, "efficiency_percent", o.timestamp))

        sev = _tiered_severity(o.downtime_minutes, th.downtime_high, th.downtime_critical, upper=True)
        if sev is not None:
            anomalies.append(
                Anomaly(
                    machine_id=o.machine_id,
                    timestamp=o.timestamp,
                    metric="downtime_minutes",
                    value=o.downtime_minutes,
                    expected=th.downtime_high,
                    severity=sev,
                    reason=(
                        f"Downtime {o.downtime_minutes} min exceeded "
                        f"{'critical' if sev == Severity.CRITICAL else 'high'} "
                        f"threshold {th.downtime_critical if sev == Severity.CRITICAL else th.downtime_high} min"
                    ),
                    detector="threshold",
                )
            )
            flagged.add((o.machine_id, "downtime_minutes", o.timestamp))

    # Statistical pass: per-machine z-score for temp/vibration.
    by_machine: dict[str, list[PlantObservation]] = {}
    for o in observations:
        by_machine.setdefault(o.machine_id, []).append(o)
    for mid, obs in by_machine.items():
        if len(obs) < 10:
            continue
        for attr, metric in (("temperature_c", "temperature_c"), ("vibration_mm_s", "vibration_mm_s")):
            vals = [float(getattr(o, attr)) for o in obs]
            mean = statistics.fmean(vals)
            stdev = statistics.pstdev(vals)
            if stdev <= 0:
                continue
            for o in obs:
                if (mid, metric, o.timestamp) in flagged:
                    continue
                z = (float(getattr(o, attr)) - mean) / stdev
                if abs(z) >= th.zscore_threshold:
                    anomalies.append(
                        Anomaly(
                            machine_id=mid,
                            timestamp=o.timestamp,
                            metric=metric,
                            value=float(getattr(o, attr)),
                            expected=round(mean, 2),
                            severity=Severity.HIGH if abs(z) >= 4.5 else Severity.MEDIUM,
                            reason=f"{metric} z-score {z:.2f} vs machine mean {mean:.2f} (|z| >= {th.zscore_threshold})",
                            detector="zscore",
                        )
                    )

    anomalies.sort(key=lambda a: (a.timestamp, a.machine_id, a.metric))
    return anomalies


def compare_machines(
    machine_kpis: list[MachineKPIs], anomalies: list[Anomaly]
) -> list[str]:
    """Factual per-metric leadership statements (no best/worst ranking)."""
    if not machine_kpis:
        return []
    summaries: list[str] = []
    by_prod = max(machine_kpis, key=lambda m: m.production)
    summaries.append(
        f"{by_prod.machine_id} recorded the highest production ({by_prod.production} units)."
    )
    by_eff = max(machine_kpis, key=lambda m: m.average_efficiency)
    summaries.append(
        f"{by_eff.machine_id} recorded the highest average efficiency ({by_eff.average_efficiency}%)."
    )
    by_down = max(machine_kpis, key=lambda m: m.downtime_minutes)
    summaries.append(
        f"{by_down.machine_id} recorded the highest downtime ({by_down.downtime_minutes} min)."
    )
    by_energy = max(machine_kpis, key=lambda m: m.energy_kwh)
    summaries.append(
        f"{by_energy.machine_id} recorded the highest energy consumption ({by_energy.energy_kwh} kWh)."
    )
    if anomalies:
        counts: dict[str, int] = {}
        for a in anomalies:
            counts[a.machine_id] = counts.get(a.machine_id, 0) + 1
        worst = max(counts, key=lambda k: counts[k])
        summaries.append(f"{worst} had the most anomalies ({counts[worst]}).")
    return summaries


def analyze_plant(
    observations: list[PlantObservation],
    thresholds: AnalyticsThresholds | None = None,
) -> AnalyticsReport:
    """Full deterministic pipeline -> one structured AnalyticsReport."""
    if not observations:
        return AnalyticsReport()
    th = thresholds or DEFAULT_THRESHOLDS
    plant = calculate_plant_kpis(observations)
    machines = calculate_machine_kpis(observations)
    trends = analyze_trends(observations, stable_band_percent=th.trend_stable_band_percent)
    anomalies = detect_anomalies(observations, thresholds=th)
    summaries = compare_machines(machines, anomalies)
    ordered = sorted(observations, key=lambda o: o.timestamp)
    start, end = ordered[0].timestamp, ordered[-1].timestamp
    period = ReportingPeriod(
        start_timestamp=start,
        end_timestamp=end,
        duration_minutes=round((end - start).total_seconds() / 60.0, 2),
        observation_count=len(observations),
    )
    return AnalyticsReport(
        period=period, plant=plant, machines=machines, trends=trends,
        anomalies=anomalies, summaries=summaries,
    )
