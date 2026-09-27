#!/usr/bin/env python3
"""Regenerate backend/data/sample_plant_data.csv deterministically.

Usage (from repo root):
    PYTHONPATH=backend ~/.venvs/plant-report-ai/bin/python scripts/generate_sample_data.py
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.simulator import generate_plant_data  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "backend" / "data" / "sample_plant_data.csv"

recs = generate_plant_data(
    num_machines=4, observations_per_machine=48, seed=7, fault_rate=0.06
)
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(recs[0].model_dump().keys()))
    w.writeheader()
    for r in recs:
        w.writerow(r.model_dump())
print(f"wrote {len(recs)} rows -> {OUT}")
