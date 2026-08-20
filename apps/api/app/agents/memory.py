from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def empty_profile() -> dict[str, Any]:
    return {
        "weak_patterns": [],
        "last_next_focus": None,
        "criterion_ewma": {},
        "skill_ewma": {},
        "attempt_count": 0,
        "updated_at": None,
    }


def profile_for_prompt(profile: dict[str, Any] | None) -> dict[str, Any]:
    data = profile or empty_profile()
    return {
        "weak_patterns": (data.get("weak_patterns") or [])[:8],
        "last_next_focus": data.get("last_next_focus"),
        "criterion_ewma": data.get("criterion_ewma") or {},
        "skill_ewma": data.get("skill_ewma") or {},
        "attempt_count": int(data.get("attempt_count") or 0),
    }


def update_coach_profile(
    existing: dict[str, Any] | None,
    *,
    recurring_patterns: list[str] | None,
    next_focus: str | None,
    criteria: list[dict[str, Any]] | None,
    skill: str | None = None,
    skill_band: float | None = None,
) -> dict[str, Any]:
    profile = dict(existing or empty_profile())
    patterns = list(profile.get("weak_patterns") or [])
    for item in recurring_patterns or []:
        cleaned = (item or "").strip()
        if cleaned and cleaned not in patterns:
            patterns.insert(0, cleaned)
    profile["weak_patterns"] = patterns[:12]
    if next_focus:
        profile["last_next_focus"] = next_focus
    ewma: dict[str, float] = dict(profile.get("criterion_ewma") or {})
    alpha = 0.4
    for row in criteria or []:
        name = str(row.get("criterion") or "").strip()
        try:
            band = float(row.get("band"))
        except (TypeError, ValueError):
            continue
        if not name:
            continue
        prev = ewma.get(name)
        ewma[name] = band if prev is None else round((alpha * band) + ((1 - alpha) * prev), 2)
    profile["criterion_ewma"] = ewma
    if skill and skill_band is not None:
        skill_ewma: dict[str, float] = dict(profile.get("skill_ewma") or {})
        prev_skill = skill_ewma.get(skill)
        skill_ewma[skill] = (
            float(skill_band)
            if prev_skill is None
            else round((alpha * float(skill_band)) + ((1 - alpha) * prev_skill), 2)
        )
        profile["skill_ewma"] = skill_ewma
    profile["attempt_count"] = int(profile.get("attempt_count") or 0) + 1
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    return profile
