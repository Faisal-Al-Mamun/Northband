"""IELTS exam-condition rules applied after specialist analysis (deterministic)."""

from __future__ import annotations

from typing import Any


def apply_exam_ceilings(
    criteria: list[dict[str, Any]],
    *,
    skill: str,
    module: str,
    task: str,
    tools: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Cap bands the way an examiner would under hard exam rules.

    Returns updated criteria rows and human-readable warnings.
    """
    tools = tools or {}
    warnings: list[str] = []
    rows = [dict(item) for item in criteria]

    def _cap(name_substr: str, ceiling: float, reason: str) -> None:
        for row in rows:
            name = str(row.get("criterion") or "")
            if name_substr.lower() not in name.lower():
                continue
            try:
                band = float(row.get("band"))
            except (TypeError, ValueError):
                continue
            if band > ceiling:
                row["band"] = ceiling
                note = str(row.get("rationale") or "")
                row["rationale"] = f"{note} [Exam ceiling {ceiling}: {reason}]".strip()
                warnings.append(f"{name} capped at {ceiling} — {reason}")

    if skill == "writing":
        if tools.get("under_length"):
            expected = tools.get("expected_min_words") or (150 if task == "task1" else 250)
            words = tools.get("word_count")
            # Official-style: under length typically prevents 7+ on Task Response/Achievement.
            _cap(
                "Task",
                6.0,
                f"under minimum length ({words}/{expected} words)",
            )
        coverage = tools.get("task_coverage") or {}
        ratio = coverage.get("coverage_ratio")
        if task == "task1" and ratio is not None and ratio < 0.5:
            _cap("Task", 5.5, "fewer than half of the bullet/key features covered")
        if module == "academic" and task == "task1" and tools.get("overview_present") is False:
            _cap("Task", 6.0, "Academic Task 1 missing a clear overview")
        if module == "general" and task == "task1" and tools.get("overview_present") is False:
            # For GT letters, overview_present encodes purpose/tone markers.
            _cap("Task", 6.0, "General Training letter missing clear purpose/tone markers")

    if skill == "speaking":
        duration = tools.get("duration_seconds")
        wpm = tools.get("words_per_minute")
        # Extremely slow delivery usually cannot sustain band 7+ fluency.
        if isinstance(wpm, (int, float)) and 0 < wpm < 70:
            _cap("Fluency", 6.0, f"very slow delivery (~{wpm:.0f} WPM)")
        if task == "part2" and isinstance(duration, (int, float)):
            if duration < 20:
                _cap("Fluency", 4.0, f"Part 2 long turn too short ({duration:.0f}s)")
            elif duration < 45:
                _cap("Fluency", 5.5, f"Part 2 long turn well under 1–2 minutes ({duration:.0f}s)")
        if task == "full" and isinstance(duration, (int, float)):
            if duration < 180:
                _cap("Fluency", 4.0, f"full interview too short ({duration:.0f}s)")
            elif duration < 360:
                _cap("Fluency", 5.5, f"full interview well under 11–14 minutes ({duration:.0f}s)")
        coverage = tools.get("task_coverage") or {}
        ratio = coverage.get("coverage_ratio")
        if task in {"part2", "full"} and ratio is not None and ratio < 0.5:
            _cap("Fluency", 6.0, "fewer than half of the cue-card points covered")
        if tools.get("pronunciation_is_proxy"):
            for row in rows:
                if "pronunciation" in str(row.get("criterion") or "").lower():
                    row["rationale"] = (
                        str(row.get("rationale") or "")
                        + " [Pronunciation is a text/audio-meta proxy, not a live examiner score.]"
                    ).strip()

    return rows, warnings


def examiner_first_impression(tools: dict[str, Any] | None, skill: str, task: str) -> str:
    """What a trained examiner typically notices in the first half-minute."""
    tools = tools or {}
    notes: list[str] = []
    if skill == "writing":
        words = tools.get("word_count")
        expected = tools.get("expected_min_words")
        if words is not None and expected and words < expected:
            notes.append(f"Length first: {words} words vs {expected}+ expected — Task Response will be limited.")
        elif words is not None:
            notes.append(f"Length looks exam-plausible ({words} words).")
        if task == "task1" and tools.get("overview_present") is False:
            notes.append("No overview / letter purpose markers spotted in the opening.")
        if task == "task1" and (tools.get("task_coverage") or {}).get("missing"):
            missing = (tools.get("task_coverage") or {}).get("missing") or []
            notes.append(f"Possible uncovered bullets: {', '.join(missing[:3])}.")
        linkers = tools.get("linker_count")
        if isinstance(linkers, int) and linkers == 0:
            notes.append("Few/no linking phrases — coherence may feel list-like.")
    if skill == "speaking":
        fillers = tools.get("filler_count")
        if isinstance(fillers, int) and fillers >= 6:
            notes.append(f"High filler density ({fillers}) — fluency may sound hesitant.")
        if tools.get("pronunciation_is_proxy"):
            notes.append("Text-only mode: pronunciation is estimated, not heard.")
        duration = tools.get("duration_seconds")
        if task == "part2" and isinstance(duration, (int, float)) and duration < 45:
            notes.append(f"Part 2 long turn is short ({duration:.0f}s vs 1–2 minutes expected).")
        if task == "full" and isinstance(duration, (int, float)) and duration < 360:
            notes.append(f"Full interview is short ({duration:.0f}s vs 11–14 minutes expected).")
        missing = (tools.get("task_coverage") or {}).get("missing") or []
        if task in {"part2", "full"} and missing:
            notes.append(f"Cue-card points may be missing: {', '.join(missing[:3])}.")
    return " ".join(notes) if notes else "No hard exam-condition flags from tools."
