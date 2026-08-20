from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.auth.security import get_current_user
from app.content.assign import next_mock_blueprint
from app.db.models import Attempt, EvaluationJob, MockBlueprint, MockSession, User
from app.db.session import get_db
from app.schemas.content import MockBlueprintOut, MockSessionCreate, MockSessionOut
from app.scoring.bands import combine_writing_bands
from app.scoring.raw_to_band import overall_ielts_band

router = APIRouter(prefix="/mocks", tags=["mocks"])


def _blueprint_out(item: MockBlueprint | None) -> MockBlueprintOut | None:
    if item is None:
        return None
    return MockBlueprintOut(
        id=str(item.id),
        module=item.module,
        title=item.title,
        listening_set_id=str(item.listening_set_id) if item.listening_set_id else None,
        reading_set_id=str(item.reading_set_id) if item.reading_set_id else None,
        writing_task1_prompt=item.writing_task1_prompt or "",
        writing_task2_prompt=item.writing_task2_prompt or "",
        speaking_cues=item.speaking_cues or {},
    )


def _session_out(session: MockSession, blueprint: MockBlueprint | None = None) -> MockSessionOut:
    return MockSessionOut(
        id=str(session.id),
        module=session.module,
        status=session.status,
        current_skill=session.current_skill,
        job_ids=session.job_ids or {},
        skill_bands=session.skill_bands or {},
        overall_band=session.overall_band,
        confidence=session.confidence,
        blueprint=_blueprint_out(blueprint),
    )


@router.get("/blueprints", response_model=list[MockBlueprintOut])
async def list_blueprints(
    module: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MockBlueprintOut]:
    query = select(MockBlueprint).where(MockBlueprint.review_status == "published")
    if module:
        query = query.where(MockBlueprint.module == module)
    rows = (await db.scalars(query.order_by(MockBlueprint.title))).all()
    return [_blueprint_out(row) for row in rows if row]


@router.post("/sessions", response_model=MockSessionOut)
async def start_session(
    body: MockSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MockSessionOut:
    blueprint = None
    if body.blueprint_id:
        blueprint = await db.get(MockBlueprint, UUID(body.blueprint_id))
    if blueprint is None:
        blueprint = await next_mock_blueprint(db, user, module=body.module)
    if blueprint is None:
        raise HTTPException(status_code=404, detail="No mock blueprint for this module")
    session = MockSession(
        user_id=user.id,
        blueprint_id=blueprint.id,
        module=blueprint.module,
        status="in_progress",
        current_skill="listening",
        job_ids={},
        skill_bands={},
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _session_out(session, blueprint)


@router.get("/sessions/{session_id}", response_model=MockSessionOut)
async def get_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MockSessionOut:
    session = await db.get(MockSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Mock session not found")
    blueprint = await db.get(MockBlueprint, session.blueprint_id) if session.blueprint_id else None
    return _session_out(session, blueprint)


@router.post("/sessions/{session_id}/attach/{skill}", response_model=MockSessionOut)
async def attach_job(
    session_id: UUID,
    skill: str,
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MockSessionOut:
    if skill not in {"listening", "reading", "writing", "writing_task1", "speaking"}:
        raise HTTPException(status_code=400, detail="Invalid skill")
    session = await db.get(MockSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Mock session not found")
    job = await db.get(EvaluationJob, UUID(job_id))
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    jobs = dict(session.job_ids or {})
    jobs[skill] = str(job.id)
    session.job_ids = jobs
    flag_modified(session, "job_ids")

    attempt = await db.scalar(select(Attempt).where(Attempt.job_id == job.id))
    bands = dict(session.skill_bands or {})
    if attempt and attempt.overall_band is not None:
        bands[skill] = attempt.overall_band
        session.skill_bands = bands
        flag_modified(session, "skill_bands")

    order = ["listening", "reading", "writing", "speaking"]
    if skill == "writing_task1":
        session.current_skill = "writing"
    elif skill in order and order.index(skill) < len(order) - 1:
        session.current_skill = order[order.index(skill) + 1]
    elif skill in order:
        session.current_skill = "done"
        session.status = "completed"

    writing_bands = [bands[k] for k in ("writing_task1", "writing") if isinstance(bands.get(k), (int, float))]
    if len(writing_bands) == 2:
        bands["writing"] = combine_writing_bands(writing_bands[0], writing_bands[1])
        session.skill_bands = bands
        flag_modified(session, "skill_bands")

    result = overall_ielts_band({k: bands.get(k) for k in order})
    session.overall_band = result["overall_band"]
    session.confidence = result["confidence"]
    await db.commit()
    await db.refresh(session)
    blueprint = await db.get(MockBlueprint, session.blueprint_id) if session.blueprint_id else None
    return _session_out(session, blueprint)


@router.post("/sessions/{session_id}/refresh", response_model=MockSessionOut)
async def refresh_bands(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MockSessionOut:
    session = await db.get(MockSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Mock session not found")
    bands = dict(session.skill_bands or {})
    for skill, job_id in (session.job_ids or {}).items():
        job = await db.get(EvaluationJob, UUID(job_id))
        if not job:
            continue
        attempt = await db.scalar(select(Attempt).where(Attempt.job_id == job.id))
        if attempt and attempt.overall_band is not None:
            bands[skill] = attempt.overall_band
    writing_bands = [bands[k] for k in ("writing_task1", "writing") if isinstance(bands.get(k), (int, float))]
    if len(writing_bands) == 2:
        bands["writing"] = combine_writing_bands(writing_bands[0], writing_bands[1])
    session.skill_bands = bands
    flag_modified(session, "skill_bands")
    result = overall_ielts_band({k: bands.get(k) for k in ("listening", "reading", "writing", "speaking")})
    session.overall_band = result["overall_band"]
    session.confidence = result["confidence"]
    four = ("listening", "reading", "writing", "speaking")
    if all(isinstance(bands.get(k), (int, float)) for k in four):
        session.status = "completed"
        session.current_skill = "done"
    await db.commit()
    await db.refresh(session)
    blueprint = await db.get(MockBlueprint, session.blueprint_id) if session.blueprint_id else None
    return _session_out(session, blueprint)
