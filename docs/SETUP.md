# Setup

Northband is a small monorepo: FastAPI + two LangGraphs (`apps/api`), Next.js studio (`apps/web`), PostgreSQL, and Redis. The same Compose file runs on macOS, Windows (Docker Desktop / WSL 2), and Ubuntu.

**Run / OS notes / VPS:** [DEPLOY.md](DEPLOY.md) — start there if you want the stack up.

## Requirements

**Happy path:** Docker Desktop (Mac/Windows) or Docker Engine + Compose plugin (Ubuntu).

**Host mode** (API/web on the machine, Compose only for Postgres/Redis):

- Python 3.12 (recommended; 3.14 may lack wheels)
- Node 20+ (Compose web image is Node 22)
- ffmpeg on the host if you run speaking STT outside Docker
- No GPU

## 1. Environment

```bash
cp .env.example .env
```

Windows: `Copy-Item .env.example .env`. Keep LF line endings (see `.gitattributes`).

Compose loads `.env` into the API and worker, then **overrides** `DATABASE_URL` / `REDIS_URL` to the `postgres` and `redis` service names. The web service only needs `NEXT_PUBLIC_API_URL` (Compose sets `http://localhost:8000` so the browser talks to the published API port).

In host mode, leave the localhost URLs from `.env.example`.

### Required for a real model

Set at least one LLM key and matching default provider:

| Goal | Settings |
|------|----------|
| OpenRouter | `OPENROUTER_API_KEY` and `LLM_DEFAULT_PROVIDER=openrouter` |
| Gemini | `GEMINI_API_KEY` and `LLM_DEFAULT_PROVIDER=gemini` |
| OpenAI or compatible | `OPENAI_COMPAT_API_KEY`, `OPENAI_COMPAT_BASE_URL`, `LLM_DEFAULT_PROVIDER=openai_compat` |

If no key is set, agents fall back to heuristic mock JSON so the UI still works.

For speaking **audio**, local **faster-whisper** is the default (`STT_PROVIDER=auto`, `WHISPER_MODEL=base`, CPU int8). The API image includes ffmpeg. On the host: `brew install ffmpeg` (macOS), `sudo apt-get install -y ffmpeg` (Ubuntu), `winget install Gyan.FFmpeg` (Windows). The first transcription downloads a small CPU model into `hfcache` (Compose) or `~/.cache/huggingface` (host). Cloud Whisper or Gemini is used only if local STT fails and a key is set. You can still paste a transcript.

### All settings

| Variable | Default | Meaning |
|----------|---------|---------|
| `DATABASE_URL` | asyncpg localhost | SQLAlchemy async URL |
| `DATABASE_URL_SYNC` | psycopg localhost | Alembic / sync URL |
| `REDIS_URL` | `redis://localhost:6379/0` | ARQ queue and job events |
| `JWT_SECRET` | example string | **Change before production** |
| `JWT_EXPIRE_MINUTES` | `10080` (7 days) | Access token lifetime |
| `ENVIRONMENT` | `development` | `production` hides `/docs` and disables in-process job fallback |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated browser origins |
| `UPLOAD_DIR` | `./uploads` | Job payloads and audio (`/app/uploads` in Compose) |
| `LLM_DEFAULT_PROVIDER` | `openrouter` | `openrouter`, `gemini`, `openai_compat`, `openai`, `mock` |
| `LLM_DEFAULT_MODEL` | `openai/gpt-4o-mini` | Used unless an `AGENT_*` override is set |
| `LLM_CHEAP_PROVIDER` / `LLM_CHEAP_MODEL` | empty | Optional cheaper host for grammar, performance, explain |
| `OPENROUTER_API_KEY` / `OPENROUTER_BASE_URL` | OpenRouter v1 | |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | `gemini-2.0-flash` | Chat + optional STT |
| `OPENAI_COMPAT_API_KEY` / `BASE_URL` / `MODEL` | OpenAI v1 | Any OpenAI-compatible host |
| `STT_PROVIDER` | `auto` | `auto` (faster-whisper, then cloud), `faster_whisper`, `openai_compat`, `gemini` |
| `WHISPER_MODEL` | `base` | Local size (`tiny`/`base`/`small`) or cloud `whisper-1` |
| `STT_DEVICE` | `cpu` | faster-whisper device (no GPU required) |
| `STT_COMPUTE_TYPE` | `int8` | CPU-efficient quantisation |
| `STT_WARMUP_ON_START` | `false` | Load the Whisper model at API boot |
| `AGENT_WRITING` … `AGENT_REVISION` / `AGENT_EXPLAIN` / `AGENT_COACH` / `AGENT_BANK` | empty | Optional `provider:model` per agent |
| `EXPLAIN_LLM_ENABLED` | `true` | Cached batch explanations for leftover Reading/Listening misses after the coach loop |
| `SCORING_LLM_ENABLED` | `false` | Notes-only scoring LLM (off by default); cannot change bands |
| `LLM_TIMEOUT_SECONDS` | `45` | Per-call timeout inside the graph |
| `TTS_ENGINE` | `auto` | Pocket TTS, else macOS `say` |
| `TTS_WARMUP_ON_START` | `true` | Warm listening TTS at API boot |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Browser API base (baked in at Next build) |

Per-agent override example:

```bash
AGENT_WRITING=openrouter:openai/gpt-4o-mini
AGENT_GRAMMAR=gemini:gemini-2.0-flash
AGENT_COACH=openrouter:openai/gpt-4o-mini
AGENT_BANK=openrouter:openai/gpt-4o-mini
```

## 2. Run with Docker

From the repo root (same commands on Mac, Windows PowerShell, and Ubuntu):

```bash
docker compose up --build
```

Helpers: `./scripts/dev.sh` or `.\scripts\dev.ps1` (copy `.env` if missing, print URLs, start Compose).

| Service | URL |
|---------|-----|
| Studio | http://localhost:3000 |
| API OpenAPI | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Ready (Postgres) | http://localhost:8000/ready |
| Postgres | localhost:5432 (`northband` / `northband` / db `northband`) |
| Redis | localhost:6379 |

The first API build downloads torch/faster-whisper (several minutes). Later builds stay smaller because `apps/api/.dockerignore` skips `.venv`. Speech models persist in the `hfcache` volume.

The web container runs `npm install` on start so new frontend packages land in the Docker `node_modules` volume. If you still see `Can't resolve 'recharts'` (or another new dependency), recreate that volume:

```bash
docker compose rm -sfv web && docker compose up --build web
```

Seed after the API is healthy:

```bash
./scripts/seed.sh
# or: docker compose exec api python -m app.seed
#     docker compose exec api python -m app.seed_content
```

`seed` creates the demo user. `seed_content` loads Reading/Listening sets. Startup also tries `seed_content`; re-running is safe.

Login: `demo@northband.app` / `demo12345` (display name Amina Rahman, target 7.0 Academic). Re-running user seed is a no-op if the email exists.

API and worker mount `./apps/api` for live reload (polling enabled for Docker Desktop). Uploads persist in the `uploads` named volume; Postgres in `pgdata`; HuggingFace weights in `hfcache`.

## 3. Run locally (host mode)

Start only the databases:

```bash
docker compose up postgres redis -d
```

OS-specific Python / ffmpeg / Node commands: [DEPLOY.md](DEPLOY.md#host-mode-compose-only-for-postgresredis).

API (uses `.env` via pydantic-settings; it also looks at `../../.env` from `apps/api`):

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

`requirements.txt` includes local STT/TTS. CI and a slimmer venv can use `requirements-base.txt` only.

Worker (required for queued evaluations unless you rely on the development in-process fallback):

```bash
cd apps/api
source .venv/bin/activate
arq app.worker.WorkerSettings
```

Frontend:

```bash
cd apps/web
npm install
npm run dev
```

Optional migrations. Tables are also created on API startup. Alembic (`001_initial`, `002_coach_loop`, `003_content_bank`, `004_prompt_bank`) is useful when an existing database needs coach-loop columns, the item-bank / mock tables, or `prompt_items` / `attempts.bank_item_id`:

```bash
cd apps/api
source .venv/bin/activate
alembic upgrade head
python -m app.seed
```

Local `DATABASE_URL` / `REDIS_URL` should point at `localhost`, not the Compose service names.

## Tests

From `apps/api` with the venv active:

```bash
cd apps/api
pytest
python -m app.eval.offline
```

`pytest.ini` sets `pythonpath = .` and `testpaths = tests`. No live LLM calls are required. CI (`.github/workflows/api-tests.yml`) installs `requirements-base.txt` and runs the same suite on `ubuntu-latest`.

Coverage:

| File | What it checks |
|------|----------------|
| `test_graph.py` | Writing/Speaking LangGraph compiles |
| `test_objective_graph.py` | Reading/Listening graph compiles; coach tools + mock coach contract |
| `test_bands.py` | Half-band rounding |
| `test_schemas.py` | Mock agent JSON matches Pydantic |
| `test_agentic_loop.py` | Quote verify, grammar caps, tools, gold essays |
| `test_planner.py` | Cost-aware skip rules, analysis cache, cheap-model routing |
| `test_offline_eval.py` | Schema validity + quote-hit-rate on the gold set (no keys) |
| `test_exam_rules.py` | Under-length / overview / short-speaking ceilings |
| `test_memory.py` | Coach-profile EWMA |
| `test_objective.py` | Key marking, raw→band, content validators |
| `test_assign.py` | Exam packs before drills |
| `test_prompt_bank.py` | Curated bank coverage, per-user shuffle, generated-paper contract |
| `test_stt.py` | Local vs cloud Whisper model names |
| `test_tts_script.py` | Listening script parse / voice map |

Gold essays and speaking transcripts: `apps/api/app/eval/gold_set.py`. Objective cases: `apps/api/app/eval/gold_objective.py`. Offline eval: `python -m app.eval.offline`. Labels are practice estimates, not official scores.

Python 3.12 is what the API Dockerfile uses.

## Production

Use [DEPLOY.md](DEPLOY.md#production-ish-compose-on-a-vps) (`docker-compose.prod.yml`). Short version:

- Set a long random `JWT_SECRET`.
- Set `ENVIRONMENT=production` so OpenAPI is disabled and a Redis outage **fails** enqueue instead of running the graph inside the API process.
- Point `CORS_ORIGINS` and `NEXT_PUBLIC_API_URL` at the real public URLs; rebuild the web image after changing the latter.
- Run the dedicated worker; do not depend on the development fallback.
- Keep `/ready` behind your orchestrator health check, not only `/health`.

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| Jobs stay `queued` | Worker not running, or Redis URL mismatch. In development the API can run the graph itself if Redis enqueue fails. |
| `Can't resolve 'recharts'` in Compose | Recreate the web container/volume (see above). |
| Speaking audio fails | Install ffmpeg on the host (Compose image already has it); wait for the first faster-whisper model download; or paste a transcript. File must be ≤ 15 MB. Windows: Chrome/Edge + microphone permission. |
| Empty / mock-looking reports | No LLM key — mock provider is intentional. |
| CORS errors | `CORS_ORIGINS` must include the exact studio origin (scheme + host + port). |
| Demo login 409 / already exists | Seed already ran; use `demo@northband.app` / `demo12345`. |
| Python 3.14 install failures | Use 3.12 as in the API Dockerfile. |
| Docker `permission denied` (Ubuntu) | `sudo usermod -aG docker $USER` and re-login. |
| Windows hot reload misses edits | Compose already polls; prefer WSL 2 clone path, or host mode. |
| `.env` values look corrupted on Windows | Convert the file to UTF-8 LF. |
| First `docker compose up --build` seems stuck | API image is installing torch. Wait; later starts reuse the image and `hfcache`. |
