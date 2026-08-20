# API

Base URL in development: `http://localhost:8000`. Interactive OpenAPI: `/docs` and `/redoc` (disabled when `ENVIRONMENT` is `production`).

Authenticated routes expect:

```
Authorization: Bearer <access_token>
```

The studio stores the token as `nb_token` in `localStorage` (`apps/web/src/lib/api.ts`).

Rate limits (per client IP, in-process):

- Auth (`/auth/register`, `/auth/login`): 8 requests / 5 minutes → `429`
- Evaluations (create any skill, revise, transcribe): 20 / 10 minutes → `429`

JSON errors use FastAPI `detail` (string or validation list). The web client flattens those into a single message.

Writing/Speaking jobs run `evaluation_graph`. Reading/Listening jobs run `objective_graph` (keys first, then a coach tool loop). See [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md).

## Health

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/health` | no | `{ "status": "ok" }` |
| GET | `/ready` | no | `{ "status": "ready" }` after `SELECT 1`; 500 if Postgres is down |

## Auth

### `POST /auth/register`

Body:

```json
{
  "email": "student@example.com",
  "password": "at-least-8-chars",
  "display_name": "Amina"
}
```

Password max 72 characters (bcrypt). Email is stored lowercased. `409` if the email exists.

### `POST /auth/login`

```json
{ "email": "student@example.com", "password": "..." }
```

`401` on bad credentials.

Both return:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": "<uuid>",
    "email": "student@example.com",
    "display_name": "Amina",
    "target_band": null,
    "preferred_module": "academic"
  }
}
```

JWT: HS256, `sub` = user id, `typ` = `access`, expiry `JWT_EXPIRE_MINUTES` (default 10080).

### `GET /auth/me`

Current user (`UserOut`). `401` if missing/invalid token.

### `PATCH /auth/me`

Any subset of:

```json
{
  "display_name": "Amina Rahman",
  "target_band": 7.0,
  "preferred_module": "academic"
}
```

`target_band` is 4–9. `preferred_module` is `academic` or `general`.

## Evaluations

Jobs are scoped to the authenticated user. List is newest first, max 50.

### `POST /evaluations/reading` / `POST /evaluations/listening`

JSON body: `content_set_id`, optional `module`, `mode` (`exam`|`practice`), `answers` map, optional `mock_session_id`. Marks are deterministic. A coach agent then investigates misses with tools (`list_misses`, `inspect_item`, `quote_context`); leftover items use a cached explain batch. Short drills (`max_marks < 35`) stay accuracy-only and do not produce a paper band.

### `POST /evaluations/writing`

JSON body:

| Field | Rules |
|-------|--------|
| `module` | `academic` \| `general` |
| `task` | `task1` \| `task2` |
| `prompt` | 10–4000 characters |
| `essay` | 20–8000 characters |
| `parent_attempt_id` | optional UUID string of a previous attempt |
| `study_item_id` | optional; marks that plan item `in_progress`, then `done` on persist |
| `bank_item_id` | optional UUID of the `prompt_items` paper that was sat |

Returns `EvaluationSummary` (`id` is the **job** id, `status` usually `queued`).

### `POST /evaluations/speaking`

`multipart/form-data`:

| Field | Rules |
|-------|--------|
| `module` | `academic` \| `general` (default academic) |
| `task` | `part1` \| `part2` \| `part3` \| `full` |
| `prompt` | 5–4000 characters |
| `transcript` | optional, max 12000 |
| `parent_attempt_id` | optional |
| `bank_item_id` | optional UUID of the prompt-bank paper |
| `audio` | optional file: `.webm .wav .mp3 .m4a .ogg`, ≤ 15 MB |

At least one of `transcript` or `audio` is required. `400` / `413` otherwise.

### `GET /evaluations`

Query: optional `skill=writing|speaking|reading|listening`, `module=academic|general`. Newest first, max 50. Omitting `skill` returns every job for the user. Any other `skill` value is `400`.

### `GET /evaluations/{job_id}`

Full detail. While running, `report` is `partial_report` (tools/grammar may appear before scores). When complete, `report` is the persisted attempt JSON and `attempt_id` is set.

`EvaluationSummary` / detail fields: `id`, `skill`, `module`, `task`, `status`, `error`, `overall_band`, `stage`, `created_at`, plus `prompt`, `input_text`, `transcript`, `speaking_mode`, `attempt_id`, `report`.

Job `status`: `queued` | `running` | `completed` | `failed`.

`stage` (also used for UI copy): `queued`, `ingest`, `transcribe`, `tools`, `plan`, `grading`, `analyzing`, `verify`, `scoring`, `coaching`, `persisting`, `completed`, `failed`.

Writing/Speaking typically walk ingest → tools → plan → analyzing → verify → scoring → coaching → persisting. Reading/Listening walk ingest → grading → scoring (partial marks) → coaching.

### `GET /evaluations/{job_id}/events`

Server-Sent Events. First event is a snapshot (`job_id`, `stage`, `label`, `status`). Then Redis channel `northband:job:{id}` until `completed` or `failed`, followed by `event: end`. If Redis is unavailable the stream ends after the snapshot.

### `POST /evaluations/{job_id}/revise`

Completed attempts only. Body `{ "span": "optional quote" }`. If `span` is omitted, the API uses the first evidence quote, else the first 40 words.

Returns `RevisionAgentOutput` (`original_span`, `rewritten`, `changes`, `target_band`, `notes`) and appends it to `report.revisions`. Target band is weakest criterion + 0.5, capped at 9.

### `POST /speaking/transcribe`

Multipart `audio` only. Returns `{ "transcript": "...", "provider": "faster_whisper"|"openai_compat"|"gemini"|... }`. Local faster-whisper is preferred. `502` if STT fails.

## Content

| Method | Path | Auth |
|--------|------|------|
| GET | `/content/sets?skill=&module=` | yes |
| GET | `/content/next-prompt?skill=writing\|speaking&task=&module=` | yes |
| GET | `/content/next-set?skill=reading\|listening&module=` | yes |
| GET | `/content/sets/{id}` | yes |
| POST | `/content/sets/{id}/prepare-audio` | yes |
| GET | `/content/audio/{filename}` | yes |

Published sets only. `ContentSetSummary.kind` is `exam` or `drill`. Audio files are served from `UPLOAD_DIR/content/audio`. `prepare-audio` materialises Pocket TTS (or `say`) WAVs for a listening set.

`GET /content/next-prompt` returns the next unused writing/speaking paper for this user (shuffled per account). Speaking `task` may be `part1`, `part2`, `part3`, or `full`. Optional `exclude_id` skips the current paper. After at least one completed sit, a live LLM (`AGENT_BANK`) may generate an original paper for that user only. Reading/Listening use `GET /content/next-set` (exam packs before drills) and never generate keys. Starting a mock without `blueprint_id` picks the next unused blueprint.

## Mocks

| Method | Path | Auth |
|--------|------|------|
| GET | `/mocks/blueprints` | yes |
| POST | `/mocks/sessions` | yes |
| GET | `/mocks/sessions/{id}` | yes |
| POST | `/mocks/sessions/{id}/attach/{skill}?job_id=` | yes |
| POST | `/mocks/sessions/{id}/refresh` | yes |

Attach skills: `listening`, `reading`, `writing_task1`, `writing`, `speaking`. `refresh` recomputes skill bands and overall from attached jobs. Writing overall = Task 1×⅓ + Task 2×⅔ (`combine_writing_bands`). Four-skill overall is the half-banded mean of the skills that have a paper band.

## Report shape

`report` is JSONB. Important keys:

| Key | Contents |
|-----|----------|
| `disclaimer` | Practice-estimate notice |
| `tools` | Word count, coverage, fillers, proxy flags |
| `writing` / `speaking` | Per-criterion analysis + evidence |
| `objective` | Reading/Listening: marks, misses, explanations, `coach_trace`, `is_drill`, optional transcripts |
| `grammar` | Issues, patterns, vocab upgrades |
| `scores` | Four criteria, `overall_band`, `confidence`, `scoring_notes`, `exam_ceilings`, `examiner_first_impression` |
| `feedback` | Strengths, weaknesses, actions, examiner summary |
| `performance` | Trends, plateau, `next_focus` |
| `delta` | Present when `parent_attempt_id` was set |
| `revisions` | List of span rewrites |
| `warnings` | Coach/scoring fallbacks, dropped-quote notes |
| `agent_trace` | Plan, stages (`deterministic` / `llm` / `cached` / `skipped` / `math`), per-call latency/tokens |

## Progress

### `GET /progress/summary`

```json
{
  "target_band": 7.0,
  "latest_overall": 6.5,
  "attempt_count": 4,
  "series": [{ "attempt_id": "...", "skill": "writing", "module": "academic", "task": "task2", "overall_band": 6.5, "created_at": "..." }],
  "skills": [{ "skill": "writing", "average_band": 6.4, "attempt_count": 3, "latest_band": 6.5 }],
  "next_focus": "Coherence and Cohesion",
  "overall_estimate": 6.5,
  "overall_confidence": 1.0,
  "missing_skills": [],
  "type_accuracy": { "mcq": { "correct": 8, "total": 10 } }
}
```

`series` is the last 30 **paper** attempts (Reading/Listening drills with `is_drill` or `max_marks < 35` are excluded). `next_focus` comes from the latest attempt’s performance agent. `overall_estimate` is the mean of the latest band per skill (`raw_to_band.overall_ielts_band`); `missing_skills` lists skills with no scored paper yet. `type_accuracy` aggregates Reading/Listening `by_type` stats.

### `GET /progress/llm-usage`

Per-agent call counts and token sums for this user’s jobs:

```json
{
  "by_agent": [{ "agent": "writing", "calls": 3, "prompt_tokens": 1200, "completion_tokens": 800 }],
  "note": "Explain calls should stay cheaper than writing/speaking agents."
}
```

### `GET /progress/study-plan`

Up to 40 items, newest first. Each: `id`, `title`, `detail`, `skill_focus`, `status`, `drill_prompt`, `drill_task`, `drill_skill`, `created_at`.

### `PATCH /progress/study-plan/{item_id}`

```json
{ "status": "pending" }
```

`status`: `pending` | `in_progress` | `done`.

### `POST /progress/study-plan/{item_id}/drill`

Marks the item `in_progress`. Returns `{ "study_item_id", "skill", "task", "prompt" }` for the studio query string. `400` if there is no usable `drill_prompt`.

## Ownership and errors

| Code | Typical cause |
|------|----------------|
| 400 | Bad module/task, missing speaking input, empty drill |
| 401 | Missing or invalid JWT |
| 404 | Job or study item not found **or not owned by this user** |
| 409 | Email already registered |
| 413 | Audio larger than 15 MB |
| 429 | Auth or evaluation rate limit |
| 502 | Transcription provider failed |
