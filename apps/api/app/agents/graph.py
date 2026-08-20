from __future__ import annotations

import asyncio
import json
from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.analysis_cache import get as cache_get
from app.agents.analysis_cache import make_key as cache_key
from app.agents.analysis_cache import put as cache_put
from app.agents.events import patch_job_progress
from app.agents.exam_rules import apply_exam_ceilings, examiner_first_impression
from app.agents.memory import profile_for_prompt, update_coach_profile
from app.agents.planner import build_plan, skip_reason
from app.agents.prompts import (
    FEEDBACK_SYSTEM,
    GRAMMAR_SYSTEM,
    PERFORMANCE_SYSTEM,
    REVISION_SYSTEM,
    SCORING_SYSTEM,
    SPEAKING_SYSTEM,
    WRITING_SYSTEM,
    feedback_user_prompt,
    grammar_user_prompt,
    performance_user_prompt,
    revision_user_prompt,
    scoring_user_prompt,
    speaking_user_prompt,
    writing_user_prompt,
)
from app.agents.tools import analyze_text, word_count
from app.agents.verify import apply_grammar_reconciliation, verify_specialist
from app.config import settings
from app.db.models import Attempt, CriterionScore, EvaluationJob, LlmCallLog, StudyPlanItem, User
from app.db.session import SessionLocal
from app.llm.router import llm_router
from app.schemas.agents import (
    BandScoreOutput,
    FeedbackAgentOutput,
    GrammarAgentOutput,
    PerformanceAgentOutput,
    RevisionAgentOutput,
    SpeakingAgentOutput,
    StudyAction,
    WritingAgentOutput,
)
from app.scoring.bands import mean_band, round_half_band
from app.services.payload import read_job_payload
from app.services.stt import audio_duration_seconds, transcribe_audio


class EvaluationState(TypedDict, total=False):
    job_id: str
    user_id: str
    skill: str
    module: str
    task: str
    prompt: str
    essay_text: str | None
    transcript: str | None
    audio_path: str | None
    speaking_mode: str | None
    audio_meta: dict[str, Any]
    writing_analysis: dict[str, Any]
    speaking_analysis: dict[str, Any]
    grammar_analysis: dict[str, Any]
    band_scores: dict[str, Any]
    feedback: dict[str, Any]
    performance: dict[str, Any]
    tools: dict[str, Any]
    history: list[dict[str, Any]]
    coach_profile: dict[str, Any]
    parent_attempt: dict[str, Any] | None
    parent_attempt_id: str | None
    delta: dict[str, Any] | None
    target_band: float | None
    error: str | None
    warnings: list[str]
    plan: dict[str, Any]
    cached_analysis: dict[str, Any]
    agent_trace: dict[str, Any]


def _source_text(state: EvaluationState) -> str:
    return (state.get("essay_text") or state.get("transcript") or "").strip()


def _as_uuid(value: Any) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def _memory_json(state: EvaluationState) -> str:
    return json.dumps(profile_for_prompt(state.get("coach_profile")), ensure_ascii=False)


def _tools_json(state: EvaluationState) -> str:
    return json.dumps(state.get("tools") or {}, ensure_ascii=False)


def _grammar_json(state: EvaluationState) -> str:
    grammar = state.get("grammar_analysis") or {}
    slim = {
        "issues": grammar.get("issues") or [],
        "recurring_patterns": grammar.get("recurring_patterns") or [],
    }
    return json.dumps(slim, ensure_ascii=False)


async def _complete(
    *,
    agent: str,
    system: str,
    user: str,
    schema: type,
    job_id: str,
) -> Any:
    return await asyncio.wait_for(
        llm_router.complete_json(
            agent=agent,
            system=system,
            user=user,
            schema=schema,
            job_id=UUID(job_id),
        ),
        timeout=settings.llm_timeout_seconds,
    )


def _partial(state: EvaluationState, **extra: Any) -> dict[str, Any]:
    payload = {
        "tools": state.get("tools"),
        "writing": state.get("writing_analysis"),
        "speaking": state.get("speaking_analysis"),
        "grammar": state.get("grammar_analysis"),
        "scores": state.get("band_scores"),
        "feedback": state.get("feedback"),
        "performance": state.get("performance"),
        "delta": state.get("delta"),
        "warnings": state.get("warnings") or [],
        "agent_trace": state.get("agent_trace"),
        "disclaimer": (
            "Band scores are AI estimates for practice. They are not official IELTS results."
        ),
    }
    payload.update(extra)
    return payload


_TRACE_THESIS = (
    "Models proposed evidence; Python owned the band; invented quotes never reached the student."
)


def _empty_grammar(reason: str) -> dict[str, Any]:
    return {
        "issues": [],
        "recurring_patterns": [],
        "lexical_range_notes": f"Grammar specialist skipped: {reason}.",
        "vocabulary_upgrades": [],
    }


def _ensure_trace(state: EvaluationState) -> dict[str, Any]:
    trace = dict(state.get("agent_trace") or {})
    trace.setdefault("stages", [])
    trace.setdefault("calls", [])
    trace.setdefault("thesis", _TRACE_THESIS)
    if state.get("plan"):
        trace["plan"] = state["plan"]
    return trace


def _trace_stage(state: EvaluationState, **stage: Any) -> dict[str, Any]:
    trace = _ensure_trace(state)
    stages = list(trace.get("stages") or [])
    stages.append({key: value for key, value in stage.items() if value is not None})
    trace["stages"] = stages
    return trace


async def ingest_node(state: EvaluationState) -> EvaluationState:
    job_id = UUID(state["job_id"])
    await patch_job_progress(state["job_id"], stage="ingest")
    async with SessionLocal() as db:
        job = await db.get(EvaluationJob, job_id)
        if job is None:
            return {**state, "error": "Job not found"}
        job.status = "running"
        job.stage = "ingest"
        user = await db.get(User, job.user_id)
        history_rows = (
            await db.scalars(
                select(Attempt)
                .options(selectinload(Attempt.scores))
                .where(Attempt.user_id == job.user_id)
                .order_by(Attempt.created_at.desc())
                .limit(12)
            )
        ).all()
        parent = None
        parent_id = state.get("parent_attempt_id")
        if parent_id:
            try:
                parent_row = await db.scalar(
                    select(Attempt)
                    .options(selectinload(Attempt.scores))
                    .where(Attempt.id == UUID(str(parent_id)))
                )
            except ValueError:
                parent_row = None
            if parent_row and parent_row.user_id == job.user_id:
                parent = {
                    "id": str(parent_row.id),
                    "overall_band": parent_row.overall_band,
                    "criteria": [
                        {"criterion": row.criterion, "band": row.band} for row in parent_row.scores
                    ],
                    "prompt": parent_row.prompt,
                }
        await db.commit()
        history = [
            {
                "skill": row.skill,
                "module": row.module,
                "task": row.task,
                "overall_band": row.overall_band,
                "criteria": [{"criterion": item.criterion, "band": item.band} for item in row.scores],
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in reversed(history_rows)
        ]
        return {
            **state,
            "target_band": user.target_band if user else None,
            "coach_profile": (user.coach_profile if user else None) or {},
            "history": history,
            "parent_attempt": parent,
        }


async def tools_node(state: EvaluationState) -> EvaluationState:
    if state.get("error"):
        return state
    text = _source_text(state)
    tools = analyze_text(
        text=text,
        skill=state["skill"],
        module=state["module"],
        task=state["task"],
        prompt=state.get("prompt") or "",
    )
    meta = dict(state.get("audio_meta") or {})
    if meta.get("duration_seconds") and not tools.get("word_count"):
        pass
    if state.get("skill") == "speaking":
        tools["duration_seconds"] = meta.get("duration_seconds")
        tools["words_per_minute"] = meta.get("words_per_minute")
        tools["pronunciation_is_proxy"] = state.get("speaking_mode") != "audio"
    updated = {**state, "tools": tools, "agent_trace": _trace_stage(state, name="tools", kind="deterministic")}
    await patch_job_progress(
        state["job_id"],
        stage="tools",
        partial=_partial(updated),
        extra={"word_count": tools.get("word_count")},
    )
    return updated


async def plan_node(state: EvaluationState) -> EvaluationState:
    if state.get("error"):
        return state
    text = _source_text(state)
    key = cache_key(
        state["skill"],
        state.get("module") or "",
        state.get("task") or "",
        state.get("prompt") or "",
        text,
    )
    cached = cache_get(key)
    plan = build_plan(
        skill=state["skill"],
        tools=state.get("tools") or {},
        history=state.get("history") or [],
        cache_hit=cached is not None,
        cache_key=key,
    )
    updated = {
        **state,
        "plan": plan,
        "cached_analysis": cached or {},
        "agent_trace": _trace_stage(
            {**state, "plan": plan},
            name="plan",
            kind="router",
            skipped=plan.get("skipped") or [],
        ),
    }
    await patch_job_progress(state["job_id"], stage="plan", partial=_partial(updated))
    return updated


async def transcribe_node(state: EvaluationState) -> EvaluationState:
    if state.get("skill") != "speaking":
        return state
    await patch_job_progress(state["job_id"], stage="transcribe")
    if state.get("transcript"):
        text = state["transcript"] or ""
        duration = (state.get("audio_meta") or {}).get("duration_seconds")
        if state.get("audio_path") and duration is None:
            duration = audio_duration_seconds(state["audio_path"])
        words = word_count(text)
        wpm = round((words / duration) * 60, 1) if duration and duration > 0 else None
        return {
            **state,
            "speaking_mode": state.get("speaking_mode") or ("audio" if state.get("audio_path") else "text"),
            "audio_meta": {
                "duration_seconds": duration,
                "words_per_minute": wpm,
                "word_count": words,
            },
        }
    audio_path = state.get("audio_path")
    if not audio_path:
        return {**state, "error": "Speaking evaluation needs audio or a transcript"}
    try:
        text, _provider = await transcribe_audio(audio_path)
    except Exception as exc:
        return {**state, "error": f"Transcription failed: {exc}"}
    duration = audio_duration_seconds(audio_path)
    words = word_count(text)
    wpm = round((words / duration) * 60, 1) if duration and duration > 0 else None
    return {
        **state,
        "transcript": text,
        "speaking_mode": "audio",
        "audio_meta": {"duration_seconds": duration, "words_per_minute": wpm, "word_count": words},
    }


async def writing_node(state: EvaluationState) -> EvaluationState:
    if state.get("error") or state.get("skill") != "writing":
        return state
    result = await _complete(
        agent="writing",
        system=WRITING_SYSTEM,
        user=writing_user_prompt(
            module=state["module"],
            task=state["task"],
            prompt=state["prompt"],
            essay=state.get("essay_text") or "",
            tools=_tools_json(state),
            memory=_memory_json(state),
            grammar_issues=_grammar_json(state),
        ),
        schema=WritingAgentOutput,
        job_id=state["job_id"],
    )
    payload = result.model_dump()
    tools = state.get("tools") or {}
    if tools.get("word_count") is not None:
        payload["word_count"] = tools["word_count"]
    return {**state, "writing_analysis": payload}


async def speaking_node(state: EvaluationState) -> EvaluationState:
    if state.get("error") or state.get("skill") != "speaking":
        return state
    meta = state.get("audio_meta") or {}
    result = await _complete(
        agent="speaking",
        system=SPEAKING_SYSTEM,
        user=speaking_user_prompt(
            module=state["module"],
            task=state["task"],
            prompt=state["prompt"],
            transcript=state.get("transcript") or "",
            mode=state.get("speaking_mode") or "text",
            duration_seconds=meta.get("duration_seconds"),
            words_per_minute=meta.get("words_per_minute"),
            tools=_tools_json(state),
            memory=_memory_json(state),
            grammar_issues=_grammar_json(state),
        ),
        schema=SpeakingAgentOutput,
        job_id=state["job_id"],
    )
    payload = result.model_dump()
    payload["mode"] = state.get("speaking_mode") or payload.get("mode")
    if meta.get("words_per_minute") is not None:
        payload["words_per_minute"] = meta["words_per_minute"]
    if meta.get("duration_seconds") is not None:
        payload["duration_seconds"] = meta["duration_seconds"]
    if payload.get("mode") != "audio":
        pronunciation = dict(payload.get("pronunciation") or {})
        pronunciation["summary"] = (
            (pronunciation.get("summary") or "")
            + " Pronunciation is a text proxy, not an acoustic score."
        ).strip()
        payload["pronunciation"] = pronunciation
    return {**state, "speaking_analysis": payload}


async def grammar_node(state: EvaluationState) -> EvaluationState:
    if state.get("error"):
        return state
    text = _source_text(state)
    result = await _complete(
        agent="grammar",
        system=GRAMMAR_SYSTEM,
        user=grammar_user_prompt(text=text, skill=state["skill"]),
        schema=GrammarAgentOutput,
        job_id=state["job_id"],
    )
    payload = result.model_dump()
    kept_issues = []
    lowered = text.lower()
    for issue in payload.get("issues") or []:
        span = str(issue.get("span") or "").strip()
        if span and span.lower() in lowered:
            kept_issues.append(issue)
    payload["issues"] = kept_issues
    return {**state, "grammar_analysis": payload}


def _cache_analyses(state: EvaluationState, skill_key: str) -> None:
    key = (state.get("plan") or {}).get("cache_key")
    if not key or (state.get("plan") or {}).get("use_cache"):
        return
    payload = {
        skill_key: state.get(skill_key),
        "grammar_analysis": state.get("grammar_analysis"),
    }
    if payload.get(skill_key):
        cache_put(key, payload)


async def analyze_writing(state: EvaluationState) -> EvaluationState:
    await patch_job_progress(state["job_id"], stage="analyzing", partial=_partial(state))
    plan = state.get("plan") or {}
    cached = state.get("cached_analysis") or {}
    if plan.get("use_cache") and cached.get("writing_analysis"):
        merged = {
            **state,
            "writing_analysis": cached["writing_analysis"],
            "grammar_analysis": cached.get("grammar_analysis") or _empty_grammar("identical_input_cache"),
        }
        merged["agent_trace"] = _trace_stage(merged, name="writing", kind="cached")
        merged["agent_trace"] = _trace_stage(merged, name="grammar", kind="cached")
    else:
        run_grammar = plan.get("run_grammar", True)
        if run_grammar:
            writing, grammar = await asyncio.gather(writing_node(state), grammar_node(state))
        else:
            writing = await writing_node(state)
            grammar = {
                **state,
                "grammar_analysis": _empty_grammar(skip_reason(plan, "grammar") or "skipped"),
            }
        merged = {**state, **writing, **grammar}
        merged["agent_trace"] = _trace_stage(merged, name="writing", kind="llm")
        merged["agent_trace"] = _trace_stage(
            merged,
            name="grammar",
            kind="llm" if run_grammar else "skipped",
            reason=None if run_grammar else skip_reason(plan, "grammar"),
        )
        _cache_analyses(merged, "writing_analysis")
    await patch_job_progress(state["job_id"], stage="analyzing", partial=_partial(merged))
    return merged


async def analyze_speaking(state: EvaluationState) -> EvaluationState:
    await patch_job_progress(state["job_id"], stage="analyzing", partial=_partial(state))
    plan = state.get("plan") or {}
    cached = state.get("cached_analysis") or {}
    if plan.get("use_cache") and cached.get("speaking_analysis"):
        merged = {
            **state,
            "speaking_analysis": cached["speaking_analysis"],
            "grammar_analysis": cached.get("grammar_analysis") or _empty_grammar("identical_input_cache"),
        }
        merged["agent_trace"] = _trace_stage(merged, name="speaking", kind="cached")
        merged["agent_trace"] = _trace_stage(merged, name="grammar", kind="cached")
    else:
        run_grammar = plan.get("run_grammar", True)
        if run_grammar:
            speaking, grammar = await asyncio.gather(speaking_node(state), grammar_node(state))
        else:
            speaking = await speaking_node(state)
            grammar = {
                **state,
                "grammar_analysis": _empty_grammar(skip_reason(plan, "grammar") or "skipped"),
            }
        merged = {**state, **speaking, **grammar}
        merged["agent_trace"] = _trace_stage(merged, name="speaking", kind="llm")
        merged["agent_trace"] = _trace_stage(
            merged,
            name="grammar",
            kind="llm" if run_grammar else "skipped",
            reason=None if run_grammar else skip_reason(plan, "grammar"),
        )
        _cache_analyses(merged, "speaking_analysis")
    await patch_job_progress(state["job_id"], stage="analyzing", partial=_partial(merged))
    return merged


def _criteria_from_state(state: EvaluationState) -> list[tuple[str, float, str]]:
    if state.get("skill") == "writing":
        writing = state.get("writing_analysis") or {}
        keys = ("task_response", "coherence", "lexical", "grammar")
        rows = []
        for key in keys:
            item = writing.get(key) or {}
            rows.append(
                (
                    item.get("criterion") or key,
                    float(item.get("proposed_band") or 0),
                    item.get("summary") or "",
                )
            )
        return rows
    speaking = state.get("speaking_analysis") or {}
    keys = ("fluency", "lexical", "grammar", "pronunciation")
    rows = []
    for key in keys:
        item = speaking.get(key) or {}
        rows.append(
            (
                item.get("criterion") or key,
                float(item.get("proposed_band") or 0),
                item.get("summary") or "",
            )
        )
    return rows


def _build_delta(state: EvaluationState, criteria: list[dict[str, Any]], overall: float) -> dict[str, Any] | None:
    parent = state.get("parent_attempt")
    if not parent:
        return None
    previous = {row["criterion"]: row["band"] for row in parent.get("criteria") or []}
    rows = []
    for item in criteria:
        name = item["criterion"]
        prev = previous.get(name)
        current = item["band"]
        rows.append(
            {
                "criterion": name,
                "previous": prev,
                "current": current,
                "delta": None if prev is None else round(current - prev, 1),
            }
        )
    prev_overall = parent.get("overall_band")
    return {
        "parent_attempt_id": parent.get("id"),
        "previous_overall": prev_overall,
        "current_overall": overall,
        "overall_delta": None if prev_overall is None else round(overall - float(prev_overall), 1),
        "criteria": rows,
    }


async def verify_node(state: EvaluationState) -> EvaluationState:
    if state.get("error"):
        return state
    source = _source_text(state)
    issues = (state.get("grammar_analysis") or {}).get("issues") or []
    updated = dict(state)
    if state.get("skill") == "writing":
        analysis = verify_specialist(
            state.get("writing_analysis"), source, ("task_response", "coherence", "lexical", "grammar")
        )
        analysis = apply_grammar_reconciliation(analysis, issues)
        tools = state.get("tools") or {}
        if tools.get("word_count") is not None:
            analysis["word_count"] = tools["word_count"]
        updated["writing_analysis"] = analysis
    else:
        analysis = verify_specialist(
            state.get("speaking_analysis"), source, ("fluency", "lexical", "grammar", "pronunciation")
        )
        analysis = apply_grammar_reconciliation(analysis, issues)
        updated["speaking_analysis"] = analysis
    specialist = updated.get("writing_analysis") or updated.get("speaking_analysis") or {}
    updated["agent_trace"] = _trace_stage(
        updated,
        name="verify",
        kind="deterministic",
        quote_hit_rate=specialist.get("quote_hit_rate"),
        quotes_dropped=specialist.get("evidence_quote_dropped"),
        quotes_kept=specialist.get("evidence_quote_kept"),
    )
    await patch_job_progress(state["job_id"], stage="verify", partial=_partial(updated))
    return updated


def _deterministic_scores(state: EvaluationState) -> dict[str, Any]:
    raw = _criteria_from_state(state)
    deterministic = [
        {"criterion": name, "band": round_half_band(band), "rationale": note}
        for name, band, note in raw
    ]
    tools = state.get("tools") or {}
    deterministic, ceiling_warnings = apply_exam_ceilings(
        deterministic,
        skill=state["skill"],
        module=state.get("module") or "academic",
        task=state.get("task") or "",
        tools=tools,
    )
    overall = mean_band([item["band"] for item in deterministic])
    notes = "Bands are the mean of the four official-style criteria, rounded to the nearest 0.5."
    first = examiner_first_impression(tools, state["skill"], state.get("task") or "")
    if first:
        notes += f" Examiner first impression: {first}"
    confidence = 0.78
    if state.get("speaking_mode") == "text":
        confidence = min(confidence, 0.7)
        notes += " Pronunciation is a text/audio-proxy estimate, not an official examiner score."
    if tools.get("under_length"):
        confidence = min(confidence, 0.72)
        notes += " Response is under the expected word count."
    if ceiling_warnings:
        confidence = min(confidence, 0.7)
        notes += " Exam ceilings applied: " + "; ".join(ceiling_warnings[:3]) + "."
    specialist = state.get("writing_analysis") or state.get("speaking_analysis") or {}
    hit = specialist.get("quote_hit_rate")
    if isinstance(hit, (int, float)) and hit < 1:
        notes += f" {int(round((1 - hit) * 100))}% of model quotes were dropped because they were not in the response."
        confidence = min(confidence, 0.74)
    return {
        "criteria": deterministic,
        "overall_band": overall,
        "confidence": confidence,
        "scoring_notes": notes.strip(),
        "exam_ceilings": ceiling_warnings,
        "examiner_first_impression": first,
    }


async def scoring_node(state: EvaluationState) -> EvaluationState:
    if state.get("error"):
        return state
    payload = _deterministic_scores(state)
    if settings.scoring_llm_enabled:
        try:
            analyses = {
                "writing": state.get("writing_analysis"),
                "speaking": state.get("speaking_analysis"),
                "grammar": state.get("grammar_analysis"),
            }
            result = await _complete(
                agent="scoring",
                system=SCORING_SYSTEM,
                user=scoring_user_prompt(
                    skill=state["skill"],
                    analyses=json.dumps(analyses, ensure_ascii=False),
                    deterministic=json.dumps(
                        {"criteria": payload["criteria"], "overall_band": payload["overall_band"]}
                    ),
                ),
                schema=BandScoreOutput,
                job_id=state["job_id"],
            )
            notes = result.model_dump()
            payload["scoring_notes"] = notes.get("scoring_notes") or payload["scoring_notes"]
            payload["confidence"] = max(0.0, min(1.0, float(notes.get("confidence") or payload["confidence"])))
        except Exception as exc:
            warnings = list(state.get("warnings") or [])
            warnings.append(f"Scoring notes skipped: {exc}")
            state = {**state, "warnings": warnings}
    if state.get("speaking_mode") == "text":
        payload["confidence"] = min(float(payload["confidence"]), 0.7)
    delta = _build_delta(state, payload["criteria"], payload["overall_band"])
    updated = {**state, "band_scores": payload, "delta": delta}
    updated["agent_trace"] = _trace_stage(
        updated,
        name="scoring",
        kind="math",
        scoring_llm=bool(settings.scoring_llm_enabled),
    )
    await patch_job_progress(state["job_id"], stage="scoring", partial=_partial(updated))
    return updated


def _fallback_feedback(state: EvaluationState) -> dict[str, Any]:
    bands = state.get("band_scores") or {}
    lowest = min((bands.get("criteria") or [{"criterion": "grammar", "band": 6}]), key=lambda row: row.get("band", 9))
    focus = str(lowest.get("criterion") or "grammar")
    skill = state["skill"]
    task = "task2" if skill == "writing" else "part2"
    grammar = state.get("grammar_analysis") or {}
    patterns = grammar.get("recurring_patterns") or ["accuracy"]
    return FeedbackAgentOutput(
        strengths=["The response attempts the task."],
        weaknesses=[f"{focus} is the current bottleneck.", f"Recurring pattern: {patterns[0]}"],
        actions=[
            StudyAction(
                title=f"Drill: {focus}",
                detail=f"Spend 10 minutes on {focus} using this attempt's topic.",
                skill_focus="grammar" if "grammar" in focus.lower() else "task_response",
                drill_prompt=state.get("prompt") or "Rewrite your weakest paragraph with a clearer topic sentence.",
                drill_task=task,
            )
        ],
        examiner_summary="Fallback coach notes after the feedback model timed out or failed.",
    ).model_dump()


def _fallback_performance(state: EvaluationState) -> dict[str, Any]:
    history = state.get("history") or []
    direction = "flat"
    if len(history) >= 2:
        prev = history[-2].get("overall_band")
        current = (state.get("band_scores") or {}).get("overall_band")
        if prev is not None and current is not None:
            if current > prev:
                direction = "up"
            elif current < prev:
                direction = "down"
    lowest = min(
        (state.get("band_scores") or {}).get("criteria") or [{"criterion": "coherence", "band": 6}],
        key=lambda row: row.get("band", 9),
    )
    last_focus = (state.get("coach_profile") or {}).get("last_next_focus")
    focus = str(lowest.get("criterion") or "coherence")
    if last_focus and last_focus == focus and len((state.get("band_scores") or {}).get("criteria") or []) > 1:
        ranked = sorted((state.get("band_scores") or {}).get("criteria") or [], key=lambda row: row.get("band", 9))
        if len(ranked) > 1:
            focus = str(ranked[1].get("criterion") or focus)
    return PerformanceAgentOutput(
        trends=[{"label": "overall", "direction": direction, "note": "Computed without the performance model."}],
        plateau=direction == "flat" and len(history) >= 3,
        next_focus=focus,
        comparison_note="Fallback trend note.",
    ).model_dump()


async def coach_node(state: EvaluationState) -> EvaluationState:
    if state.get("error"):
        return state
    await patch_job_progress(state["job_id"], stage="coaching", partial=_partial(state))
    payload = {
        "bands": state.get("band_scores"),
        "writing": state.get("writing_analysis"),
        "speaking": state.get("speaking_analysis"),
        "grammar": state.get("grammar_analysis"),
        "tools": state.get("tools"),
        "delta": state.get("delta"),
    }
    current = {
        "skill": state["skill"],
        "module": state["module"],
        "task": state["task"],
        "overall_band": (state.get("band_scores") or {}).get("overall_band"),
        "criteria": (state.get("band_scores") or {}).get("criteria"),
    }
    warnings = list(state.get("warnings") or [])

    async def _feedback() -> dict[str, Any]:
        result = await _complete(
            agent="feedback",
            system=FEEDBACK_SYSTEM,
            user=feedback_user_prompt(
                skill=state["skill"],
                target_band=state.get("target_band"),
                payload=json.dumps(payload, ensure_ascii=False),
                memory=_memory_json(state),
            ),
            schema=FeedbackAgentOutput,
            job_id=state["job_id"],
        )
        return result.model_dump()

    async def _performance() -> dict[str, Any]:
        result = await _complete(
            agent="performance",
            system=PERFORMANCE_SYSTEM,
            user=performance_user_prompt(
                current=json.dumps(current),
                history=json.dumps(state.get("history") or []),
                memory=_memory_json(state),
            ),
            schema=PerformanceAgentOutput,
            job_id=state["job_id"],
        )
        return result.model_dump()

    plan = state.get("plan") or {}
    run_performance = plan.get("run_performance", True)
    feedback_task = asyncio.create_task(_feedback())
    performance_task = asyncio.create_task(_performance()) if run_performance else None
    feedback, performance = None, None
    try:
        feedback = await feedback_task
        feedback_kind = "llm"
    except Exception as exc:
        warnings.append(f"Feedback fallback used: {exc}")
        feedback = _fallback_feedback(state)
        feedback_kind = "fallback"
        if not feedback_task.done():
            feedback_task.cancel()
    if performance_task is None:
        performance = _fallback_performance(state)
        performance_kind = "skipped"
        warnings.append("Performance model skipped: not enough attempt history.")
    else:
        try:
            performance = await performance_task
            performance_kind = "llm"
        except Exception as exc:
            warnings.append(f"Performance fallback used: {exc}")
            performance = _fallback_performance(state)
            performance_kind = "fallback"
            if not performance_task.done():
                performance_task.cancel()
    updated = {**state, "feedback": feedback, "performance": performance, "warnings": warnings}
    updated["agent_trace"] = _trace_stage(updated, name="feedback", kind=feedback_kind)
    updated["agent_trace"] = _trace_stage(
        updated,
        name="performance",
        kind=performance_kind,
        reason=skip_reason(plan, "performance") if performance_kind == "skipped" else None,
    )
    await patch_job_progress(state["job_id"], stage="coaching", partial=_partial(updated))
    return updated


async def persist_node(state: EvaluationState) -> EvaluationState:
    job_id = UUID(state["job_id"])
    await patch_job_progress(state["job_id"], stage="persisting", partial=_partial(state))
    async with SessionLocal() as db:
        job = await db.get(EvaluationJob, job_id)
        if job is None:
            return state
        if state.get("error"):
            job.status = "failed"
            job.stage = "failed"
            job.error = state["error"][:4000]
            await db.commit()
            await patch_job_progress(state["job_id"], stage="failed", extra={"error": state["error"]})
            return state

        extra = read_job_payload(str(job.id))
        parent_id = extra.get("parent_attempt_id") or state.get("parent_attempt_id")
        logs = (
            await db.scalars(
                select(LlmCallLog)
                .where(LlmCallLog.job_id == job.id)
                .order_by(LlmCallLog.created_at.asc())
            )
        ).all()
        trace = _trace_stage(state, name="persist", kind="system")
        trace["calls"] = [
            {
                "agent": row.agent,
                "provider": row.provider,
                "model": row.model,
                "latency_ms": row.latency_ms,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "success": row.success,
            }
            for row in logs
        ]
        state = {**state, "agent_trace": trace}
        report = _partial(state)
        overall = (state.get("band_scores") or {}).get("overall_band")
        attempt = Attempt(
            job_id=job.id,
            user_id=job.user_id,
            skill=job.skill,
            module=job.module,
            task=job.task,
            prompt=state.get("prompt") or "",
            input_text=state.get("essay_text"),
            transcript=state.get("transcript"),
            audio_path=state.get("audio_path"),
            speaking_mode=state.get("speaking_mode"),
            overall_band=overall,
            parent_attempt_id=UUID(str(parent_id)) if parent_id else None,
            bank_item_id=_as_uuid(extra.get("bank_item_id") or state.get("bank_item_id")),
            report=report,
        )
        db.add(attempt)
        await db.flush()
        for item in (state.get("band_scores") or {}).get("criteria") or []:
            db.add(
                CriterionScore(
                    attempt_id=attempt.id,
                    criterion=item.get("criterion", "unknown"),
                    band=float(item.get("band") or 0),
                    evidence=item.get("rationale"),
                )
            )
        for action in (state.get("feedback") or {}).get("actions") or []:
            skill_focus = action.get("skill_focus", "general")
            drill_skill = job.skill
            drill_task = action.get("drill_task") or ("task2" if job.skill == "writing" else "part2")
            db.add(
                StudyPlanItem(
                    user_id=job.user_id,
                    attempt_id=attempt.id,
                    title=action.get("title", "Practice item")[:255],
                    detail=action.get("detail", ""),
                    skill_focus=skill_focus[:40],
                    drill_prompt=(action.get("drill_prompt") or action.get("detail") or "")[:4000] or None,
                    drill_task=str(drill_task)[:20],
                    drill_skill=drill_skill,
                )
            )
        user = await db.get(User, job.user_id)
        if user is not None:
            user.coach_profile = update_coach_profile(
                user.coach_profile,
                recurring_patterns=(state.get("grammar_analysis") or {}).get("recurring_patterns") or [],
                next_focus=(state.get("performance") or {}).get("next_focus"),
                criteria=(state.get("band_scores") or {}).get("criteria") or [],
                skill=job.skill,
                skill_band=(state.get("band_scores") or {}).get("overall_band"),
            )
            flag_modified(user, "coach_profile")
        study_item_id = extra.get("study_item_id")
        if study_item_id:
            try:
                item = await db.get(StudyPlanItem, UUID(str(study_item_id)))
            except ValueError:
                item = None
            if item and item.user_id == job.user_id:
                item.status = "done"
        job.status = "completed"
        job.stage = "completed"
        job.error = None
        job.partial_report = report
        await db.commit()
    await patch_job_progress(state["job_id"], stage="completed", partial=report)
    return state


def _after_ingest(state: EvaluationState) -> str:
    if state.get("error"):
        return "persist"
    if state.get("skill") == "speaking":
        return "transcribe"
    return "tools"


def _after_transcribe(state: EvaluationState) -> str:
    if state.get("error"):
        return "persist"
    return "tools"


def _after_tools(state: EvaluationState) -> str:
    if state.get("error"):
        return "persist"
    return "plan"


def _after_plan(state: EvaluationState) -> str:
    if state.get("error"):
        return "persist"
    if state.get("skill") == "speaking":
        return "analyze_speaking"
    return "analyze_writing"


def build_graph():
    graph = StateGraph(EvaluationState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("transcribe", transcribe_node)
    graph.add_node("tools", tools_node)
    graph.add_node("plan", plan_node)
    graph.add_node("analyze_writing", analyze_writing)
    graph.add_node("analyze_speaking", analyze_speaking)
    graph.add_node("verify", verify_node)
    graph.add_node("scoring", scoring_node)
    graph.add_node("coach", coach_node)
    graph.add_node("persist", persist_node)

    graph.add_edge(START, "ingest")
    graph.add_conditional_edges(
        "ingest",
        _after_ingest,
        {"transcribe": "transcribe", "tools": "tools", "persist": "persist"},
    )
    graph.add_conditional_edges(
        "transcribe",
        _after_transcribe,
        {"tools": "tools", "persist": "persist"},
    )
    graph.add_conditional_edges(
        "tools",
        _after_tools,
        {"plan": "plan", "persist": "persist"},
    )
    graph.add_conditional_edges(
        "plan",
        _after_plan,
        {
            "analyze_writing": "analyze_writing",
            "analyze_speaking": "analyze_speaking",
            "persist": "persist",
        },
    )
    graph.add_edge("analyze_writing", "verify")
    graph.add_edge("analyze_speaking", "verify")
    graph.add_edge("verify", "scoring")
    graph.add_edge("scoring", "coach")
    graph.add_edge("coach", "persist")
    graph.add_edge("persist", END)
    return graph.compile()


evaluation_graph = build_graph()


async def run_evaluation_job(job_id: str) -> None:
    async with SessionLocal() as db:
        job = await db.get(EvaluationJob, UUID(job_id))
        if job is None:
            return
        skill = job.skill
        attempt_seed = {
            "job_id": str(job.id),
            "user_id": str(job.user_id),
            "skill": job.skill,
            "module": job.module,
            "task": job.task,
        }
    if skill in {"reading", "listening"}:
        try:
            from app.agents.objective_flow import run_objective_evaluation

            await run_objective_evaluation(job_id)
        except Exception as exc:
            async with SessionLocal() as db:
                job = await db.get(EvaluationJob, UUID(job_id))
                if job:
                    job.status = "failed"
                    job.stage = "failed"
                    job.error = str(exc)[:4000]
                    await db.commit()
            await patch_job_progress(job_id, stage="failed", extra={"error": str(exc)[:500]})
        return
    extra = read_job_payload(job_id)
    initial: EvaluationState = {**attempt_seed, **extra}
    try:
        await evaluation_graph.ainvoke(initial)
    except Exception as exc:
        async with SessionLocal() as db:
            job = await db.get(EvaluationJob, UUID(job_id))
            if job:
                job.status = "failed"
                job.stage = "failed"
                job.error = str(exc)[:4000]
                await db.commit()
        await patch_job_progress(job_id, stage="failed", extra={"error": str(exc)[:500]})


async def run_revision(
    *,
    job_id: str,
    skill: str,
    prompt: str,
    response: str,
    span: str,
    weakest: str,
    target_band: float,
) -> RevisionAgentOutput:
    return await _complete(
        agent="revision",
        system=REVISION_SYSTEM,
        user=revision_user_prompt(
            skill=skill,
            prompt=prompt,
            response=response,
            span=span,
            weakest=weakest,
            target_band=target_band,
        ),
        schema=RevisionAgentOutput,
        job_id=job_id,
    )
