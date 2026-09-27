#!/usr/bin/env python
"""Generate the native-schema (generic profile) CSV fixture.

A 3-row fixture produced an almost-empty dashboard when uploaded, which is not a
fair test of the console. This generates a multi-machine, multi-shift dataset
with the shapes real plant data has:

  * a working day across several machines
  * 15-minute intervals
  * per-machine character (one runs hot, one is vibration-prone, one sags)
  * genuine threshold breaches (overheat, vibration, downtime, efficiency drop)
  * maintenance and idle stretches, not just running/fault

Values stay inside the PlantObservation bounds the backend enforces:
production >= 0, energy >= 0, efficiency 0-100, temperature -20..150,
vibration 0-50, downtime >= 0, status in running|idle|maintenance|fault.

The breaches are calibrated against the backend's demonstration thresholds
(temp 85/95 C, vibration 7/10 mm/s, efficiency 60/40, downtime 10/30 min), so
they are honest readings that cross a real line rather than values bent to
trip a rule.

Deterministic: the same file every time, so a reviewer's figures match the
notes. Regenerating must produce a byte-identical file.
"""

from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 19
START = datetime(2026, 9, 1, 6, 0, 0)
INTERVAL_MIN = 15
MACHINES = ["MACHINE-001", "MACHINE-002", "MACHINE-003", "MACHINE-004"]

# Per-machine character: (efficiency, temp offset, vibration base, yield, sag)
PROFILE = {
    "MACHINE-001": dict(eff=88.0, temp_off=0.0, vib=2.1, yld=95, sag=0.0),
    "MACHINE-002": dict(eff=83.0, temp_off=4.5, vib=2.8, yld=78, sag=6.0),  # runs hot
    "MACHINE-003": dict(eff=91.0, temp_off=-2.0, vib=1.8, yld=112, sag=0.0),  # best unit
    "MACHINE-004": dict(eff=80.0, temp_off=1.5, vib=3.6, yld=88, sag=9.0),   # vibration-prone
}

# Scheduled events: (machine, interval index, kind)
EVENTS = {
    "MACHINE-002": [(26, "heat"), (27, "heat"), (28, "heat"), (46, "stop")],
    "MACHINE-004": [(18, "vib"), (19, "vib"), (57, "maint"), (58, "maint"), (59, "maint")],
    "MACHINE-003": [(64, "vib")],
    "MACHINE-001": [(38, "stop")],
}

FIELDS = ["timestamp", "machine_id", "production_count", "energy_consumption_kwh",
          "efficiency_percent", "temperature_c", "vibration_mm_s",
          "downtime_minutes", "status"]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def build() -> list[dict]:
    rnd = random.Random(SEED)
    rows = []
    for machine in MACHINES:
        p = PROFILE[machine]
        events = dict(EVENTS.get(machine, []))
        for i in range(72):  # 72 x 15 min = 18 hours, 06:00 -> 24:00
            ts = START + timedelta(minutes=INTERVAL_MIN * i)
            kind = events.get(i)

            # A slow efficiency sag late in the shift on the weaker units.
            drift = -p["sag"] * max(0.0, (i - 40) / 32.0)
            eff = p["eff"] + drift + rnd.gauss(0, 2.4)
            temp = 58.0 + p["temp_off"] + 6.0 * math.sin(i / 9.0) + rnd.gauss(0, 1.5)
            vib = p["vib"] + 0.35 * math.sin(i / 5.0) + abs(rnd.gauss(0, 0.22))
            downtime = 0.0
            status = "running"

            if kind == "heat":
                temp = 97.0 + rnd.uniform(0.0, 6.0)      # over the 95 critical
                eff -= 26.0
                vib += 2.4
            elif kind == "vib":
                vib = 11.4 + rnd.uniform(0.0, 1.4)        # over the 10 critical
                eff -= 14.0
                temp += 3.0
            elif kind == "stop":
                status = "fault"
                downtime = rnd.uniform(31.0, 44.0)        # over the 30 critical
                eff = clamp(24.0 + rnd.uniform(0, 8), 0, 100)
                vib += 1.2
                temp += 4.0
            elif kind == "maint":
                status = "maintenance"
                downtime = 15.0
                eff = clamp(52.0 + rnd.uniform(-4, 4), 0, 100)
                vib = max(0.1, vib - 1.5)
            elif rnd.random() < 0.035:
                status = "idle"
                eff = clamp(eff - 30.0, 0, 100)
                downtime = rnd.uniform(2.0, 6.0)
                vib = max(0.1, vib - 1.6)

            if status in ("fault", "maintenance"):
                production = 0
            else:
                load = max(0.15, min(1.0, eff / 100.0))
                production = int(max(0, p["yld"] * load + rnd.gauss(0, 5)))

            energy = round(max(0.0, production * (0.115 + rnd.uniform(-0.012, 0.02))
                               + rnd.uniform(1.4, 3.2)), 2)

            rows.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "machine_id": machine,
                "production_count": production,
                "energy_consumption_kwh": energy,
                "efficiency_percent": round(clamp(eff, 0.0, 100.0), 2),
                "temperature_c": round(clamp(temp, -20.0, 150.0), 2),
                "vibration_mm_s": round(clamp(vib, 0.0, 50.0), 2),
                "downtime_minutes": round(downtime, 2),
                "status": status,
            })

    rows.sort(key=lambda r: (r["timestamp"], r["machine_id"]))
    return rows


def write(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "generic.csv"
    rows = build()
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return path


if __name__ == "__main__":
    p = write(Path(__file__).resolve().parents[1] / "data" / "templates")
    print(f"wrote {p} ({len(build())} rows)")
