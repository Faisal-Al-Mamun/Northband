from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.events import patch_job_progress
from app.agents.memory import update_coach_profile
from app.agents.prompts import EXPLAIN_SYSTEM
from app.config import settings
from app.db.models import (
    Attempt,
    ContentSet,
    CriterionScore,
    EvaluationJob,
    ExplanationCache,
    Question,
    StudyPlanItem,
    User,
)
from app.db.session import SessionLocal
from app.llm.router import llm_router
from app.scoring.objective import normalize_answer
from app.scoring.raw_to_band import is_full_paper
from pydantic import BaseModel, Field
from sqlalchemy.orm.attributes import flag_modified


class ExplainItem(BaseModel):
    question_id: str
    explanation: str
    tip: str = ""
    skill_tag: str = "general"
    trap_type: str = ""


class ExplainBatchOutput(BaseModel):
    items: list[ExplainItem] = Field(default_factory=list)


async def _load_questions(set_id: UUID) -> tuple[ContentSet, list[dict[str, Any]]]:
    async with SessionLocal() as db:
        content = await db.scalar(
            select(ContentSet)
            .options(
                selectinload(ContentSet.questions).selectinload(Question.answer_key),
                selectinload(ContentSet.passages),
                selectinload(ContentSet.audio_assets),
            )
            .where(ContentSet.id == set_id)
        )
        if content is None:
            raise ValueError("Content set not found")
        questions = []
        for q in sorted(content.questions, key=lambda item: item.order_index):
            key = q.answer_key
            questions.append(
                {
                    "id": str(q.id),
                    "number": q.number,
                    "qtype": q.qtype,
                    "stem": q.stem,
                    "skill_tags": list(q.skill_tags or []),
                    "marks": q.marks,
                    "word_limit": q.word_limit,
                    "answer_key": {
                        "canonical": key.canonical if key else "",
                        "acceptable_variants": list(key.acceptable_variants or []) if key else [],
                        "normalization": dict(key.normalization or {}) if key else {},
                        "multi_blank": dict(key.multi_blank or {}) if key else {},
                        "key_version": key.key_version if key else 1,
                    },
                }
            )
        return content, questions


async def _cached_explanations(misses: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    found: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    async with SessionLocal() as db:
        for miss in misses:
            wrong = normalize_answer(miss.get("given"))
            row = await db.scalar(
                select(ExplanationCache).where(
                    ExplanationCache.question_id == UUID(miss["question_id"]),
                    ExplanationCache.key_version == int(miss.get("key_version") or 1),
                    ExplanationCache.wrong_normalized == wrong,
                )
            )
            if row:
                found.append({"question_id": miss["question_id"], **(row.explanation or {})})
            else:
                missing.append(miss)
    return found, missing


async def _batch_explain(
    *,
    job_id: str,
    skill: str,
    context: str,
    misses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not misses:
        return []
    cached, need = await _cached_explanations(misses)
    if not need:
        return cached
    payload = [
        {
            "question_id": m["question_id"],
            "stem": m.get("stem"),
            "given": m.get("given"),
            "canonical": m.get("canonical"),
            "qtype": m.get("qtype"),
            "skill_tags": m.get("skill_tags"),
        }
        for m in need[:12]
    ]
    try:
        result = await llm_router.complete_json(
            agent="explain",
            system=EXPLAIN_SYSTEM,
            user=f"Skill: {skill}\nContext:\n{context[:4000]}\n\nWrong items:\n{json.dumps(payload)}",
            schema=ExplainBatchOutput,
            job_id=UUID(job_id),
        )
        explanations = [item.model_dump() for item in result.items]
    except Exception:
        explanations = [
            {
                "question_id": m["question_id"],
                "explanation": f"Expected “{m.get('canonical')}”. Check the wording in the text carefully.",
                "tip": "Underline the key phrase before answering.",
                "skill_tag": (m.get("skill_tags") or ["general"])[0],
            }
            for m in need
        ]

    async with SessionLocal() as db:
        for miss in need:
            match = next((e for e in explanations if e.get("question_id") == miss["question_id"]), None)
            if not match:
                continue
            db.add(
                ExplanationCache(
                    question_id=UUID(miss["question_id"]),
                    key_version=int(miss.get("key_version") or 1),
                    wrong_normalized=normalize_answer(miss.get("given")),
                    explanation=match,
                    model=settings.llm_default_model,
                )
            )
        await db.commit()
    return cached + explanations


def _objective_confidence(graded: dict[str, Any]) -> float:
    earned = float(graded.get("earned_marks") or 0)
    maximum = float(graded.get("max_marks") or 0) or 1.0
    attempted = sum(1 for item in (graded.get("per_item") or []) if str(item.get("given") or "").strip())
    ratio = earned / maximum
    if attempted and earned == 0:
        return 0.42
    if ratio >= 0.8:
        return 0.9
    if ratio >= 0.5:
        return 0.82
    if ratio >= 0.25:
        return 0.7
    return 0.55


async def persist_objective_result(state: dict[str, Any]) -> None:
    job_id = state["job_id"]
    graded = state.get("graded") or {}
    max_marks = int(graded.get("max_marks") or 0)
    drill = not is_full_paper(max_marks)
    band = state.get("band")
    if drill:
        band = None
    table = state.get("table") or ""
    feedback = state.get("feedback") or {}
    explanations = state.get("explanations") or []
    report = {
        "disclaimer": "Band scores are AI/practice estimates. Objective items are marked against answer keys.",
        "objective": {
            **graded,
            "table_id": table,
            "mode": state.get("mode") or "practice",
            "content_set_id": state.get("content_set_id"),
            "content_title": state.get("content_title"),
            "explanations": explanations,
            "transcripts": state.get("transcripts") or [],
            "coach_trace": state.get("tool_trace") or [],
            "is_drill": drill,
        },
        "scores": {
            "criteria": [] if drill else [
                {
                    "criterion": "Objective accuracy",
                    "band": band,
                    "rationale": f"{graded.get('earned_marks', 0)}/{graded.get('max_marks', 0)} marks",
                }
            ],
            "overall_band": band,
            "confidence": _objective_confidence(graded) if not drill else 0.7,
            "scoring_notes": (
                f"Drill {graded.get('earned_marks', 0)}/{max_marks} — accuracy only, not an IELTS band."
                if drill
                else f"Deterministic key grading ({table}). Coach loop investigated misses with tools."
            ),
        },
        "feedback": feedback,
        "performance": state.get("performance")
        or {
            "trends": [],
            "plateau": False,
            "next_focus": "accuracy",
            "comparison_note": "Objective skill attempt recorded.",
        },
    }

    async with SessionLocal() as db:
        job = await db.get(EvaluationJob, UUID(job_id))
        if job is None:
            return
        attempt = Attempt(
            job_id=job.id,
            user_id=job.user_id,
            skill=job.skill,
            module=job.module,
            task=job.task,
            prompt=state.get("content_title") or "",
            input_text=json.dumps(state.get("answers") or {}),
            transcript=None,
            overall_band=band,
            bank_item_id=UUID(str(state["content_set_id"])) if state.get("content_set_id") else None,
            report=report,
        )
        db.add(attempt)
        await db.flush()
        if band is not None:
            db.add(
                CriterionScore(
                    attempt_id=attempt.id,
                    criterion="Objective accuracy",
                    band=band,
                    evidence=f"{graded.get('earned_marks', 0)}/{graded.get('max_marks', 0)}",
                )
            )
        skill = state.get("content_skill") or job.skill
        for action in feedback.get("actions") or []:
            db.add(
                StudyPlanItem(
                    user_id=job.user_id,
                    attempt_id=attempt.id,
                    title=str(action.get("title", "Practice"))[:255],
                    detail=str(action.get("detail", "")),
                    skill_focus=str(action.get("skill_focus", skill))[:40],
                    drill_prompt=action.get("drill_prompt"),
                    drill_task=action.get("drill_task"),
                    drill_skill=action.get("drill_skill") or skill,
                )
            )
        user = await db.get(User, job.user_id)
        if user is not None:
            weak_tags = []
            for miss in (graded.get("misses") or [])[:5]:
                weak_tags.extend(miss.get("skill_tags") or [])
            user.coach_profile = update_coach_profile(
                user.coach_profile,
                recurring_patterns=weak_tags,
                next_focus=(report.get("performance") or {}).get("next_focus") if not drill else None,
                criteria=[] if drill else ((report.get("scores") or {}).get("criteria") or []),
                skill=job.skill,
                skill_band=band,
            )
            flag_modified(user, "coach_profile")
        job.status = "completed"
        job.stage = "completed"
        job.partial_report = report
        job.error = None
        await db.commit()
    await patch_job_progress(job_id, stage="completed", partial=report)


async def run_objective_evaluation(job_id: str) -> None:
    from app.agents.objective_graph import run_objective_graph

    await run_objective_graph(job_id)
