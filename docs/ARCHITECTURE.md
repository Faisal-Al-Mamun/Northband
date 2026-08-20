# Architecture

Northband is a Next.js studio and a FastAPI service. Writing and Speaking evaluations run as a compiled LangGraph job. Reading and Listening are marked from keys on a second LangGraph, then a tool-using coach explains misses. PostgreSQL stores users, jobs, attempts, criterion scores, study-plan items, coach profiles, LLM call logs, the item bank, prompt bank, and mock sessions. Redis (ARQ) queues long-running agent work and publishes job-stage events. If Redis is down in development, the API starts the graph in-process. Production does not use that fallback.

Band scores are **AI estimates for practice**. They are not official IELTS results. Every report includes that disclaimer. Short Reading/Listening drills show accuracy only and are not converted to a paper band.

## System diagram

```
Browser (Next.js :3000)
    │  JWT in Authorization
    ▼
FastAPI (:8000) ── PostgreSQL
    │ enqueue job + write UPLOAD_DIR/{job_id}.json
    ▼
ARQ worker (Redis)
    │ skill = writing|speaking → evaluation_graph
    │ skill = reading|listening → objective_graph
    │ stage + partial_report on the job row
    │ publish northband:job:{id}
    ▼
UI polls GET /evaluations/{id}
   (optional SSE GET /evaluations/{id}/events)
```

Compose services: `postgres`, `redis`, `api` (uvicorn reload), `worker` (`arq app.worker.WorkerSettings`, max 4 jobs, 360s timeout), `web` (`npm run dev`). API and worker share the `uploads` volume. HuggingFace weights persist in `hfcache`.

## Repository map

Layout of the monorepo is in the root [README.md](../README.md).

| Path | Role |
|------|------|
| `apps/api/app/main.py` | FastAPI app, CORS, security headers, `/health`, `/ready`; startup seed + TTS/STT warmup |
| `apps/api/app/routers/` | `auth`, `evaluations`, `progress`, `content`, `mocks` |
| `apps/api/app/queue.py` | ARQ enqueue; in-process fallback in development |
| `apps/api/app/worker.py` | ARQ: `run_evaluation`, max 4 jobs, 360s timeout |
| `apps/api/app/agents/graph.py` | Writing/Speaking LangGraph; routes reading/listening to `objective_flow` |
| `apps/api/app/agents/objective_graph.py` | Reading/Listening LangGraph: keys → coach tools → synthesize |
| `apps/api/app/agents/objective_flow.py` | Load questions, cached explain batch, persist objective result |
| `apps/api/app/agents/coach_tools.py` | `list_misses`, `inspect_item`, `quote_context` |
| `apps/api/app/agents/planner.py` | Cost-aware skip rules after tools |
| `apps/api/app/agents/analysis_cache.py` | Hash cache for identical writing/speaking analyses |
| `apps/api/app/agents/exam_rules.py` | Examiner-style band ceilings + first-impression notes |
| `apps/api/app/agents/prompts.py` | System/user prompts + official-style rubric text + `COACH_SYSTEM` |
| `apps/api/app/agents/rubrics.py` | Criterion descriptor blocks injected into prompts |
| `apps/api/app/agents/tools.py` | Deterministic word count, coverage, fillers, linkers |
| `apps/api/app/agents/verify.py` | Drop invented quotes; cap inflated grammar bands |
| `apps/api/app/agents/memory.py` | Coach profile EWMA and weak-pattern list |
| `apps/api/app/agents/events.py` | Redis pub/sub + `partial_report` patches |
| `apps/api/app/content/prompt_bank.py` | Curated writing/speaking papers |
| `apps/api/app/content/assign.py` | Next unused paper/set; exam-before-drill; per-user shuffle |
| `apps/api/app/content/generate.py` | `AGENT_BANK` original writing/speaking papers |
| `apps/api/app/content/validators.py` | Pre-publish item-bank checks |
| `apps/api/app/llm/router.py` | Provider routing, JSON schema, retries, call logs |
| `apps/api/app/llm/mock_responses.py` | Heuristic JSON when keys are missing |
| `apps/api/app/scoring/bands.py` | Clamp 0–9, round to 0.5, mean of four criteria, Writing T1×⅓+T2×⅔ |
| `apps/api/app/scoring/objective.py` | Key-based Reading/Listening marking |
| `apps/api/app/scoring/raw_to_band.py` | Raw/40 → band tables, `is_full_paper`, four-skill overall |
| `apps/api/app/services/stt.py` | faster-whisper first, then cloud Whisper / Gemini |
| `apps/api/app/services/tts.py` | Pocket TTS (else macOS `say`) for listening audio |
| `apps/api/app/services/listening_audio.py` | Prepare / serve section WAV files |
| `apps/api/app/db/models.py` | SQLAlchemy models |
| `apps/api/app/eval/` | Gold essays, speaking transcripts, objective cases, offline eval |
| `apps/api/app/seed.py` / `seed_content.py` | Demo user; curated Reading/Listening + prompt bank |
| `apps/api/tests/` | Graph, bands, verify, exam rules, memory, schemas, objective keys, assign, coach tools |
| `apps/web/src/app/` | Marketing, auth, studio (4 skills + mock), results |
| `apps/web/src/lib/types.ts` | Report shape mirrored from API schemas |
| `packages/shared/README.md` | How Pydantic and TypeScript stay aligned |

Tables are created on API startup (`Base.metadata.create_all`) plus `ensure_optional_columns`. Alembic (`001_initial`, `002_coach_loop`, `003_content_bank`, `004_prompt_bank`) is optional for existing databases. Startup also seeds curated Reading/Listening sets and the demo user (`seed_content`, `seed`).

## Request flow

1. The student registers or signs in (`POST /auth/register` or `/auth/login`) and receives a JWT (HS256, default 7 days). The web app stores it as `nb_token` in `localStorage`.
2. Practice paths:
   - Writing (`POST /evaluations/writing`) or speaking (`POST /evaluations/speaking`) — rubric LangGraph. Optional `bank_item_id` records which prompt-bank paper was sat. Speaking `task` is `part1` | `part2` | `part3` | `full`.
   - Reading (`POST /evaluations/reading`) or listening (`POST /evaluations/listening`) — `objective_graph`: deterministic keys, then coach tools + optional explain.
   - Full mock (`POST /mocks/sessions`) sequences Listening → Reading → Writing Task 1 → Writing Task 2 → Speaking. Writing overall = Task 1×⅓ + Task 2×⅔.
3. The API writes an `evaluation_jobs` row (`status=queued`) and a JSON payload under `UPLOAD_DIR/{job_id}.json`.
4. `enqueue_evaluation` pushes `run_evaluation` onto ARQ. On Redis failure in development only, `asyncio.create_task(run_evaluation_job)` runs in the API process.
5. For reading/listening, `run_objective_evaluation` grades against Postgres keys, maps raw→band only for full papers (`max_marks >= 35`), runs the coach loop, persists attempt + study drills.
6. The UI polls `GET /evaluations/{id}` until `completed` or `failed`. Objective scorecards render from `partial_report` as soon as marks exist.

Job statuses: `queued` → `running` → `completed` | `failed`.

How the multi-agent graphs decide bands, evidence, and study actions is documented in [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md).

## Graphs

Writing / Speaking (`build_graph()` in `graph.py`):

```
START → ingest
  speaking → transcribe
  → tools → plan → analyze_writing|analyze_speaking → verify → scoring → coach → persist → END
```

Reading / Listening (`build_objective_graph()` in `objective_graph.py`):

```
START → ingest → grade → coach_loop → synthesize → persist → END
```

Conditional edges skip transcribe for writing and jump to `persist` on error.

### Writing / Speaking nodes

| Node | What it does |
|------|----------------|
| `ingest` | Marks the job running. Loads last 12 attempts (criterion history), the user's `coach_profile` and `target_band`, and the parent attempt if `parent_attempt_id` is set. |
| `transcribe` | Speaking only. Uses a provided transcript, or local faster-whisper (then cloud) on `audio_path`. Records duration and words-per-minute. |
| `tools` | Deterministic facts: word count, expected minimum (150 Task 1 / 250 Task 2), under-length, linkers, Task 1 overview + bullet coverage, speaking fillers. Speaking text-only sets `pronunciation_is_proxy`. |
| `plan` | Deterministic router (`planner.py`). Skips grammar on tiny answers, skips performance with thin history, reuses cached specialist JSON for identical input. Writes `agent_trace`. |
| `analyze_writing` / `analyze_speaking` | Specialist agent and grammar agent in parallel (`asyncio.gather`) unless the plan skipped or cached them. Grammar issue spans that are not in the source text are dropped immediately. |
| `verify` | Drops evidence quotes that are not in the response. Reconciles the grammar criterion with the grammar-agent issue count (caps: 12+ issues → 5.0, 8+ → 5.5, 5+ → 6.0, 3+ → 6.5). |
| `scoring` | Half-band math, then `exam_rules.apply_exam_ceilings`. Optional scoring LLM (`SCORING_LLM_ENABLED`) may only write confidence notes — it cannot change bands. Builds `delta` vs parent. Stores `examiner_first_impression`. |
| `coach` | Feedback and performance agents in parallel. Timeouts/failures use deterministic fallbacks; they do not fail the job. |
| `persist` | Writes `attempts` + `criterion_scores` + `study_plan_items`, updates `users.coach_profile`, marks linked study item `done`, sets job `completed`. On graph error, sets `failed`. |

Worker timeout is 360 seconds (`app/worker.py`). Each LLM call is bounded by `LLM_TIMEOUT_SECONDS` (default 45).

## Scoring

Specialist agents propose criterion bands with evidence. `app/scoring/bands.py`:

- clamp to 0–9
- round to the nearest 0.5 (IELTS half-up: .25 → .5, .75 → next whole)
- overall = mean of the four official-style criteria, then half-band again
- mock Writing overall (Task 1 + Task 2): `combine_writing_bands` = (T1 + 2×T2) / 3

**Writing:** Task Response / Task Achievement, Coherence and Cohesion, Lexical Resource, Grammatical Range and Accuracy.

**Speaking:** Fluency and Coherence, Lexical Resource, Grammatical Range and Accuracy, Pronunciation.

Confidence starts around 0.78 and is lowered when the response is under length, quotes were dropped, speaking was text-only, or an exam ceiling applied. Text-only speaking flags pronunciation as a proxy, not an acoustic score.

`exam_rules.apply_exam_ceilings` then hard-caps Task/Fluency when:

- writing is under length (Task typically capped at 6.0)
- Academic Task 1 has no overview, or a GT letter covers fewer than half the bullets / lacks purpose-tone markers
- speaking WPM is very low (< 70)
- Part 2 is under 20s (cap 4.0) or under 45s (cap 5.5)
- a full interview is under 3 minutes (cap 4.0) or under 6 minutes (cap 5.5)
- Part 2 / full covers fewer than half the cue-card points

The scoring LLM is **off by default**. When on, it only overwrites `scoring_notes` and `confidence`.

**Reading / Listening:** `scoring/objective.py` matches keys. `raw_to_band` converts marks to a practice band only when `max_marks >= 35`. Drills store `objective.is_drill` and a null overall band. Progress `/summary` ignores drills.

Four-skill overall (`overall_ielts_band`) is the half-banded mean of whatever skills have a latest paper band. With fewer than two skills it stays null and lists `missing_skills`.

## Closed loop

- Feedback actions include `drill_prompt` and `drill_task`. Persist writes them as `study_plan_items`. The studio opens `/app/writing` or `/app/speaking` with `?prompt=&task=&item=`. Submitting with `study_item_id` marks the item done.
- `POST /evaluations/{id}/revise` rewrites the weakest span (or a chosen span) about +0.5 band and appends to `report.revisions`.
- Re-sitting with `parent_attempt_id` stores `report.delta` (overall and per-criterion).

Coach profile (`users.coach_profile` JSONB):

- `weak_patterns` — grammar patterns (or objective skill tags), newest first, cap 12
- `last_next_focus` — last performance-agent focus (avoid repeating verbatim)
- `criterion_ewma` — exponential moving average, α = 0.4
- `attempt_count`, `updated_at`

`profile_for_prompt` sends a slim copy into writing, speaking, feedback, and performance prompts.

## Content assignment

`content/assign.py` picks the next unused paper for a user. Order is shuffled per account so two students do not walk the bank in the same sequence.

- Writing/Speaking: curated `prompt_items`. After at least one completed sit, a live LLM may inject an original paper (`AGENT_BANK`, `owner_user_id` set). Optional `exclude_id` skips the current paper.
- Reading/Listening: published `content_sets`. Exam packs (≈40 questions / `meta.kind=exam`) are offered before drills. Keys are never generated.
- Mocks: `next_mock_blueprint` if `POST /mocks/sessions` omits `blueprint_id`.

## Data model

| Table | Purpose |
|-------|---------|
| `users` | Email (unique), bcrypt hash, display name, `target_band`, `preferred_module` (`academic` \| `general`), `coach_profile` |
| `evaluation_jobs` | Skill, module, task, `status`, `stage`, `partial_report`, `error` |
| `attempts` | Prompt, essay/transcript, audio path, `speaking_mode`, `overall_band`, `parent_attempt_id`, `bank_item_id`, full JSONB `report` |
| `criterion_scores` | Normalized criterion + band + rationale (for history and charts) |
| `study_plan_items` | Title, detail, `skill_focus`, `drill_prompt` / `drill_task` / `drill_skill`, `status` (`pending` \| `in_progress` \| `done`) |
| `llm_call_logs` | Agent, provider, model, latency, tokens, success/error |
| `content_sets` | Reading/Listening item bank (skill, module, slug, `review_status`, `meta.kind` exam/drill) |
| `passages` | Reading texts on a set |
| `audio_assets` | Listening section audio + transcript (unlock after submit) |
| `questions` | Stem, type, options, marks, word limit |
| `answer_keys` | Canonical + acceptable variants (never shown to the LLM for marking) |
| `explanation_cache` | Wrong-item explain payloads keyed by question + key version + wrong answer |
| `prompt_items` | Writing/Speaking papers (`source` curated \| generated, optional `owner_user_id`) |
| `mock_blueprints` | Full-mock sequence: listening/reading set ids + writing/speaking prompts |
| `mock_sessions` | Per-user run: current skill, job ids (including `writing_task1`), skill bands, overall |

Users own jobs, attempts, study-plan items, and mock sessions. List/get endpoints always filter by `user_id`.

## LLM routing

`app/llm/router.py` resolves `provider:model` per agent from `AGENT_*` env vars or `LLM_DEFAULT_*`. HTTP clients are reused. JSON schema is requested from the provider and echoed in the system prompt. Invalid JSON is retried. Each call is logged to `llm_call_logs`.

Supported providers:

- `openrouter`
- `gemini`
- `openai_compat` / `openai`
- `mock` (automatic when keys are missing — heuristic JSON so the UI still works)

Temperature is 0.2. Agents never receive free-form chat; output is validated Pydantic.

`GET /progress/llm-usage` groups this user’s call logs by agent (counts and tokens).

## Speech

**Speaking STT** (`app/services/stt.py`). Default `STT_PROVIDER=auto`: local **faster-whisper** (CPU int8, `WHISPER_MODEL=base`) first. ffmpeg converts WebM/Opus to 16 kHz mono WAV. Cloud Whisper (`OPENAI_COMPAT_*`) or Gemini file upload is fallback only. Without STT, students can paste a transcript.

Uploads: `app/security/uploads.py` — suffixes `.webm .wav .mp3 .m4a .ogg`, max 15 MB, stored as `{uuid}{suffix}` under `UPLOAD_DIR`.

**Listening TTS** (`app/services/tts.py`). Pocket TTS if installed, else macOS `say`. Never sine tones. `POST /content/sets/{id}/prepare-audio` materialises section WAVs; `GET /content/audio/{filename}` serves them.

## Frontend

App Router pages:

| Route | Role |
|-------|------|
| `/` | Marketing landing |
| `/login`, `/register` | Auth forms |
| `/app` | Studio home: target gap, recent attempts, pending drills, trend |
| `/app/listening` | Section audio, exam or practice mode, key-graded answers |
| `/app/reading` | Academic / GT sets, exam papers before drills, key-graded answers |
| `/app/writing` | Timed Task 1/2 (or 60-minute both-task paper), module switch, drill query params |
| `/app/speaking` | Parts 1–3 or full interview, record/upload/transcript, Part 2 prep timer |
| `/app/mock` | Blueprint-driven 4-skill session (Writing Task 1 then Task 2) |
| `/app/results/[id]` | Polling report: bands or scorecard, evidence, grammar, plan, revise, re-sit, agent trace |
| `/app/attempts` | History (jobs, bands, status) |
| `/app/history` | Redirects to `/app/attempts` |
| `/app/progress` | Band trend, skill averages, study plan (paper attempts only) |
| `/app/settings` | Display name, target band, preferred module |

`apps/web/src/lib/api.ts` is the only HTTP client. Charts use Recharts (`BandGauge`, `BandTrendChart`, `CriteriaCharts`).

## Auth and security

- Email/password, bcrypt, JWT `Authorization: Bearer`. Passwords 8–72 characters.
- Rate limits (in-memory, per client IP): auth 8 / 5 min; evaluations 20 / 10 min.
- CORS from `CORS_ORIGINS`. Methods GET, POST, PATCH, OPTIONS.
- API security headers: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Cache-Control: no-store` (audio files may be cached).
- OpenAPI `/docs` is off when `ENVIRONMENT` is `prod` or `production`.
- Next.js adds similar headers plus `Permissions-Policy` (microphone allowed on same origin for recording).
- Warns at startup if `JWT_SECRET` is still the example default.

## Health

- `GET /health` — process up
- `GET /ready` — `SELECT 1` against Postgres
