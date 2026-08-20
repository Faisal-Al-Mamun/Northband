from arq.connections import RedisSettings

from app.config import settings


async def run_evaluation(ctx: dict, job_id: str) -> None:
    from app.agents.graph import run_evaluation_job

    await run_evaluation_job(job_id)


class WorkerSettings:
    functions = [run_evaluation]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 4
    job_timeout = 360
