#!/usr/bin/env python
"""Check which dataset profile a CSV fits, before uploading it.

The dashboard refuses a file whose columns do not feed the chosen profile,
because mapping absent columns produces zeros and default constants that look
like real measurements. This tool answers the question locally and offline, so
you can find the right profile before spending an upload:

    PYTHONPATH=backend python scripts/check_dataset.py path/to/file.csv
    PYTHONPATH=backend python scripts/check_dataset.py file.csv --profile ai4i

With no --profile it scores every profile and ranks them, so you can see at a
glance which one your file matches. Exit code is 0 if at least one profile
fits, 1 if none do.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.dataset_profiles import (  # noqa: E402
    HINTS,
    PROFILES,
    REQUIRED,
    column_report,
)


def read_header(path: Path) -> list[str]:
    # utf-8-sig strips a BOM, which would otherwise corrupt the first column name.
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            return [c for c in row if c.strip()]
    return []


def count_rows(path: Path, limit: int = 100_000) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        next(reader, None)
        return sum(1 for _ in reader)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_path", type=Path, help="CSV file to inspect")
    ap.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        help="Check only this profile (default: score all and rank)",
    )
    args = ap.parse_args()

    if not args.csv_path.is_file():
        print(f"error: no such file: {args.csv_path}", file=sys.stderr)
        return 1

    header = read_header(args.csv_path)
    if not header:
        print(f"error: {args.csv_path} has no header row", file=sys.stderr)
        return 1

    print(f"file   : {args.csv_path}")
    print(f"columns: {len(header)}")
    print(f"header : {', '.join(header)}")
    try:
        print(f"rows   : {count_rows(args.csv_path)}")
    except (OSError, UnicodeDecodeError):
        print("rows   : (could not count)")
    print()

    profiles = [args.profile] if args.profile else sorted(PROFILES)
    reports = [column_report(header, p) for p in profiles]
    reports.sort(key=lambda r: (not r["ok"], -len(r["matched_groups"]), r["profile"]))

    any_ok = False
    for rep in reports:
        required = REQUIRED.get(rep["profile"], ())
        status = "MATCH" if rep["ok"] else "no match"
        if rep["ok"]:
            any_ok = True
        print(f"[{status:8}] {rep['profile']:16} {rep['label']}")
        if required:
            print(f"           matched {len(rep['matched_groups'])}/{len(required)} required groups")
            for g in rep["missing_groups"]:
                print(f"           missing: {g}")
        if rep["ok"] and rep["profile"] != "generic":
            print(f"           note: some fields will be DERIVED, not measured")
        if not rep["ok"] and rep["profile"] in HINTS:
            print(f"           hint: {HINTS[rep['profile']]}")
        print()

    if any_ok:
        best = next(r for r in reports if r["ok"])
        print(f"Use:  profile={best['profile']}")
        print(f"  curl -X POST 'http://localhost:8001/api/v1/data/upload?profile={best['profile']}' \\")
        print(f"       -F 'file=@{args.csv_path}'")
        return 0

    print("No profile fits this file.")
    print("If it already uses the native P041 column names it should match 'generic':")
    print("  timestamp, machine_id, production_count, energy_consumption_kwh,")
    print("  efficiency_percent, temperature_c, vibration_mm_s, downtime_minutes, status")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
