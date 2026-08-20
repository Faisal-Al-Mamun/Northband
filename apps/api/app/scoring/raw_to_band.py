"""Raw Listening/Reading score → approximate IELTS band (versioned tables)."""

from __future__ import annotations

from typing import Any

from app.scoring.bands import mean_band, round_half_band

# Approximate public conversion tables (practice estimates — not official).
# Format: minimum correct marks out of 40 → band
READING_ACADEMIC_V1: list[tuple[int, float]] = [
    (39, 9.0),
    (37, 8.5),
    (35, 8.0),
    (33, 7.5),
    (30, 7.0),
    (27, 6.5),
    (23, 6.0),
    (19, 5.5),
    (15, 5.0),
    (13, 4.5),
    (10, 4.0),
    (8, 3.5),
    (6, 3.0),
    (4, 2.5),
    (0, 0.0),
]

READING_GENERAL_V1: list[tuple[int, float]] = [
    (40, 9.0),
    (39, 8.5),
    (37, 8.0),
    (36, 7.5),
    (34, 7.0),
    (32, 6.5),
    (30, 6.0),
    (27, 5.5),
    (23, 5.0),
    (19, 4.5),
    (15, 4.0),
    (12, 3.5),
    (9, 3.0),
    (6, 2.5),
    (0, 0.0),
]

LISTENING_V1: list[tuple[int, float]] = [
    (39, 9.0),
    (37, 8.5),
    (35, 8.0),
    (32, 7.5),
    (30, 7.0),
    (26, 6.5),
    (23, 6.0),
    (18, 5.5),
    (16, 5.0),
    (13, 4.5),
    (10, 4.0),
    (8, 3.5),
    (6, 3.0),
    (4, 2.5),
    (0, 0.0),
]

TABLES: dict[str, list[tuple[int, float]]] = {
    "reading_academic_v1": READING_ACADEMIC_V1,
    "reading_general_v1": READING_GENERAL_V1,
    "listening_v1": LISTENING_V1,
}


FULL_PAPER_MARKS = 35


def is_full_paper(max_marks: int | None) -> bool:
    """True when the sit is long enough to convert raw marks to an IELTS-style band."""
    return int(max_marks or 0) >= FULL_PAPER_MARKS


def raw_to_band(correct: int, *, table_id: str, max_marks: int = 40) -> float | None:
    """Map raw marks to a practice band. Drills (under 35 marks) are not converted."""
    if not is_full_paper(max_marks):
        return None
    scaled = int(correct)
    if max_marks and max_marks != 40:
        scaled = int(round((correct / max_marks) * 40))
    table = TABLES.get(table_id) or LISTENING_V1
    for minimum, band in table:
        if scaled >= minimum:
            return float(band)
    return 0.0


def table_for_skill(skill: str, module: str) -> str:
    if skill == "listening":
        return "listening_v1"
    if module == "general":
        return "reading_general_v1"
    return "reading_academic_v1"


def overall_ielts_band(skill_bands: dict[str, float | None]) -> dict[str, Any]:
    present = {k: float(v) for k, v in skill_bands.items() if v is not None}
    missing = [s for s in ("listening", "reading", "writing", "speaking") if s not in present]
    if len(present) < 2:
        return {
            "overall_band": None,
            "confidence": round(len(present) / 4, 2),
            "missing_skills": missing,
            "estimated": True,
            "skills_used": present,
        }
    overall = mean_band(list(present.values()))
    confidence = round(len(present) / 4, 2)
    return {
        "overall_band": overall,
        "confidence": confidence,
        "missing_skills": missing,
        "estimated": len(present) < 4,
        "skills_used": present,
    }
