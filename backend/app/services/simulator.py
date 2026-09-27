"""Deterministic simulated plant-data generator.

Produces realistic, smoothly-varying observations (not independent random
numbers) and deliberately injects abnormal/fault episodes so Stage 3
anomaly detection has something to find.

Determinism: all randomness flows from ``random.Random(seed)``.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta

from app.schemas.plant import PlantObservation, PlantStatus

DEFAULT_MACHINE_IDS = ("MACHINE-001", "MACHINE-002", "MACHINE-003", "MACHINE-004")
DEFAULT_START = datetime(2026, 9, 1, 6, 0, 0)


def generate_plant_data(
    num_machines: int = 4,
    observations_per_machine: int = 48,
    start: datetime | str | None = None,
    interval_minutes: int = 15,
    seed: int = 42,
    fault_rate: float = 0.05,
    machine_ids: list[str] | tuple[str, ...] | None = None,
) -> list[PlantObservation]:
    """Generate simulated plant observations.

    Args:
        num_machines: how many machines to simulate.
        observations_per_machine: rows per machine.
        start: first timestamp (datetime, ISO string, or None for default).
        interval_minutes: sampling interval in minutes.
        seed: RNG seed for reproducibility.
        fault_rate: probability of a fault row (0..1).
        machine_ids: optional explicit IDs (else MACHINE-001..NNN).

    Returns:
        Validated ``PlantObservation`` list, ordered by machine then time.
    """
    if num_machines < 1:
        raise ValueError("num_machines must be >= 1")
    if observations_per_machine < 1:
        raise ValueError("observations_per_machine must be >= 1")
    if interval_minutes < 1:
        raise ValueError("interval_minutes must be >= 1")
    if not 0 <= fault_rate <= 1:
        raise ValueError("fault_rate must be between 0 and 1")

    if isinstance(start, str):
        start_dt = datetime.fromisoformat(start)
    else:
        start_dt = start or DEFAULT_START

    if machine_ids is None:
        ids = [f"MACHINE-{i:03d}" for i in range(1, num_machines + 1)]
    else:
        ids = list(machine_ids)[:num_machines]
        if len(ids) < num_machines:
            raise ValueError("not enough machine_ids for num_machines")

    rng = random.Random(seed)
    records: list[PlantObservation] = []

    for mid in ids:
        # Per-machine baselines give each unit a distinct personality.
        base_eff = rng.uniform(82.0, 92.0)
        base_temp = rng.uniform(62.0, 72.0)
        base_vib = rng.uniform(1.5, 3.0)
        base_prod = rng.uniform(90.0, 120.0)
        phase = rng.uniform(0, 2 * math.pi)

        for i in range(observations_per_machine):
            ts = start_dt + timedelta(minutes=i * interval_minutes)
            # Smooth diurnal-ish drift shared by temp/efficiency.
            drift = 5.0 * math.sin(2 * math.pi * i / 48 + phase)
            r = rng.random()

            if r < fault_rate:
                # --- Abnormal fault episode ---
                temp = rng.uniform(85.0, 105.0) + drift * 0.3
                vib = rng.uniform(7.5, 12.0)
                eff = rng.uniform(35.0, 60.0)
                prod = int(rng.uniform(0, 20))
                energy = prod * 0.12 + rng.uniform(8.0, 15.0)
                downtime = rng.uniform(10.0, 45.0)
                status = PlantStatus.FAULT
            elif r < fault_rate + 0.04:
                # --- Planned maintenance ---
                temp = rng.uniform(40.0, 55.0)
                vib = rng.uniform(0.2, 0.8)
                eff = 0.0
                prod = 0
                energy = rng.uniform(2.0, 5.0)
                downtime = float(interval_minutes)
                status = PlantStatus.MAINTENANCE
            elif r < fault_rate + 0.10:
                # --- Idle (no production, warm) ---
                temp = base_temp - rng.uniform(5.0, 12.0) + drift * 0.3
                vib = rng.uniform(0.3, 1.0)
                eff = 0.0
                prod = 0
                energy = rng.uniform(3.0, 7.0)
                downtime = rng.uniform(5.0, float(interval_minutes))
                status = PlantStatus.IDLE
            else:
                # --- Normal running with smooth + noisy variation ---
                temp = base_temp + drift * 0.4 + rng.gauss(0, 1.5)
                vib = abs(base_vib + rng.gauss(0, 0.4))
                eff = base_eff + drift * 0.3 + rng.gauss(0, 1.8)
                eff = min(99.5, max(70.0, eff))
                prod = int(base_prod * (0.85 + 0.3 * rng.random()) * (eff / 90.0))
                prod = max(0, prod)
                energy = prod * 0.12 + rng.uniform(6.0, 10.0)
                downtime = 0.0 if rng.random() > 0.03 else rng.uniform(0.5, 2.0)
                status = PlantStatus.RUNNING

            records.append(
                PlantObservation(
                    timestamp=ts,
                    machine_id=mid,
                    production_count=prod,
                    energy_consumption_kwh=round(energy, 2),
                    efficiency_percent=round(eff, 2),
                    temperature_c=round(temp, 2),
                    vibration_mm_s=round(vib, 2),
                    downtime_minutes=round(downtime, 2),
                    status=status,
                )
            )

        # Guarantee at least one abnormal row per machine so anomaly
        # detection always has signal, even at low fault_rate.
        machine_rows = [o for o in records if o.machine_id == mid]
        if not any(
            o.status == PlantStatus.FAULT or o.temperature_c > 85 or o.vibration_mm_s > 7
            for o in machine_rows
        ):
            victim = rng.randrange(len(machine_rows))
            row = machine_rows[victim]
            row.status = PlantStatus.FAULT
            row.temperature_c = round(rng.uniform(88.0, 100.0), 2)
            row.vibration_mm_s = round(rng.uniform(8.0, 11.0), 2)
            row.efficiency_percent = round(rng.uniform(40.0, 55.0), 2)
            row.downtime_minutes = round(rng.uniform(15.0, 40.0), 2)

    return records
