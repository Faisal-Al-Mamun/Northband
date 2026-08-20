from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.security import get_current_user
from app.config import settings
from app.content.assign import next_content_set, next_prompt, pack_kind
from app.db.models import ContentSet, Question, User
from app.db.session import get_db
from app.schemas.content import (
    AudioOut,
    ContentSetDetail,
    ContentSetSummary,
    NextPaperOut,
    NextSetOut,
    PassageOut,
    QuestionOut,
)
from app.services.listening_audio import ensure_filename_audio, prepare_set_audio
from app.services.tts import wav_is_playable

router = APIRouter(prefix="/content", tags=["content"])


def _audio_url(uri: str) -> str:
    return f"/content/audio/{Path(uri).name}" if uri else ""


@router.get("/sets", response_model=list[ContentSetSummary])
async def list_sets(
    skill: str | None = None,
    module: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ContentSetSummary]:
    query = (
        select(ContentSet, func.count(Question.id))
        .outerjoin(Question, Question.content_set_id == ContentSet.id)
        .where(ContentSet.review_status == "published")
        .group_by(ContentSet.id)
        .order_by(func.count(Question.id).desc(), ContentSet.title)
    )
    if skill:
        query = query.where(ContentSet.skill == skill)
    if module:
        # Listening is shared for Academic and GT
        if skill == "listening" or module == "shared":
            query = query.where(ContentSet.module.in_(["shared", module]))
        else:
            query = query.where(ContentSet.module == module)
    rows = (await db.execute(query)).all()
    return [
        ContentSetSummary(
            id=str(item.id),
            skill=item.skill,
            module=item.module,
            slug=item.slug,
            title=item.title,
            difficulty=item.difficulty,
            time_limit_sec=item.time_limit_sec,
            question_count=count or 0,
            review_status=item.review_status,
            kind=pack_kind(item, count or 0),
        )
        for item, count in rows
    ]


@router.get("/next-prompt", response_model=NextPaperOut)
async def get_next_prompt(
    skill: str,
    task: str,
    module: str | None = None,
    exclude_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NextPaperOut:
    if skill not in {"writing", "speaking"}:
        raise HTTPException(status_code=400, detail="skill must be writing or speaking")
    if skill == "writing" and task not in {"task1", "task2"}:
        raise HTTPException(status_code=400, detail="task must be task1 or task2")
    if skill == "speaking" and task not in {"part1", "part2", "part3", "full"}:
        raise HTTPException(status_code=400, detail="task must be part1, part2, part3, or full")
    chosen_module = module if module in {"academic", "general"} else user.preferred_module
    data = await next_prompt(
        db,
        user,
        skill=skill,
        module=chosen_module,
        task=task,
        exclude_id=exclude_id,
    )
    return NextPaperOut(**data)


@router.get("/next-set", response_model=NextSetOut)
async def get_next_set(
    skill: str,
    module: str | None = None,
    exclude_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NextSetOut:
    if skill not in {"reading", "listening"}:
        raise HTTPException(status_code=400, detail="skill must be reading or listening")
    chosen_module = module if module in {"academic", "general", "shared"} else user.preferred_module
    data = await next_content_set(
        db,
        user,
        skill=skill,
        module=None if skill == "listening" else chosen_module,
        exclude_id=exclude_id,
    )
    return NextSetOut(**data)


@router.get("/sets/{set_id}", response_model=ContentSetDetail)
async def get_set(
    set_id: UUID,
    include_transcript: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentSetDetail:
    item = await db.scalar(
        select(ContentSet)
        .options(
            selectinload(ContentSet.passages),
            selectinload(ContentSet.audio_assets),
            selectinload(ContentSet.questions),
        )
        .where(ContentSet.id == set_id, ContentSet.review_status == "published")
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Content set not found")
    return ContentSetDetail(
        id=str(item.id),
        skill=item.skill,
        module=item.module,
        slug=item.slug,
        title=item.title,
        difficulty=item.difficulty,
        time_limit_sec=item.time_limit_sec,
        question_count=len(item.questions),
        review_status=item.review_status,
        passages=[
            PassageOut(
                id=str(p.id),
                order_index=p.order_index,
                title=p.title,
                body=p.body,
            )
            for p in sorted(item.passages, key=lambda x: x.order_index)
        ],
        audio_assets=[
            AudioOut(
                id=str(a.id),
                order_index=a.order_index,
                section_label=a.section_label,
                url=_audio_url(a.uri),
                duration_sec=a.duration_sec,
                accent=a.accent,
                transcript=a.transcript if include_transcript else None,
            )
            for a in sorted(item.audio_assets, key=lambda x: x.order_index)
        ],
        questions=[
            QuestionOut(
                id=str(q.id),
                number=q.number,
                qtype=q.qtype,
                stem=q.stem,
                options=q.options or {},
                skill_tags=list(q.skill_tags or []),
                marks=q.marks,
                word_limit=q.word_limit,
                passage_id=str(q.passage_id) if q.passage_id else None,
                audio_asset_id=str(q.audio_asset_id) if q.audio_asset_id else None,
            )
            for q in sorted(item.questions, key=lambda x: x.order_index)
        ],
    )


@router.post("/sets/{set_id}/prepare-audio")
async def prepare_audio(
    set_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = await db.get(ContentSet, set_id)
    if item is None or item.review_status != "published":
        raise HTTPException(status_code=404, detail="Content set not found")
    if item.skill != "listening":
        return {"assets": []}
    try:
        return await prepare_set_audio(set_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not prepare audio: {exc}") from exc


@router.get("/audio/{filename}")
async def get_audio(filename: str, user: User = Depends(get_current_user)):
    safe = Path(filename).name
    path = settings.upload_path / "content" / "audio" / safe
    if not wav_is_playable(path, min_seconds=8.0):
        try:
            path = await ensure_filename_audio(safe)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Audio not found")
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Audio is still being prepared: {exc}") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path, media_type="audio/wav", filename=safe)
