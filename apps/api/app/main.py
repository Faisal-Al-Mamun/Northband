from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db.base import Base
from app.db.schema_patch import ensure_optional_columns
from app.db.session import engine
from app.routers import auth, content, evaluations, mocks, progress
from app.seed import seed as seed_demo_user
from app.seed_content import seed_content

logger = logging.getLogger("northband")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.jwt_secret == "change-me-to-a-long-random-string":
        logger.warning("JWT_SECRET is still the default value. Set a long random secret before production.")
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_optional_columns()
    try:
        await seed_content()
    except Exception:
        logger.exception("Content seed skipped or failed")
    try:
        await seed_demo_user()
    except Exception:
        logger.exception("Demo user seed skipped or failed")
    if settings.tts_warmup_on_start:
        from app.services.listening_audio import warmup_listening_audio

        asyncio.create_task(warmup_listening_audio())
    if settings.stt_warmup_on_start:
        from app.services.stt import warmup_stt

        asyncio.create_task(asyncio.to_thread(warmup_stt))
    yield
    await engine.dispose()


app = FastAPI(
    title="Northband IELTS API",
    description="Multi-agent IELTS evaluation, scoring, and study recommendations.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not request.url.path.startswith("/content/audio/"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(auth.router)
app.include_router(evaluations.router)
app.include_router(progress.router)
app.include_router(content.router)
app.include_router(mocks.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    from app.db.session import SessionLocal

    async with SessionLocal() as db:
        await db.execute(text("SELECT 1"))
    return {"status": "ready"}
