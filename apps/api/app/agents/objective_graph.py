"""LangGraph for Reading/Listening: keys first, then a tool-using coach loop."""

from __future__ import annotations

import json
from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from app.agents.coach_tools import run_coach_tool
from app.agents.events import patch_job_progress
from app.agents.prompts import COACH_SYSTEM, FEEDBACK_SYSTEM, PERFORMANCE_SYSTEM
from app.config import settings
from app.db.models import EvaluationJob, User
from app.db.session import SessionLocal
from app.llm.router import llm_router
from app.schemas.agents import CoachStepOutput, FeedbackAgentOutput, PerformanceAgentOutput
from app.scoring.objective import grade_attempt
from app.scoring.raw_to_band import is_full_paper, raw_to_band, table_for_skill
from app.services.payload import read_job_payload

MAX_COACH_STEPS = 8


class ObjectiveState(TypedDict, total=False):
    job_id: str
    skill: str
    module: str
    mode: str
    content_set_id: str
    answers: dict[str, Any]
    questions: list[dict[str, Any]]
    context: str
    content_title: str
    content_skill: str
    transcripts: list[dict[str, str]]
    graded: dict[str, Any]
    band: float
    table: str
    notes: list[dict[str, Any]]
    tool_trace: list[dict[str, str]]
    explanations: list[dict[str, Any]]
    feedback: dict[str, Any]
    performance: dict[str, Any]
    error: str | None
    warnings: list[str]


async def ingest_objective(state: ObjectiveState) -> ObjectiveState:
    job_id = state["job_id"]
    await patch_job_progress(job_id, stage="ingest")
    async with SessionLocal() as db:
        job = await db.get(EvaluationJob, UUID(job_id))
        if job is None:
            return {**state, "error": "Job not found"}
        job.status = "running"
        job.stage = "ingest"
        await db.commit()
        user = await db.get(User, job.user_id)
        memory = (user.coach_profile if user else None) or {}

    payload = read_job_payload(job_id)
    set_id = payload.get("content_set_id")
    if not set_id:
        return {**state, "error": "content_set_id missing"}

    from app.agents.objective_flow import _load_questions

    content, questions = await _load_questions(UUID(set_id))
    context_bits = [p.body for p in content.passages] + [a.transcript for a in content.audio_assets]
    return {
        **state,
        "skill": job.skill,
        "module": job.module or content.module,
        "mode": payload.get("mode") or "practice",
        "content_set_id": str(content.id),
        "answers": payload.get("answers") or {},
        "questions": questions,
        "context": "\n\n".join(context_bits),
        "content_title": content.title,
        "content_skill": content.skill,
        "transcripts": [
            {"section": a.section_label, "transcript": a.transcript}
            for a in content.audio_assets
        ]
        if content.skill == "listening"
        else [],
        "warnings": [],
        "coach_memory": memory,
    }


async def grade_objective(state: ObjectiveState) -> ObjectiveState:
    if state.get("error"):
        return state
    job_id = state["job_id"]
    await patch_job_progress(job_id, stage="grading")
    graded = grade_attempt(state["questions"], state.get("answers") or {})
    table = table_for_skill(
        state.get("skill") if state.get("skill") in {"reading", "listening"} else state["content_skill"],
        "academic" if state.get("module") == "shared" else (state.get("module") or "academic"),
    )
    band = raw_to_band(graded["earned_marks"], table_id=table, max_marks=graded["max_marks"])
    drill = not is_full_paper(graded["max_marks"])
    ratio = (graded["earned_marks"] / graded["max_marks"]) if graded["max_marks"] else 0
    await patch_job_progress(
        job_id,
        stage="scoring",
        partial={
            "objective": {
                "earned_marks": graded["earned_marks"],
                "max_marks": graded["max_marks"],
                "overall_band": band,
                "is_drill": drill,
                "by_type": graded["by_type"],
            },
            "scores": {
                "overall_band": band,
                "confidence": 0.9 if (not drill and ratio >= 0.5) else (0.78 if not drill else 0.7),
                "criteria": [],
                "scoring_notes": (
                    "Drill — accuracy only; not converted to a paper band."
                    if drill
                    else "Key-based score"
                ),
            },
        },
    )
    return {**state, "graded": graded, "band": band, "table": table, "notes": [], "tool_trace": []}


async def coach_loop(state: ObjectiveState) -> ObjectiveState:
    if state.get("error"):
        return state
    misses = list((state.get("graded") or {}).get("misses") or [])
    if not misses:
        return {**state, "notes": []}

    await patch_job_progress(state["job_id"], stage="coaching")
    notes: list[dict[str, Any]] = list(state.get("notes") or [])
    trace: list[dict[str, str]] = []
    last_action = "none"
    observation = "(none)"

    for step in range(MAX_COACH_STEPS):
        noted_ids = {str(item.get("question_id")) for item in notes}
        remaining = [m for m in misses if str(m.get("question_id")) not in noted_ids]
        user = (
            f"STEP: {step}\nLAST_ACTION: {last_action}\n"
            f"NOTES_COUNT: {len(notes)}\nREMAINING_MISSES: {len(remaining)}\n"
            f"MISSES:\n{json.dumps(misses[:12], ensure_ascii=False)}\n\n"
            f"LAST_OBSERVATION:\n{observation[:2500]}"
        )
        try:
            step_out = await llm_router.complete_json(
                agent="coach",
                system=COACH_SYSTEM,
                user=user,
                schema=CoachStepOutput,
                job_id=UUID(state["job_id"]),
            )
        except Exception:
            break

        action = (step_out.action or "finish").strip()
        last_action = action
        if action == "note_explanation":
            qid = step_out.question_id or (str(remaining[0]["question_id"]) if remaining else "")
            if qid:
                notes.append(
                    {
                        "question_id": qid,
                        "explanation": step_out.explanation or "Compare the wording with the source.",
                        "tip": step_out.tip or "Underline names, numbers, and negatives.",
                        "trap_type": step_out.trap_type or "",
                        "skill_tag": step_out.skill_tag or "accuracy",
                    }
                )
            observation = f"Saved note for {qid}. Notes={len(notes)} remaining={max(0, len(remaining) - 1)}"
            trace.append({"action": action, "observation": observation})
            if not remaining or len(notes) >= len(misses):
                break
            continue
        if action == "finish":
            trace.append({"action": "finish", "observation": step_out.thought})
            break

        observation = run_coach_tool(
            action,
            question_id=step_out.question_id,
            query=step_out.query,
            questions=state.get("questions") or [],
            misses=misses,
            context=state.get("context") or "",
        )
        trace.append({"action": action, "observation": observation[:500]})

    return {**state, "notes": notes, "tool_trace": trace}


async def synthesize(state: ObjectiveState) -> ObjectiveState:
    if state.get("error"):
        return state
    graded = state.get("graded") or {}
    misses = list(graded.get("misses") or [])
    notes = list(state.get("notes") or [])
    by_id = {str(item.get("question_id")): item for item in notes}
    explanations: list[dict[str, Any]] = []
    need: list[dict[str, Any]] = []
    for miss in misses:
        qid = str(miss.get("question_id"))
        if qid in by_id:
            explanations.append(by_id[qid])
        else:
            need.append(miss)

    if need and settings.explain_llm_enabled:
        from app.agents.objective_flow import _batch_explain

        extra = await _batch_explain(
            job_id=state["job_id"],
            skill=state.get("content_skill") or state.get("skill") or "reading",
            context=state.get("context") or "",
            misses=need,
        )
        explanations.extend(extra)
    else:
        for miss in need:
            explanations.append(
                {
                    "question_id": miss["question_id"],
                    "explanation": f"Expected “{miss.get('canonical')}”.",
                    "tip": "Re-read the exact wording in the text or audio.",
                    "skill_tag": (miss.get("skill_tags") or ["general"])[0],
                }
            )

    feedback = {
        "strengths": ["You handled several question types accurately."] if graded.get("earned_marks") else [],
        "weaknesses": [f"Review {m.get('qtype')} items" for m in misses[:3]],
        "actions": [],
        "examiner_summary": (
            f"Score {graded.get('earned_marks', 0)}/{graded.get('max_marks', 0)}"
            + (
                f" → estimated band {state.get('band', 0):.1f} ({state.get('mode')} mode)."
                if state.get("band") is not None
                else " (drill — not converted to a paper band)."
            )
        ),
    }
    for miss in misses[:3]:
        tag = (miss.get("skill_tags") or ["accuracy"])[0]
        feedback["actions"].append(
            {
                "title": f"Drill: {tag}",
                "detail": f"Revisit question {miss.get('number')}: expected “{miss.get('canonical')}”.",
                "skill_focus": tag,
                "drill_prompt": miss.get("stem"),
                "drill_task": "set",
                "drill_skill": state.get("content_skill") or state.get("skill"),
            }
        )

    try:
        coach = await llm_router.complete_json(
            agent="feedback",
            system=FEEDBACK_SYSTEM,
            user=json.dumps(
                {
                    "skill": state.get("content_skill"),
                    "graded": {
                        "earned_marks": graded.get("earned_marks"),
                        "max_marks": graded.get("max_marks"),
                        "by_type": graded.get("by_type"),
                        "misses": misses[:8],
                    },
                    "band": state.get("band"),
                    "coach_notes": notes[:8],
                    "tool_trace": (state.get("tool_trace") or [])[-6:],
                }
            ),
            schema=FeedbackAgentOutput,
            job_id=UUID(state["job_id"]),
        )
        feedback = coach.model_dump()
    except Exception:
        pass

    performance = {
        "trends": [],
        "plateau": False,
        "next_focus": (misses[0].get("skill_tags") or ["accuracy"])[0] if misses else "accuracy",
        "comparison_note": "Objective skill attempt recorded.",
    }
    try:
        perf = await llm_router.complete_json(
            agent="performance",
            system=PERFORMANCE_SYSTEM,
            user=json.dumps(
                {
                    "skill": state.get("content_skill"),
                    "band": state.get("band"),
                    "by_type": graded.get("by_type"),
                    "misses": [{"qtype": m.get("qtype"), "tags": m.get("skill_tags")} for m in misses[:8]],
                }
            ),
            schema=PerformanceAgentOutput,
            job_id=UUID(state["job_id"]),
        )
        performance = perf.model_dump()
    except Exception:
        pass

    return {**state, "explanations": explanations, "feedback": feedback, "performance": performance}


async def persist_objective(state: ObjectiveState) -> ObjectiveState:
    from app.agents.objective_flow import persist_objective_result

    if state.get("error"):
        async with SessionLocal() as db:
            job = await db.get(EvaluationJob, UUID(state["job_id"]))
            if job:
                job.status = "failed"
                job.stage = "failed"
                job.error = str(state["error"])[:4000]
                await db.commit()
        await patch_job_progress(state["job_id"], stage="failed", extra={"error": state["error"]})
        return state
    await persist_objective_result(state)
    return state


def _after_ingest(state: ObjectiveState) -> str:
    return "persist" if state.get("error") else "grade"


def build_objective_graph():
    graph = StateGraph(ObjectiveState)
    graph.add_node("ingest", ingest_objective)
    graph.add_node("grade", grade_objective)
    graph.add_node("coach_loop", coach_loop)
    graph.add_node("synthesize", synthesize)
    graph.add_node("persist", persist_objective)
    graph.add_edge(START, "ingest")
    graph.add_conditional_edges("ingest", _after_ingest, {"grade": "grade", "persist": "persist"})
    graph.add_edge("grade", "coach_loop")
    graph.add_edge("coach_loop", "synthesize")
    graph.add_edge("synthesize", "persist")
    graph.add_edge("persist", END)
    return graph.compile()


objective_graph = build_objective_graph()


async def run_objective_graph(job_id: str) -> None:
    await objective_graph.ainvoke({"job_id": job_id})
