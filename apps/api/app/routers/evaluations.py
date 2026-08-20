from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.events import STAGE_LABELS, channel_for, get_redis
from app.agents.graph import run_revision
from app.auth.security import get_current_user
from app.db.models import Attempt, ContentSet, EvaluationJob, StudyPlanItem, User
from app.db.session import get_db
from app.queue import enqueue_evaluation
from app.schemas.evaluations import (
    EvaluationDetail,
    EvaluationSummary,
    ObjectiveEvaluationCreate,
    RevisionRequest,
    WritingEvaluationCreate,
)
from app.security.rate_limit import limit_evaluations
from app.security.uploads import save_audio_upload
from app.services.payload import read_job_payload, write_job_payload
from app.services.stt import transcribe_audio

router = APIRouter(tags=["evaluations"])


def _summary(job: EvaluationJob, attempt: Attempt | None = None) -> EvaluationSummary:
    return EvaluationSummary(
        id=str(job.id),
        skill=job.skill,
        module=job.module,
        task=job.task,
        status=job.status,
        error=job.error,
        overall_band=attempt.overall_band if attempt else None,
        stage=job.stage,
        created_at=(job.created_at or datetime.utcnow()).isoformat(),
    )


async def _create_objective(
    *,
    skill: str,
    body: ObjectiveEvaluationCreate,
    user: User,
    db: AsyncSession,
) -> EvaluationSummary:
    try:
        set_id = UUID(body.content_set_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid content_set_id") from exc
    content = await db.get(ContentSet, set_id)
    if content is None or content.review_status != "published" or content.skill != skill:
        raise HTTPException(status_code=404, detail="Published content set not found")
    module = body.module if body.module != "shared" else user.preferred_module
    job = EvaluationJob(
        user_id=user.id,
        skill=skill,
        module=module if module in {"academic", "general"} else "academic",
        task="set",
        stage="queued",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    write_job_payload(
        str(job.id),
        {
            "content_set_id": str(content.id),
            "answers": body.answers,
            "mode": body.mode,
            "mock_session_id": body.mock_session_id,
            "prompt": content.title,
        },
    )
    await enqueue_evaluation(str(job.id))
    return _summary(job)


@router.post("/evaluations/reading", response_model=EvaluationSummary, dependencies=[Depends(limit_evaluations)])
async def create_reading(
    body: ObjectiveEvaluationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationSummary:
    return await _create_objective(skill="reading", body=body, user=user, db=db)


@router.post("/evaluations/listening", response_model=EvaluationSummary, dependencies=[Depends(limit_evaluations)])
async def create_listening(
    body: ObjectiveEvaluationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationSummary:
    return await _create_objective(skill="listening", body=body, user=user, db=db)


@router.post("/evaluations/writing", response_model=EvaluationSummary, dependencies=[Depends(limit_evaluations)])
async def create_writing(
    body: WritingEvaluationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationSummary:
    job = EvaluationJob(user_id=user.id, skill="writing", module=body.module, task=body.task, stage="queued")
    db.add(job)
    if body.study_item_id:
        try:
            item = await db.get(StudyPlanItem, UUID(body.study_item_id))
        except ValueError:
            item = None
        if item and item.user_id == user.id:
            item.status = "in_progress"
    await db.commit()
    await db.refresh(job)
    write_job_payload(
        str(job.id),
        {
            "prompt": body.prompt,
            "essay_text": body.essay,
            "transcript": None,
            "audio_path": None,
            "speaking_mode": None,
            "parent_attempt_id": body.parent_attempt_id,
            "study_item_id": body.study_item_id,
            "bank_item_id": body.bank_item_id,
        },
    )
    await enqueue_evaluation(str(job.id))
    return _summary(job)


@router.post("/evaluations/speaking", response_model=EvaluationSummary, dependencies=[Depends(limit_evaluations)])
async def create_speaking(
    module: str = Form("academic"),
    task: str = Form(...),
    prompt: str = Form(..., min_length=5, max_length=4000),
    transcript: str | None = Form(None, max_length=12000),
    parent_attempt_id: str | None = Form(None),
    bank_item_id: str | None = Form(None),
    audio: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationSummary:
    if module not in {"academic", "general"}:
        raise HTTPException(status_code=400, detail="module must be academic or general")
    if task not in {"part1", "part2", "part3", "full"}:
        raise HTTPException(status_code=400, detail="task must be part1, part2, part3, or full")
    if not transcript and audio is None:
        raise HTTPException(status_code=400, detail="Provide audio or a transcript")

    audio_path = None
    speaking_mode = "text"
    if audio is not None and audio.filename:
        dest = await save_audio_upload(audio)
        audio_path = str(dest)
        speaking_mode = "audio"

    job = EvaluationJob(user_id=user.id, skill="speaking", module=module, task=task, stage="queued")
    db.add(job)
    await db.commit()
    await db.refresh(job)
    write_job_payload(
        str(job.id),
        {
            "prompt": prompt,
            "essay_text": None,
            "transcript": transcript.strip() if transcript else None,
            "audio_path": audio_path,
            "speaking_mode": speaking_mode if not transcript else ("audio" if audio_path else "text"),
            "parent_attempt_id": parent_attempt_id,
            "bank_item_id": bank_item_id,
        },
    )
    await enqueue_evaluation(str(job.id))
    return _summary(job)


@router.get("/evaluations", response_model=list[EvaluationSummary])
async def list_evaluations(
    skill: str | None = None,
    module: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EvaluationSummary]:
    query = (
        select(EvaluationJob)
        .options(selectinload(EvaluationJob.attempt))
        .where(EvaluationJob.user_id == user.id)
        .order_by(EvaluationJob.created_at.desc())
    )
    if skill:
        if skill not in {"writing", "speaking", "reading", "listening"}:
            raise HTTPException(
                status_code=400, detail="skill must be writing, speaking, reading, or listening"
            )
        query = query.where(EvaluationJob.skill == skill)
    if module:
        if module not in {"academic", "general"}:
            raise HTTPException(status_code=400, detail="module must be academic or general")
        query = query.where(EvaluationJob.module == module)
    jobs = (await db.scalars(query.limit(50))).all()
    return [_summary(job, job.attempt) for job in jobs]


@router.get("/evaluations/{job_id}", response_model=EvaluationDetail)
async def get_evaluation(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationDetail:
    job = await db.scalar(
        select(EvaluationJob)
        .options(selectinload(EvaluationJob.attempt))
        .where(EvaluationJob.id == job_id, EvaluationJob.user_id == user.id)
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    attempt = job.attempt
    payload = read_job_payload(str(job.id))
    report = attempt.report if attempt else (job.partial_report or None)
    return EvaluationDetail(
        **_summary(job, attempt).model_dump(),
        prompt=(attempt.prompt if attempt else payload.get("prompt")),
        input_text=(attempt.input_text if attempt else payload.get("essay_text")),
        transcript=(attempt.transcript if attempt else payload.get("transcript")),
        speaking_mode=(attempt.speaking_mode if attempt else payload.get("speaking_mode")),
        attempt_id=str(attempt.id) if attempt else None,
        report=report,
    )


@router.get("/evaluations/{job_id}/events")
async def evaluation_events(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.scalar(
        select(EvaluationJob).where(EvaluationJob.id == job_id, EvaluationJob.user_id == user.id)
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    async def stream():
        import json

        snapshot = {
            "job_id": str(job.id),
            "stage": job.stage or job.status,
            "label": STAGE_LABELS.get(job.stage or job.status, job.stage or job.status),
            "status": job.status,
        }
        yield f"data: {json.dumps(snapshot)}\n\n"
        if job.status in {"completed", "failed"}:
            yield "event: end\ndata: {}\n\n"
            return
        try:
            redis = await get_redis()
            pubsub = redis.pubsub()
            await pubsub.subscribe(channel_for(str(job_id)))
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                yield f"data: {data}\n\n"
                if isinstance(data, str) and ('"stage": "completed"' in data or '"stage": "failed"' in data):
                    yield "event: end\ndata: {}\n\n"
                    break
        except Exception:
            yield "event: end\ndata: {}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/evaluations/{job_id}/revise", dependencies=[Depends(limit_evaluations)])
async def revise_evaluation(
    job_id: UUID,
    body: RevisionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    job = await db.scalar(
        select(EvaluationJob)
        .options(selectinload(EvaluationJob.attempt))
        .where(EvaluationJob.id == job_id, EvaluationJob.user_id == user.id)
    )
    if job is None or job.attempt is None:
        raise HTTPException(status_code=404, detail="Completed evaluation not found")
    attempt = job.attempt
    response = attempt.input_text or attempt.transcript or ""
    report = dict(attempt.report or {})
    scores = report.get("scores") or {}
    criteria = scores.get("criteria") or []
    weakest = min(criteria, key=lambda row: row.get("band", 9), default={"criterion": "coherence", "band": 6.0})
    span = (body.span or "").strip()
    if not span:
        writing = report.get("writing") or {}
        speaking = report.get("speaking") or {}
        for block in (writing, speaking):
            for key, value in block.items():
                if isinstance(value, dict):
                    evidence = value.get("evidence") or []
                    if evidence and evidence[0].get("quote"):
                        span = evidence[0]["quote"]
                        break
            if span:
                break
    if not span:
        span = " ".join(response.split()[:40])
    if not span:
        raise HTTPException(status_code=400, detail="Nothing to rewrite")
    target = min(9.0, float(weakest.get("band") or 6) + 0.5)
    result = await run_revision(
        job_id=str(job.id),
        skill=job.skill,
        prompt=attempt.prompt,
        response=response,
        span=span,
        weakest=str(weakest.get("criterion") or "coherence"),
        target_band=target,
    )
    payload = result.model_dump()
    revisions = list(report.get("revisions") or [])
    revisions.append(payload)
    report["revisions"] = revisions
    attempt.report = report
    flag_modified(attempt, "report")
    job.partial_report = report
    await db.commit()
    return payload


@router.post("/speaking/transcribe", dependencies=[Depends(limit_evaluations)])
async def transcribe_only(
    audio: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    dest = await save_audio_upload(audio)
    try:
        text, provider = await transcribe_audio(dest)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Transcription failed") from exc
    return {"transcript": text, "provider": provider}
