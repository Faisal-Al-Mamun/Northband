"""Deterministic cost-aware planner — no extra LLM call.

Decides which specialists are worth running after tools have produced facts.
Hiring-manager story: skip unused model calls; never skip the verifier or band math.
"""

from __future__ import annotations

from typing import Any

MIN_GRAMMAR_WORDS = 25
MIN_PERFORMANCE_HISTORY = 2

SKIP_CACHE = "identical_input_cache"
SKIP_SHORT = "response_too_short"
SKIP_HISTORY = "history_too_short"


def build_plan(
    *,
    skill: str,
    tools: dict[str, Any] | None,
    history: list[dict[str, Any]] | None,
    cache_hit: bool,
    cache_key: str | None = None,
) -> dict[str, Any]:
    word_count = int((tools or {}).get("word_count") or 0)
    history_len = len(history or [])
    skipped: list[dict[str, str]] = []

    run_specialist = True
    run_grammar = True
    run_feedback = True
    run_performance = True

    if cache_hit:
        run_specialist = False
        run_grammar = False
        specialist = skill if skill in {"writing", "speaking"} else "specialist"
        skipped.append({"agent": specialist, "reason": SKIP_CACHE})
        skipped.append({"agent": "grammar", "reason": SKIP_CACHE})

    if run_grammar and word_count < MIN_GRAMMAR_WORDS:
        run_grammar = False
        skipped.append({"agent": "grammar", "reason": SKIP_SHORT})

    if history_len < MIN_PERFORMANCE_HISTORY:
        run_performance = False
        skipped.append({"agent": "performance", "reason": SKIP_HISTORY})

    return {
        "run_specialist": run_specialist,
        "run_grammar": run_grammar,
        "run_feedback": run_feedback,
        "run_performance": run_performance,
        "use_cache": cache_hit,
        "cache_key": cache_key,
        "skipped": skipped,
        "word_count": word_count,
        "history_len": history_len,
    }


def skip_reason(plan: dict[str, Any] | None, agent: str) -> str | None:
    for item in (plan or {}).get("skipped") or []:
        if item.get("agent") == agent:
            return str(item.get("reason") or "skipped")
    return None
