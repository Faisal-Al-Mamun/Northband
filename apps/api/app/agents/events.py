from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from sqlalchemy.orm.attributes import flag_modified

from app.config import settings
from app.db.models import EvaluationJob
from app.db.session import SessionLocal

_redis: Redis | None = None

STAGE_LABELS = {
    "queued": "In the queue",
    "ingest": "Loading your attempt",
    "tools": "Checking length and task coverage",
    "plan": "Choosing which agents to run",
    "transcribe": "Transcribing audio",
    "grading": "Marking against the answer key",
    "analyzing": "Reading language and criteria",
    "verify": "Checking evidence quotes",
    "scoring": "Finalising bands",
    "coaching": "Building your study list",
    "persisting": "Saving the report",
    "completed": "Ready",
    "failed": "Failed",
}


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def channel_for(job_id: str) -> str:
    return f"northband:job:{job_id}"


async def publish_job_event(job_id: str, stage: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "job_id": job_id,
        "stage": stage,
        "label": STAGE_LABELS.get(stage, stage),
        "ts": datetime.now(timezone.utc).isoformat(),
        **(extra or {}),
    }
    try:
        redis = await get_redis()
        raw = json.dumps(payload, ensure_ascii=False)
        await redis.publish(channel_for(job_id), raw)
        await redis.setex(f"northband:jobstage:{job_id}", 3600, raw)
    except Exception:
        pass
    return payload


async def patch_job_progress(
    job_id: str,
    *,
    stage: str,
    partial: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    async with SessionLocal() as db:
        job = await db.get(EvaluationJob, UUID(job_id))
        if job is None:
            return
        job.stage = stage
        if partial is not None:
            current = dict(job.partial_report or {})
            current.update(partial)
            current["stage"] = stage
            job.partial_report = current
            flag_modified(job, "partial_report")
        await db.commit()
    await publish_job_event(job_id, stage, extra)
