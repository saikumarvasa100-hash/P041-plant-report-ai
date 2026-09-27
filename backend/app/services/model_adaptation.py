"""Future model-adaptation interface (no training happens here).

Defines the honest path toward domain fine-tuning without pulling GPU /
training dependencies into the core runtime: dataset preparation and
manifest helpers over the synthetic examples from ``services.dataset``.
Actual training (runners, base models, CUDA) lives outside this project.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.dataset import HUMAN_REVIEWED_SOURCE, SYNTHETIC_SOURCE, validate_training_example


def prepare_training_dataset(
    examples: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split examples into (valid, invalid-with-reasons). Pure stdlib."""
    valid, invalid = [], []
    for ex in examples:
        problems = validate_training_example(ex)
        if problems:
            invalid.append({"example_seed": ex.get("seed"), "problems": problems})
        else:
            valid.append(ex)
    return valid, invalid


def validate_training_dataset(examples: list[dict[str, Any]]) -> list[str]:
    """Corpus-level checks beyond per-example validation."""
    problems: list[str] = []
    if not examples:
        problems.append("empty dataset")
        return problems
    sources = {ex.get("source") for ex in examples}
    if HUMAN_REVIEWED_SOURCE not in sources:
        problems.append(
            "no human-reviewed examples: corpus is synthetic-only; "
            "fine-tuning on it alone is not validated"
        )
    return problems


def get_training_manifest(examples: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe a prepared corpus for a future training run."""
    from collections import Counter

    valid, invalid = prepare_training_dataset(examples)
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "num_examples": len(valid),
        "num_invalid": len(invalid),
        "sources": dict(Counter(ex.get("source") for ex in valid)),
        "report_types": dict(Counter(ex.get("report_type") for ex in valid)),
        "note": "synthetic examples only unless human-reviewed entries are added",
    }
