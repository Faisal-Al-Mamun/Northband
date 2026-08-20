from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.db.models import Attempt, LlmCallLog, StudyPlanItem, User
from app.db.session import get_db
from app.scoring.raw_to_band import is_full_paper, overall_ielts_band
from app.schemas.evaluations import (
    DrillStartResponse,
    ProgressPoint,
    ProgressSummary,
    SkillBreakdown,
    StudyPlanItemOut,
    StudyPlanUpdate,
)

router = APIRouter(prefix="/progress", tags=["progress"])


def _is_paper_attempt(item: Attempt) -> bool:
    if item.overall_band is None:
        return False
    obj = (item.report or {}).get("objective") or {}
    if obj.get("is_drill"):
        return False
    max_marks = obj.get("max_marks")
    if max_marks is not None and not is_full_paper(int(max_marks)):
        return False
    return True


@router.get("/summary", response_model=ProgressSummary)
async def progress_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgressSummary:
    all_attempts = (
        await db.scalars(
            select(Attempt)
            .where(Attempt.user_id == user.id, Attempt.overall_band.is_not(None))
            .order_by(Attempt.created_at.asc())
        )
    ).all()
    attempts = [item for item in all_attempts if _is_paper_attempt(item)]
    series = [
        ProgressPoint(
            attempt_id=str(item.id),
            skill=item.skill,
            module=item.module,
            task=item.task,
            overall_band=item.overall_band or 0,
            created_at=item.created_at.isoformat() if item.created_at else "",
        )
        for item in attempts
    ]
    skills: list[SkillBreakdown] = []
    for skill_name in ("listening", "reading", "writing", "speaking"):
        rows = [item for item in attempts if item.skill == skill_name]
        avg = round(sum(item.overall_band or 0 for item in rows) / len(rows), 2) if rows else None
        skills.append(
            SkillBreakdown(
                skill=skill_name,
                average_band=avg,
                attempt_count=len(rows),
                latest_band=rows[-1].overall_band if rows else None,
            )
        )
    next_focus = None
    type_accuracy: dict = {}
    if attempts:
        report = attempts[-1].report or {}
        performance = report.get("performance") or {}
        next_focus = performance.get("next_focus")
        for item in attempts:
            obj = (item.report or {}).get("objective") or {}
            for qtype, stats in (obj.get("by_type") or {}).items():
                bucket = type_accuracy.setdefault(qtype, {"correct": 0, "total": 0})
                bucket["correct"] += int(stats.get("correct") or 0)
                bucket["total"] += int(stats.get("total") or 0)
    latest_by_skill = {
        skill.skill: skill.latest_band for skill in skills if skill.latest_band is not None
    }
    overall = overall_ielts_band(latest_by_skill)
    return ProgressSummary(
        target_band=user.target_band,
        latest_overall=attempts[-1].overall_band if attempts else None,
        attempt_count=len(attempts),
        series=series[-30:],
        skills=skills,
        next_focus=next_focus,
        overall_estimate=overall.get("overall_band"),
        overall_confidence=overall.get("confidence"),
        missing_skills=overall.get("missing_skills") or [],
        type_accuracy=type_accuracy,
    )


@router.get("/study-plan", response_model=list[StudyPlanItemOut])
async def study_plan(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StudyPlanItemOut]:
    items = (
        await db.scalars(
            select(StudyPlanItem)
            .where(StudyPlanItem.user_id == user.id)
            .order_by(StudyPlanItem.created_at.desc())
            .limit(40)
        )
    ).all()
    seen: set[tuple[str, str]] = set()
    unique: list[StudyPlanItem] = []
    for item in items:
        key = (item.title.strip().lower(), (item.detail or "").strip().lower()[:80])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return [
        StudyPlanItemOut(
            id=str(item.id),
            title=item.title,
            detail=item.detail,
            skill_focus=item.skill_focus,
            status=item.status,
            drill_prompt=item.drill_prompt,
            drill_task=item.drill_task,
            drill_skill=item.drill_skill,
            created_at=item.created_at.isoformat() if item.created_at else "",
        )
        for item in unique
    ]


@router.patch("/study-plan/{item_id}", response_model=StudyPlanItemOut)
async def update_study_item(
    item_id: str,
    body: StudyPlanUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudyPlanItemOut:
    try:
        parsed_id = UUID(item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Item not found") from exc
    item = await db.scalar(
        select(StudyPlanItem).where(StudyPlanItem.id == parsed_id, StudyPlanItem.user_id == user.id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    item.status = body.status
    await db.commit()
    await db.refresh(item)
    return _item_out(item)


def _item_out(item: StudyPlanItem) -> StudyPlanItemOut:
    return StudyPlanItemOut(
        id=str(item.id),
        title=item.title,
        detail=item.detail,
        skill_focus=item.skill_focus,
        status=item.status,
        drill_prompt=item.drill_prompt,
        drill_task=item.drill_task,
        drill_skill=item.drill_skill,
        created_at=item.created_at.isoformat() if item.created_at else "",
    )


@router.post("/study-plan/{item_id}/drill", response_model=DrillStartResponse)
async def start_drill(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DrillStartResponse:
    try:
        parsed_id = UUID(item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Item not found") from exc
    item = await db.scalar(
        select(StudyPlanItem).where(StudyPlanItem.id == parsed_id, StudyPlanItem.user_id == user.id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    prompt = (item.drill_prompt or item.detail or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="This study item has no drill prompt yet")
    skill = item.drill_skill or "writing"
    if skill in {"reading", "listening"}:
        task = item.drill_task or "set"
    elif skill == "speaking":
        task = item.drill_task or "part2"
    else:
        task = item.drill_task or "task2"
    item.status = "in_progress"
    await db.commit()
    return DrillStartResponse(
        study_item_id=str(item.id),
        skill=skill,
        task=task,
        prompt=prompt,
    )


@router.get("/llm-usage")
async def llm_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Lightweight cost-control view of recent LLM calls for this user."""
    from app.db.models import EvaluationJob

    rows = (
        await db.execute(
            select(
                LlmCallLog.agent,
                func.count(LlmCallLog.id),
                func.coalesce(func.sum(LlmCallLog.prompt_tokens), 0),
                func.coalesce(func.sum(LlmCallLog.completion_tokens), 0),
            )
            .join(EvaluationJob, EvaluationJob.id == LlmCallLog.job_id)
            .where(EvaluationJob.user_id == user.id)
            .group_by(LlmCallLog.agent)
        )
    ).all()
    by_agent = [
        {
            "agent": agent,
            "calls": count,
            "prompt_tokens": int(prompt or 0),
            "completion_tokens": int(completion or 0),
        }
        for agent, count, prompt, completion in rows
    ]
    return {"by_agent": by_agent, "note": "Explain calls should stay cheaper than writing/speaking agents."}
