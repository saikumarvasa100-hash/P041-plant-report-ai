#!/usr/bin/env python
"""Generate every dataset fixture used for upload testing.

One fixture per ingestion profile, in that profile's own published column
layout. These are the files shipped in ``dataset-templates/``; regenerating
them must produce byte-identical output, so a reviewer's numbers match the
shipped notes.

Usage
-----
    python scripts/make_dataset_templates.py                    # -> backend/data/templates
    python scripts/make_dataset_templates.py --out ~/my/dir    # elsewhere
    python scripts/make_dataset_templates.py --check ~/Documents/P041-submission/dataset-templates

``--check`` regenerates into a temporary directory and diffs against an
existing set, so drift between the generator and the shipped files is caught
rather than silently overwriting good fixtures with stub ones.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_fixture_generic import build as build_generic  # noqa: E402
from gen_fixture_generic import write as write_generic  # noqa: E402
from gen_fixture_profiles import write_all as write_profiles  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO / "backend" / "data" / "templates"

NOTES = {
    "generic.csv": (
        "profile id : generic\n"
        "label      : Generic (native P041 schema)\n"
        "what it is : The native P041 column format -- the same schema the app\n"
        "             writes itself, so every field is a real measurement and\n"
        "             nothing is derived. This is the reference fixture: if a\n"
        "             profile-based upload disagrees with this file, the mapping\n"
        "             is what changed, not the data.\n"
        "derived    : None -- every field is measured in the source file.\n"
        "size       : 288 data rows, 4 machines (MACHINE-001..004),\n"
        "             2026-09-01 06:00 -> 23:45, 15-minute intervals.\n"
        "shape      : Built to exercise the console rather than to fill space.\n"
        "             - one 18-hour shift, four units with different character\n"
        "             - MACHINE-002 runs hot; MACHINE-004 is vibration-prone\n"
        "             - a late-shift efficiency sag on the two weaker units\n"
        "             - genuine threshold breaches against the backend defaults\n"
        "               (temperature 85/95 C, vibration 7/10 mm/s, efficiency 60/40,\n"
        "               downtime 10/30 min): overheat, vibration excursion,\n"
        "               two breakdowns, one planned maintenance window, idle stretches\n"
        "             - expected result: ~20 anomalies (10 critical, 10 medium),\n"
        "               OEE ~81%, production ~22,000 units\n"
        "determinism: fixed seed (19). Regenerating gives a byte-identical file.\n"
    ),
    "ai4i.csv": (
        "profile id : ai4i\n"
        "label      : AI4I 2020 Predictive Maintenance (UCI)\n"
        "what it is : Manufacturing prediction dataset. Product types L/M/H,\n"
        "             process conditions in Kelvin, tool wear, and a\n"
        "             machine-failure flag. No timestamps and no machine ids --\n"
        "             both are synthesised.\n"
        "derived    : 7 fields. timestamp (15-min steps), machine_id (from Type\n"
        "             L/M/H), production_count (from rpm), energy (from production),\n"
        "             efficiency (from tool wear), vibration (proxy from wear),\n"
        "             downtime (15 min on failure rows).\n"
        "size       : 72 rows, 18 hours of 15-minute steps (seed 41).\n"
        "shape      : The production order shifts L -> M -> H partway through, and\n"
        "             the H run carries enough tool wear to trigger genuine failures\n"
        "             late in the run (high process temperature, wear past ~240).\n"
        "             Expected: 3 machines, ~12 anomalies, 7 derived fields.\n"
        "determinism: fixed seed; regenerating gives a byte-identical file.\n"
    ),
    "iot-fault.csv": (
        "profile id : iot-fault\n"
        "label      : Industrial IoT Fault Detection (ziya07)\n"
        "what it is : Single-machine vibration and temperature telemetry with a\n"
        "             Fault Label of 0 / 1 / 2.\n"
        "derived    : 5 fields. machine_id (single-machine file), production_count\n"
        "             (from vibration), energy (from production), efficiency (from\n"
        "             temperature), downtime (20 min on fault rows).\n"
        "size       : 72 rows, 15-minute steps over 18 hours (seed 52).\n"
        "shape      : A bearing-degradation episode mid-run: vibration climbs\n"
        "             through both the 7 and 10 mm/s thresholds and temperature rises\n"
        "             with it, so the labels progress 0 -> 1 -> 2.\n"
        "             Expected: 1 machine, ~14 anomalies, 5 derived fields.\n"
        "determinism: fixed seed; regenerating gives a byte-identical file.\n"
    ),
    "iiot-timeseries.csv": (
        "profile id : iiot-timeseries\n"
        "label      : IIoT Sensor Data (zara2099)\n"
        "what it is : Simulated hourly plant telemetry: temperature, vibration,\n"
        "             machine load, active power, and a machine-failure flag. The\n"
        "             richest source layout -- energy comes from active_power.\n"
        "derived    : 4 fields. machine_id (single-machine file), production_count\n"
        "             (from load %), efficiency (from load %), downtime (30 min on\n"
        "             failure rows).\n"
        "size       : 72 rows, 15-minute steps over 18 hours (seed 63).\n"
        "shape      : A load-collapse event drops load to ~45, pushing mapped\n"
        "             efficiency under the 60 / 40 thresholds while temperature and\n"
        "             vibration rise. Expected: 1 machine, ~18 anomalies, 4 derived.\n"
        "determinism: fixed seed; regenerating gives a byte-identical file.\n"
    ),
    "smart-factory.csv": (
        "profile id : smart-factory\n"
        "label      : Smart Factory 2026 automation telemetry\n"
        "what it is : Conveyor and motor telemetry: temperature sensor, vibration\n"
        "             level, motor speed, energy consumption, an explicit\n"
        "             conveyor_status, and a failure flag.\n"
        "derived    : 4 fields. machine_id (single-machine file), production_count\n"
        "             (from rpm), efficiency (from temperature), downtime (15 min on\n"
        "             fault/maintenance).\n"
        "size       : 72 rows, 15-minute steps over 18 hours (seed 74).\n"
        "shape      : A realistic state sequence: running, then an overheat stop,\n"
        "             then running again, then a planned maintenance window\n"
        "             (status \"maintenance\", motor at 0 rpm), plus idle stretches.\n"
        "             Best fixture for showing status handling.\n"
        "             Expected: 1 machine, ~19 anomalies, 4 derived fields.\n"
        "determinism: fixed seed; regenerating gives a byte-identical file.\n"
    ),
    "azure.csv": (
        "profile id : azure\n"
        "label      : Azure / LBNL Predictive Maintenance\n"
        "what it is : Multi-unit rotating-machinery telemetry. THREE units, so\n"
        "             this is the only multi-machine source fixture.\n"
        "derived    : 4 fields. production_count (from rotation), energy (from\n"
        "             production), efficiency (from temperature), downtime (20 min on\n"
        "             failure rows).\n"
        "size       : 216 rows = 72 intervals x 3 units (seed 85).\n"
        "shape      : Unit 2 develops a bearing fault mid-run (vibration through\n"
        "             both thresholds); unit 3 sags in speed late in the shift. The\n"
        "             duplicate \"rotate\" column is deliberate: the published file has\n"
        "             it, and a CSV dict keeps the last occurrence.\n"
        "             Expected: 3 machines, ~12 anomalies, 4 derived fields.\n"
        "\n"
        "KNOWN LIMITATION: this is the WIDE form. The published LBNL files also\n"
        "ship in long \"telemetry\" form (datetime, machine, component, Value)\n"
        "which this profile will refuse, with an explanation. A pivot is not\n"
        "implemented.\n"
        "determinism: fixed seed; regenerating gives a byte-identical file.\n"
    ),
}


def generate(out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {"generic.csv": len(build_generic())}
    write_generic(out_dir)
    counts.update(write_profiles(out_dir))
    for name, body in NOTES.items():
        (out_dir / name.replace(".csv", ".notes.txt")).write_text(body, encoding="utf-8")
    return counts


def check_against(existing: Path) -> int:
    """Regenerate into a temp dir and diff against `existing`. Returns exit code."""
    if not existing.is_dir():
        print(f"error: not a directory: {existing}", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as td:
        fresh = Path(td)
        generate(fresh)
        drift = []
        for name in sorted(NOTES):
            a, b = fresh / name, existing / name
            if not b.is_file():
                drift.append(f"{name}: missing in {existing}")
            elif not filecmp.cmp(a, b, shallow=False):
                drift.append(f"{name}: DIFFERS from generator output")
            na, nb = fresh / name.replace(".csv", ".notes.txt"), existing / name.replace(".csv", ".notes.txt")
            if nb.is_file() and not filecmp.cmp(na, nb, shallow=False):
                drift.append(f"{name.replace('.csv', '.notes.txt')}: DIFFERS")
        if drift:
            print("DRIFT DETECTED:")
            for d in drift:
                print(f"  {d}")
            return 1
        print(f"no drift: {len(NOTES)} fixtures match the generator exactly")
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"output directory (default: {DEFAULT_OUT})")
    ap.add_argument("--check", type=Path, metavar="DIR",
                    help="verify DIR matches generator output instead of writing")
    args = ap.parse_args()

    if args.check:
        return check_against(args.check)

    counts = generate(args.out)
    for name in sorted(counts):
        print(f"wrote {args.out / name} ({counts[name]} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
