from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import settings

_pool: ArqRedis | None = None


async def get_queue() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


async def enqueue_evaluation(job_id: str) -> None:
    try:
        queue = await get_queue()
        await queue.enqueue_job("run_evaluation", job_id)
    except Exception:
        if settings.is_production:
            raise
        import asyncio

        from app.agents.graph import run_evaluation_job

        asyncio.create_task(run_evaluation_job(job_id))
