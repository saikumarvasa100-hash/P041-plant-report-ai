#!/usr/bin/env python
"""Generate the five profile-specific CSV fixtures.

Each fixture holds SOURCE data in that dataset's own published column layout,
not the native P041 schema -- the profile mapper is what converts it. So each
generator emits the real headers and physically plausible values, and the
interesting part is what survives the mapping: variation, genuine threshold
breaches, and machine-level character.

Values are chosen so the mapped result stays inside the PlantObservation bounds
(efficiency 0-100, temperature -20..150, vibration 0-50, production >= 0) and so
derived fields vary instead of collapsing to constants.

Every file is seeded, so a reviewer's figures match the shipped notes.
Regenerating must produce byte-identical files.
"""

from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

START = datetime(2026, 9, 1, 6, 0, 0)
STEP = 15
N = 72  # 18 hours at 15-minute intervals


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def ts(i: int) -> str:
    return (START + timedelta(minutes=STEP * i)).strftime("%Y-%m-%d %H:%M:%S")


def _write(out_dir: Path, name: str, header: list[str], rows: list[list]) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------- AI4I 2020
def ai4i(out_dir: Path) -> int:
    """UCI AI4I: temperatures in Kelvin, L/M/H product type, no timestamps."""
    rnd = random.Random(41)
    rows = []
    types = [("L", 295, 310, 1500, 40, 10),
             ("M", 298, 313, 1400, 45, 60),
             ("H", 302, 317, 1200, 50, 120)]
    for i in range(N):
        # Type shifts partway through, as a real production order would.
        base = types[0] if i < 26 else (types[1] if i < 50 else types[2])
        label, air, proc, rpm0, tq, wear0 = base
        air_k = air + rnd.gauss(0, 1.1)
        proc_k = proc + rnd.gauss(0, 1.3) + 2.4 * math.sin(i / 7.0)
        rpm = rpm0 + rnd.gauss(0, 22)
        torque = tq + rnd.gauss(0, 2.2)
        wear = max(0, wear0 + i * 0.9 + rnd.gauss(0, 1.6))
        fail = 0
        # A genuine tool-wear failure late in the H run.
        if label == "H" and 54 <= i <= 57:
            proc_k += 11.0
            wear += 130
            fail = 1
        rows.append([i + 1, label, round(air_k, 1), round(proc_k, 1),
                     int(max(0, rpm)), round(max(0.0, torque), 1), int(wear),
                     0.0, 0.0, fail])
    return _write(out_dir, "ai4i.csv", [
        "UDI", "Type", "Air temperature [K]", "Process temperature [K]",
        "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]", "Tare [Nm]",
        "Tare Process [g]", "Machine failure",
    ], rows)


# ------------------------------------------------- Industrial IoT fault
def iot_fault(out_dir: Path) -> int:
    """ziya07 layout: single machine, vibration/temperature, Fault Label 0/1/2."""
    rnd = random.Random(52)
    rows = []
    for i in range(N):
        vib = 2.3 + 0.3 * math.sin(i / 5.0) + abs(rnd.gauss(0, 0.25))
        temp = 66.0 + 2.0 * math.sin(i / 8.0) + rnd.gauss(0, 1.1)
        pressure = 101.2 + rnd.gauss(0, 0.6)
        label = 0
        # Bearing degradation through both the 7 and 10 mm/s thresholds.
        if 30 <= i <= 36:
            vib = 7.6 + (i - 30) * 0.72
            temp += 6.0
            pressure -= 1.4
            label = 2 if i >= 34 else 1
        rows.append([ts(i), round(vib, 3), round(temp, 2), round(pressure, 2), label])
    return _write(out_dir, "iot-fault.csv",
                  ["Timestamp", "Vibration", "Temperature", "Pressure", "Fault Label"], rows)


# ------------------------------------------------- IIoT timeseries (zara2099)
def iiot(out_dir: Path) -> int:
    """Hourly simulated plant telemetry with load, power and failure flag."""
    rnd = random.Random(63)
    rows = []
    for i in range(N):
        load = 88.0 + 6.0 * math.sin(i / 9.0) + rnd.gauss(0, 2.6)
        temp = 64.0 + 3.0 * math.sin(i / 7.0) + rnd.gauss(0, 1.3)
        vib = 2.0 + 0.25 * math.sin(i / 4.0) + abs(rnd.gauss(0, 0.2))
        power = round(max(1.0, load * 0.145 + rnd.gauss(0, 0.6)), 3)
        fail = 0
        # Load collapse pushes mapped efficiency under the 60/40 thresholds.
        if 40 <= i <= 45:
            load = 45.0 + rnd.uniform(-3, 3)
            temp += 7.5
            vib += 3.1
            power = round(max(1.0, load * 0.1), 3)
            fail = 1
        rows.append([ts(i), round(temp, 2), round(vib, 3),
                     round(clamp(load, 1, 100), 2), power, fail])
    return _write(out_dir, "iiot-timeseries.csv",
                  ["timestamp", "temperature", "vibration", "load",
                   "active_power", "machine_failure"], rows)


# ------------------------------------------------------- Smart factory 2026
def smart_factory(out_dir: Path) -> int:
    """Conveyor + motor telemetry with an explicit conveyor_status column."""
    rnd = random.Random(74)
    rows = []
    for i in range(N):
        temp = 63.0 + 2.5 * math.sin(i / 6.0) + rnd.gauss(0, 1.2)
        vib = 2.2 + 0.3 * math.sin(i / 5.0) + abs(rnd.gauss(0, 0.24))
        rpm = 1450 + 30 * math.sin(i / 8.0) + rnd.gauss(0, 14)
        energy = round(max(0.5, rpm * 0.0128 + rnd.gauss(0, 0.25)), 3)
        conv, fail = "running", 0
        # Overheat stop, then a planned maintenance window.
        if 22 <= i <= 25:
            temp = 96.0 + rnd.uniform(0, 5)
            vib += 2.6
            conv, fail = "stopped", 1
        elif 50 <= i <= 56:
            conv = "maintenance"
            temp -= 9.0
            vib = max(0.2, vib - 1.5)
            rpm = 0
            energy = round(rnd.uniform(0.4, 1.2), 3)
        elif rnd.random() < 0.04:
            conv = "idle"
            rpm = 0
            energy = round(rnd.uniform(0.5, 1.4), 3)
        rows.append([ts(i), round(temp, 2), round(vib, 3), int(max(0, rpm)),
                     energy, conv, fail])
    return _write(out_dir, "smart-factory.csv", [
        "timestamp", "temperature_sensor", "vibration_level", "motor_speed_rpm",
        "energy_consumption", "conveyor_status", "machine_failure",
    ], rows)


# ----------------------------------------------------- Azure / LBNL (wide)
def azure(out_dir: Path) -> int:
    """Wide form, one row per machine per interval.

    The duplicate ``rotate`` column is deliberate: the published file has it,
    and a CSV dict keeps the last occurrence.
    """
    rnd = random.Random(85)
    rows = []
    units = [(1, 1520, 420.0, 101.2, 2.2),
             (2, 1465, 418.5, 101.0, 2.4),
             (3, 1390, 419.2, 100.8, 2.5)]
    for i in range(N):
        for unit, rpm0, volt0, press0, vib0 in units:
            vib = vib0 + 0.22 * math.sin(i / 5.0) + abs(rnd.gauss(0, 0.2))
            temp = 65.0 + 2.4 * math.sin(i / 7.0) + rnd.gauss(0, 1.1)
            rpm = rpm0 + 18 * math.sin(i / 8.0) + rnd.gauss(0, 11)
            press = press0 + rnd.gauss(0, 0.4)
            volt = volt0 + rnd.gauss(0, 1.1)
            fail = 0
            if unit == 2 and 28 <= i <= 33:
                vib = 7.4 + (i - 28) * 0.78
                temp += 8.0
                fail = 1
            elif unit == 3 and i >= 60:
                rpm -= 210
                temp += 4.5
            rows.append([ts(i), unit, round(rpm, 1), round(volt, 1), round(rpm, 1),
                         round(press, 2), round(vib, 3), fail])
    return _write(out_dir, "azure.csv", [
        "datetime", "machineID", "rotate", "voltage", "rotate", "pressure",
        "vibration", "failure",
    ], rows)


BUILDERS = {
    "ai4i.csv": ai4i,
    "iot-fault.csv": iot_fault,
    "iiot-timeseries.csv": iiot,
    "smart-factory.csv": smart_factory,
    "azure.csv": azure,
}


def write_all(out_dir: Path) -> dict[str, int]:
    return {name: fn(out_dir) for name, fn in BUILDERS.items()}


if __name__ == "__main__":
    d = Path(__file__).resolve().parents[1] / "data" / "templates"
    for name, n in write_all(d).items():
        print(f"wrote {d / name} ({n} rows)")
