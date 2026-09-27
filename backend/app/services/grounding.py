"""Deterministic numeric grounding validation.

Checks that the figures a report is required to reproduce actually appear
verbatim in the generated text. Conservative by design: anything not
reproduced exactly (including reformatted numbers like "16,183") is reported
as a mismatch. A mismatch means "not fully reproduced", not "hallucinated".

No NLP, no model calls — regex presence checks over normalized text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas.analytics import AnalyticsReport
from app.services.figures import key_numbers, required_numbers

__all__ = [
    "GroundingResult",
    "key_numbers",
    "required_numbers",
    "validate_report_numbers",
]


@dataclass
class GroundingResult:
    """Structured outcome of one grounding check."""

    numbers_verified: bool
    checked_count: int
    mismatches: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    """Strip thousands separators so "16,183" matches required "16183"."""
    return re.sub(r"(?<=\d),(?=\d)", "", text)


def _present(text: str, value: object) -> bool:
    """Boundary-aware verbatim presence (avoids "9" matching "192")."""
    return (
        re.search(r"(?<![\d.])" + re.escape(str(value)) + r"(?!\d)", text)
        is not None
    )


def validate_report_numbers(
    report: AnalyticsReport, generated_text: str
) -> GroundingResult:
    """Validate required figures against generated text, structurally."""
    text = _normalize(generated_text)
    mismatches = [
        f"{label}={value!r} not reproduced verbatim"
        for label, value in required_numbers(report)
        if not _present(text, value)
    ]
    total = len(required_numbers(report))
    return GroundingResult(
        numbers_verified=not mismatches,
        checked_count=total,
        mismatches=mismatches,
    )
