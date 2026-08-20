# Run and deploy

One happy path on macOS, Windows, and Ubuntu: copy the example env file, then start Docker Compose. No GPU. Local faster-whisper and Pocket TTS stay in the API image; HuggingFace weights persist in the `hfcache` volume.

Environment variables and host-mode install details: [SETUP.md](SETUP.md).

## Prerequisites

| OS | What you need |
|----|----------------|
| macOS | [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/). Apple Silicon is fine (native `arm64` images). |
| Windows | [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) with the **WSL 2** backend. Clone the repo inside the Linux filesystem (`\\wsl$\...` / `~/`), not `C:\`, if bind mounts feel slow. PowerShell 7+ or Windows Terminal. |
| Ubuntu | Docker Engine + Compose plugin (`docker compose`). Add your user to the `docker` group, then log out/in: `sudo usermod -aG docker $USER`. |

Git should check out text files as LF (`.gitattributes` enforces this). That avoids Windows CRLF breaking `.env` values and shell scripts.

## Happy path (all three OS)

```bash
cp .env.example .env
docker compose up --build
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Or use the helpers (they copy `.env` if it is missing, then start Compose):

```bash
./scripts/dev.sh          # macOS / Ubuntu
.\scripts\dev.ps1         # Windows
```

Pass `-d` to either script to run detached.

| Service | URL |
|---------|-----|
| Studio | http://localhost:3000 |
| API OpenAPI | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Ready (Postgres) | http://localhost:8000/ready |

**First API image build is slow** (often 5–15 minutes). `faster-whisper` pulls PyTorch. That is expected. Rebuilds after that are much faster because `apps/api/.dockerignore` excludes `.venv` and caches. No GPU is used (`STT_DEVICE=cpu`, `STT_COMPUTE_TYPE=int8`).

Whisper / Pocket TTS models download on first speaking or listening use and stay in the Compose volume `hfcache`.

Seed the demo user and curated banks (content seed and demo user also run on API startup; re-running is safe):

```bash
./scripts/seed.sh
# Windows: .\scripts\seed.ps1
# or: docker compose exec api python -m app.seed
#     docker compose exec api python -m app.seed_content
```

Login: `demo@northband.app` / `demo12345`

An LLM key is optional. Without one, agents return heuristic mock JSON so you can walk the UI.

## Host mode (Compose only for Postgres/Redis)

Use this when you want a faster inner loop than rebuilding the API image.

```bash
cp .env.example .env
docker compose up postgres redis -d
```

Keep `DATABASE_URL` and `REDIS_URL` pointing at `localhost` (the values in `.env.example`). Compose overrides those only inside the `api` / `worker` containers.

### macOS

```bash
brew install ffmpeg
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Worker (second terminal): `arq app.worker.WorkerSettings`

Studio: `cd apps/web && npm install && npm run dev`

Apple Silicon: use a native (non-Rosetta) Python 3.12. `portaudio` is not required for file-based Pocket TTS / faster-whisper. Install it only if a host package errors on it (`brew install portaudio`).

### Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y python3.12-venv python3.12-dev ffmpeg build-essential libpq-dev
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Worker and studio commands are the same as macOS.

### Windows

Prefer **WSL 2 Ubuntu** and follow the Ubuntu host-mode steps. A native Windows venv works if you have Python 3.12 and ffmpeg on `PATH`:

```powershell
winget install Gyan.FFmpeg
cd apps\api
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

If `Activate.ps1` is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Slim host install (no local STT/TTS, same as CI): `pip install -r requirements-base.txt`. Speaking then needs a pasted transcript or a cloud STT key.

## OS footguns

### Windows

- **CRLF** — `.gitattributes` forces LF. If `.env` was edited in Notepad and values look “wrong”, convert to UTF-8 LF.
- **Bind mounts / watchers** — Compose sets `WATCHFILES_FORCE_POLLING`, `WATCHPACK_POLLING`, and `CHOKIDAR_USEPOLLING`. If the studio still misses file changes, run the repo from WSL 2, or use host mode.
- **PowerShell vs bash** — use `.\scripts\dev.ps1` / `Copy-Item`; do not run `./scripts/dev.sh` from cmd.exe.
- **Paths** — keep the clone path free of unusual Unicode. Docker Desktop bind-mounts `./apps/api` and `./apps/web`.
- **Speaking audio** — use Chrome or Edge. Allow the microphone (localhost is a secure context). Safari-style `audio/mp4` is a fallback; Chrome records WebM/Opus, which ffmpeg in the API image converts for Whisper. You can always paste a transcript.

### macOS

- Host-mode speaking needs **ffmpeg** (`brew install ffmpeg`). The API image already includes it.
- Docker Desktop file sharing must include the clone directory.
- First listening/speaking call downloads models into `hfcache` (Compose) or `~/.cache/huggingface` (host).

### Ubuntu

- `permission denied` on the Docker socket → user is not in the `docker` group, or you have not re-logged.
- `python3` may be 3.10/3.11; use **3.12** (the API Dockerfile version). 3.14 may lack wheels.
- ffmpeg is already in the API image. Host mode: `sudo apt-get install -y ffmpeg`.

## Production-ish: Compose on a VPS

This repo does not ship Kubernetes. The runnable production path is `docker-compose.prod.yml` on one VM (Ubuntu 22.04/24.04 is what we test against).

1. Install Docker Engine + Compose plugin on the VPS.
2. Clone the repo. Copy env and **change secrets**:

   ```bash
   cp .env.example .env
   ```

   Set at least:

   | Variable | Why |
   |----------|-----|
   | `JWT_SECRET` | Long random value (`openssl rand -hex 32`). The API warns if the example string remains. |
   | `ENVIRONMENT=production` | Hides `/docs`; Redis enqueue failure is an error (no in-process fallback). Prod Compose also forces this. |
   | `CORS_ORIGINS` | Exact studio origin, e.g. `http://YOUR_IP:3000` or `https://studio.example.com`. |
   | `NEXT_PUBLIC_API_URL` | Browser-visible API base, e.g. `http://YOUR_IP:8000`. Baked in at **web image build**. |
   | LLM key | Same as development; mock mode still works if empty. |

3. Start:

   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env up --build -d
   docker compose -f docker-compose.prod.yml exec -T api python -m app.seed
   ```

4. Open `http://YOUR_IP:3000`. Postgres and Redis are **not** published on the host in the prod file.

What prod Compose changes vs the dev file:

- No source bind mounts; no uvicorn `--reload`; no `npm install` on every start.
- Web is `apps/web/Dockerfile.prod` (`next build` then `next start`).
- `restart: unless-stopped` on every service; API `/health` is the healthcheck.
- Same `hfcache` + `uploads` + `pgdata` named volumes.

Put a reverse proxy (Caddy/nginx) in front if you want HTTPS. Point `CORS_ORIGINS` and `NEXT_PUBLIC_API_URL` at those public URLs, then rebuild web (`docker compose -f docker-compose.prod.yml up --build -d web`).

This is a single-node demo you can actually run — not a multi-AZ platform.

## CI

`.github/workflows/api-tests.yml` runs pytest on `ubuntu-latest` with `requirements-base.txt` (no torch, no live keys) and `docker compose config` on both Compose files. After you push to GitHub, the workflow badge is:

`https://github.com/<owner>/<repo>/actions/workflows/api-tests.yml/badge.svg`
