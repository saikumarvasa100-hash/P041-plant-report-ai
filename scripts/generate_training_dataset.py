#!/usr/bin/env python3
"""Generate a synthetic report-example dataset (JSONL) deterministically.

Usage (from repo root):
    PYTHONPATH=backend ~/.venvs/plant-report-ai/bin/python scripts/generate_training_dataset.py \
        --seeds 7 11 21 --machines 2 4 --types daily weekly --observations 24

Output: backend/data/training/report_examples.jsonl
Every line is validated before writing; invalid lines abort the run.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.dataset import generate_dataset, validate_training_example  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "backend" / "data" / "training" / "report_examples.jsonl"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[7, 11, 21])
    ap.add_argument("--machines", type=int, nargs="+", default=[2, 4])
    ap.add_argument("--types", nargs="+", default=["daily", "weekly"])
    ap.add_argument("--observations", type=int, default=24)
    args = ap.parse_args()

    examples = generate_dataset(args.seeds, args.machines, args.types, args.observations)
    bad = [(i, validate_training_example(ex)) for i, ex in enumerate(examples)]
    bad = [(i, p) for i, p in bad if p]
    if bad:
        print(f"refusing to write: {len(bad)} invalid examples, e.g. {bad[0]}")
        sys.exit(1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"wrote {len(examples)} examples -> {OUT}")


if __name__ == "__main__":
    main()
