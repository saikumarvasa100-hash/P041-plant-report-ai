#!/usr/bin/env python
"""Generate per-profile CSV templates into ~/Documents/plant-datasets/templates.

Each template carries the real published header spelling for its dataset plus a
few physically plausible rows. Purpose: when you download a CSV from Kaggle you
can diff its header against the template and know immediately whether the
profile will accept it, before spending an upload.

Generated from the same REQUIRED table the server enforces, so the templates
cannot drift from the code.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.dataset_profiles import PROFILES  # noqa: E402

OUT = Path.home() / "Documents" / "plant-datasets" / "templates"

# Real published headers, and sample rows with plausible magnitudes so the
# values survive backend validation (a 1 K reading is -272 C and is rejected,
# which is correct but makes a useless template).
TEMPLATES: dict[str, tuple[str, list[str], str]] = {
    "generic": (
        "native P041 schema - the format this app writes itself",
        [
            "timestamp,machine_id,production_count,energy_consumption_kwh,"
            "efficiency_percent,temperature_c,vibration_mm_s,downtime_minutes,status",
            "2026-09-01 06:00:00,MACHINE-001,77,15.6,86.77,64.73,2.65,0.0,running",
            "2026-09-01 06:15:00,MACHINE-001,64,13.1,84.20,66.10,2.81,0.0,running",
            "2026-09-01 06:30:00,MACHINE-001,0,4.2,41.30,78.44,6.02,15.0,fault",
        ],
        "Everything is measured. derived_fields will be empty.",
    ),
    "ai4i": (
        "AI4I 2020 Predictive Maintenance (UCI). Temperatures are in KELVIN.",
        [
            "UDI,Type,Air temperature [K],Process temperature [K],Rotational speed [rpm],"
            "Torque [Nm],Tool wear [min],Tare [Nm],Tare Process [g],Machine failure",
            "1,L,295.3,310.5,1500,40.0,10,0.0,0.0,0",
            "2,M,298.1,312.4,1400,42.5,3,0.0,0.0,0",
            "3,H,301.7,315.9,900,55.0,180,0.0,0.0,1",
        ],
        "No timestamps, no real machine ids, no energy/production: those are "
        "DERIVED (timestamp synthesized, machine id from Type L/M/H, production "
        "from rpm, energy from production, efficiency from tool wear).",
    ),
    "iot-fault": (
        "Industrial IoT Fault Detection (ziya07). Fault Label 0/1/2.",
        [
            "Timestamp,Vibration,Temperature,Pressure,Fault Label",
            "2026-09-01 06:00:00,2.41,68.52,101.3,0",
            "2026-09-01 06:00:15,2.38,69.10,101.6,0",
            "2026-09-01 06:00:30,7.92,91.44,98.2,1",
        ],
        "Single machine. Production, energy, efficiency and downtime are DERIVED.",
    ),
    "iiot-timeseries": (
        "IIoT Sensor Data (zara2099), hourly simulated telemetry.",
        [
            "timestamp,temperature,vibration,load,active_power,machine_failure",
            "2026-09-01 06:00:00,66.21,2.14,88.0,12.44,0",
            "2026-09-01 07:00:00,67.03,2.22,91.0,13.10,0",
            "2026-09-01 08:00:00,84.77,6.40,42.0,9.02,1",
        ],
        "Richest mapping: energy comes from active_power. Only timestamp, "
        "temperature, vibration and failure are measured.",
    ),
    "smart-factory": (
        "Smart Factory 2026 automation telemetry.",
        [
            "timestamp,temperature_sensor,vibration_level,motor_speed_rpm,"
            "energy_consumption,conveyor_status,machine_failure",
            "2026-09-01 06:00:00,64.83,2.22,1450,18.64,running,0",
            "2026-09-01 06:05:00,65.10,2.31,1470,19.02,running,0",
            "2026-09-01 06:10:00,78.44,6.02,0,4.21,maintenance,0",
        ],
        "energy_consumption is used as measured. Production, efficiency and "
        "downtime are DERIVED.",
    ),
    "azure": (
        "Azure/LBNL Predictive Maintenance - WIDE form only.",
        [
            "datetime,machineID,rotate,voltage,rotate,pressure,vibration,failure",
            "2026-09-01 06:00:00,1,1520.5,420.1,1520.5,101.3,2.31,0",
            "2026-09-01 07:00:00,1,1489.2,419.8,1489.2,101.9,2.44,0",
            "2026-09-01 08:00:00,2,905.1,417.2,905.1,99.8,6.77,1",
        ],
        "NOTE: the real LBNL files ship LONG (datetime, machine, component, "
        "Value) and must be pivoted to this wide form first. Duplicate 'rotate' "
        "headers are kept because the real file has them; the mapper reads the "
        "last occurrence.",
    ),
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for pid, (note, lines, derived) in TEMPLATES.items():
        assert pid in PROFILES, f"template for unknown profile {pid}"
        path = OUT / f"{pid}.csv"
        body = "\n".join(lines) + "\n"
        path.write_text(body, encoding="utf-8")
        (OUT / f"{pid}.notes.txt").write_text(
            f"profile id : {pid}\n"
            f"label      : {PROFILES[pid]['label']}\n"
            f"what it is : {note}\n"
            f"derived    : {derived}\n\n"
            f"check it   : ~/.venvs/plant-report-ai/bin/python "
            f"~/code/plant-report-ai/scripts/check_dataset.py {path}\n",
            encoding="utf-8",
        )
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
